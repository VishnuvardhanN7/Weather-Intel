"""
ATMOS RAG & JEV Intelligence Pipeline Service.

Source of Truth: System Flow Architecture
DATA SOURCES → Backend → JEV Verification Gate (prob < 0.6 => REJECT; >= 0.6 => ACCEPT)
  → LLM Purification → Admin Approval → Database & Vector Embedding
  → RAG Knowledge Base → Ask ATMOS Chatbot (Vector Similarity Search -> LLM -> Grounded Response)
"""

import os
import math
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.core.config import settings
from app.ml.fake_detector import fake_detector
from app.ml.verification_engine import verification_engine

logger = logging.getLogger(__name__)

# Configurable JEV Probability Threshold (Default: 0.6)
JEV_THRESHOLD: float = float(os.getenv("JEV_THRESHOLD", "0.6"))

# Vector dimension for fallback dense semantic embedding
EMBEDDING_DIM = 128


def _tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into word tokens."""
    if not text:
        return []
    return re.findall(r'\b\w+\b', text.lower())


def generate_embedding(text: str) -> List[float]:
    """
    Generate a normalized vector embedding for text.
    Uses dense semantic hashing and term frequency weighting (128-dim)
    so vector similarity search works deterministically without external API dependencies,
    while remaining fully upgradeable to Gemini/OpenAI embedding APIs.
    """
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * EMBEDDING_DIM

    vector = [0.0] * EMBEDDING_DIM
    for idx, token in enumerate(tokens):
        # Position-aware hashing across 128 dimensions
        h1 = hash(token) % EMBEDDING_DIM
        h2 = hash(token + "_pos") % EMBEDDING_DIM
        weight = 1.0 / (1.0 + math.log(idx + 1))
        vector[h1] += 1.0 * weight
        vector[h2] += 0.5 * weight

    # L2 normalize vector
    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [round(v / norm, 6) for v in vector]
    return vector


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vector embeddings."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


async def evaluate_jev(event, db=None) -> Dict[str, Any]:
    """
    JEV Verification Gate Component.
    Evaluates incoming weather information and computes a probability/confidence score (0.0 - 1.0).

    Decision Rule:
      IF JEV probability < 0.6  => REJECT data (is_fake=True, verification_status='rejected')
      IF JEV probability >= 0.6 => ACCEPT data for LLM purification
    """
    title = getattr(event, 'title', '') or ''
    description = getattr(event, 'description', '') or ''
    source = getattr(event, 'source', '') or ''

    # Signal 1: Misinformation risk from FakeDetector
    is_fake_signal, fake_conf = fake_detector.predict(title, description)

    # Signal 2: Multi-signal VerificationEngine score
    ver_score = 75.0
    try:
        ver_res = await verification_engine.verify(event, db=db)
        ver_score = ver_res.score
    except Exception as e:
        logger.warning(f"Verification engine score error in JEV: {e}")
        ver_score = 65.0 if source in ('api', 'WEB') else 50.0

    # Derive unified JEV probability (0.0 - 1.0)
    ver_prob = ver_score / 100.0
    trust_penalty = fake_conf * 0.4
    jev_probability = max(0.0, min(1.0, ver_prob * (1.0 - trust_penalty)))

    # Apply OpenWeather / official source boost if reliable API
    source_str = str(getattr(source, 'value', source)).lower()
    if source_str in ('api', 'eventsource.api', 'event_source.api') or 'api' in source_str:
        jev_probability = max(jev_probability, 0.85)

    jev_probability = round(jev_probability, 3)
    is_accepted = jev_probability >= JEV_THRESHOLD

    jev_decision = {
        "probability": jev_probability,
        "threshold": JEV_THRESHOLD,
        "status": "ACCEPTED" if is_accepted else "REJECTED",
        "is_fake_flag": is_fake_signal,
        "fake_confidence": round(fake_conf, 3),
        "verification_score": ver_score,
        "evaluated_at": datetime.utcnow().isoformat(),
    }

    # Store JEV probability and decision in metadata
    metadata = getattr(event, 'metadata_', None) or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}

    metadata['jev'] = jev_decision
    setattr(event, 'metadata_', metadata)
    setattr(event, 'fake_confidence', float(fake_conf))

    if not is_accepted:
        # Strict Gate: REJECT data
        setattr(event, 'is_fake', True)
        metadata['pipeline_status'] = 'jev_rejected'
        try:
            from app.models.weather_event import VerificationStatus
            setattr(event, 'verification_status', VerificationStatus.REJECTED)
        except Exception:
            setattr(event, 'verification_status', 'rejected')
    else:
        setattr(event, 'is_fake', False)
        metadata['pipeline_status'] = 'jev_accepted'

    setattr(event, 'metadata_', metadata)
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(event, 'metadata_')
    except Exception:
        pass
    return jev_decision


async def purify_weather_data(event) -> Dict[str, Any]:
    """
    LLM Purification / Summarization Step for ACCEPTED data (JEV >= 0.6).
    Cleans noisy text, extracts key weather facts, preserves metadata, and avoids inventing facts.
    """
    title = getattr(event, 'title', '') or ''
    description = getattr(event, 'description', '') or ''
    event_type = getattr(event, 'event_type', '') or ''
    city = getattr(event, 'city', '') or ''
    state = getattr(event, 'state', '') or ''
    source = getattr(event, 'source', '') or ''

    # Standard clean structuring
    clean_title = re.sub(r'\s+', ' ', title).strip()
    clean_desc = re.sub(r'\s+', ' ', description).strip()

    # Attempt LLM purification if Gemini / OpenAI API key is available
    gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
    purified_summary = None

    if gemini_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                prompt = (
                    f"Purify and summarize this accepted weather report cleanly for atmospheric intelligence database.\n"
                    f"Title: {clean_title}\n"
                    f"Description: {clean_desc}\n"
                    f"Location: {city}, {state}\n"
                    f"Event Type: {event_type}\n"
                    f"Rules: Clean noise, summarize facts accurately, do NOT invent facts."
                )
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}",
                    json={"contents": [{"parts": [{"text": prompt}]}]}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            purified_summary = parts[0].get("text", "").strip()
        except Exception as err:
            logger.warning(f"LLM purification API call error: {err}")

    if not purified_summary:
        loc_str = f" in {city}, {state}" if (city or state) else ""
        purified_summary = f"[{str(event_type).upper()}{loc_str}] {clean_title}. Observations: {clean_desc[:300]}"

    purified_info = {
        "purified_title": clean_title,
        "purified_summary": purified_summary,
        "event_type": str(event_type),
        "location": f"{city}, {state}".strip(", "),
        "purified_at": datetime.utcnow().isoformat(),
    }

    metadata = getattr(event, 'metadata_', None) or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}

    metadata['purified_info'] = purified_info
    metadata['pipeline_status'] = 'purified_pending_review'
    setattr(event, 'metadata_', metadata)
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(event, 'metadata_')
    except Exception:
        pass
    return purified_info


async def index_approved_event_embedding(db, event) -> Optional[List[float]]:
    """
    Embedding Pipeline Step.
    Generates and stores a vector representation for APPROVED records (verification_status == 'verified' and JEV >= 0.6).
    Stores complete metadata tracing back to event_id, source, location, event_type, timestamp, JEV probability, approval status.
    """
    verification_status = str(getattr(event, 'verification_status', '')).lower()
    if 'verified' not in verification_status:
        # Strict Enforcement: Unapproved or rejected records MUST NOT enter vector storage
        return None

    metadata = getattr(event, 'metadata_', None) or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}

    jev_info = metadata.get('jev', {})
    jev_prob = jev_info.get('probability', 0.7)
    if jev_prob < JEV_THRESHOLD or getattr(event, 'is_fake', False):
        # Strict Security Rule: Rejected JEV data cannot enter vector RAG
        return None

    purified = metadata.get('purified_info', {})
    title = purified.get('purified_title') or getattr(event, 'title', '')
    summary = purified.get('purified_summary') or getattr(event, 'description', '')
    city = getattr(event, 'city', '') or ''
    state = getattr(event, 'state', '') or ''
    event_type = getattr(event, 'event_type', '') or ''
    source = getattr(event, 'source', '') or ''
    reported_at = getattr(event, 'reported_at', None)

    # Compose rich text for embedding
    embed_text = f"Event: {title}. Category: {event_type}. Location: {city} {state}. Details: {summary}"
    vector = generate_embedding(embed_text)

    # Attach full tracing metadata
    embedding_record = {
        "event_id": getattr(event, 'id', None),
        "vector": vector,
        "dim": len(vector),
        "source": str(source),
        "location": f"{city}, {state}".strip(", "),
        "city": city,
        "state": state,
        "event_type": str(event_type),
        "timestamp": reported_at.isoformat() if isinstance(reported_at, datetime) else str(reported_at or ''),
        "verification_status": "verified",
        "jev_probability": jev_prob,
        "approval_status": "approved",
        "indexed_at": datetime.utcnow().isoformat(),
    }

    # Re-fetch latest metadata_ to avoid overwriting changes from prior pipeline steps
    current_meta = getattr(event, 'metadata_', None) or {}
    if isinstance(current_meta, str):
        try:
            current_meta = json.loads(current_meta)
        except Exception:
            current_meta = {}
    if not isinstance(current_meta, dict):
        current_meta = {}

    current_meta['vector_embedding'] = embedding_record
    current_meta['pipeline_status'] = 'rag_indexed'
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(event, 'metadata_')
    except Exception:
        pass
    return vector


async def search_rag_knowledge_base(db, query: str, top_k: int = 5, min_score: float = 0.25) -> Tuple[List[Dict[str, Any]], List[float]]:
    """
    RAG Similarity Search.
    Queries the database ONLY for APPROVED and JEV-ACCEPTED weather events.
    Strictly filters out rejected JEV records (< 0.6), unapproved records, and unverified data.
    """
    from sqlalchemy import select
    from app.models.weather_event import WeatherEvent, VerificationStatus

    query_vec = generate_embedding(query)

    # Fetch verified weather events from Database
    stmt = select(WeatherEvent).where(
        WeatherEvent.verification_status == VerificationStatus.VERIFIED,
        WeatherEvent.is_fake == False
    )
    result = await db.execute(stmt)
    approved_events = result.scalars().all()

    scored_records = []

    for ev in approved_events:
        metadata = ev.metadata_ or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}

        # Enforce JEV Gate: Probability >= 0.6
        jev_info = metadata.get('jev', {})
        jev_prob = jev_info.get('probability', ev.verification_score / 100.0 if ev.verification_score else 0.7)
        if jev_prob < JEV_THRESHOLD:
            continue

        # Get or generate vector embedding
        vec_record = metadata.get('vector_embedding', {})
        ev_vec = vec_record.get('vector')
        if not ev_vec:
            purified = metadata.get('purified_info', {})
            title = purified.get('purified_title') or ev.title
            summary = purified.get('purified_summary') or ev.description
            embed_text = f"Event: {title}. Category: {ev.event_type}. Location: {ev.city} {ev.state}. Details: {summary}"
            ev_vec = generate_embedding(embed_text)

        sim_score = cosine_similarity(query_vec, ev_vec)

        # Keyword boost if exact location/category matches query
        q_lower = query.lower()
        if ev.city and ev.city.lower() in q_lower:
            sim_score += 0.25
        if ev.state and ev.state.lower() in q_lower:
            sim_score += 0.20
        e_type = str(ev.event_type.value if hasattr(ev.event_type, 'value') else ev.event_type).lower()
        if e_type in q_lower:
            sim_score += 0.20

        if sim_score >= min_score:
            purified = metadata.get('purified_info', {})
            scored_records.append({
                "event_id": ev.id,
                "title": purified.get('purified_title') or ev.title,
                "description": purified.get('purified_summary') or ev.description,
                "event_type": e_type,
                "severity": str(ev.severity.value if hasattr(ev.severity, 'value') else ev.severity),
                "city": ev.city or "India",
                "state": ev.state or "",
                "source": str(ev.source.value if hasattr(ev.source, 'value') else ev.source),
                "reported_at": ev.reported_at.isoformat() if ev.reported_at else None,
                "jev_probability": jev_prob,
                "verification_score": ev.verification_score or (jev_prob * 100),
                "similarity_score": round(sim_score, 3),
            })

    # Sort candidate records by relevance score and recency
    scored_records.sort(
        key=lambda x: (x["similarity_score"], x["reported_at"] or ""),
        reverse=True
    )

    # 1. Deduplication Step: Remove exact duplicate event IDs and near-duplicate observations
    # (same location + event_type + source, or matching normalized title)
    unique_records = []
    seen_event_ids = set()
    seen_keys = set()
    seen_titles = set()

    for rec in scored_records:
        e_id = rec.get("event_id")
        if e_id and e_id in seen_event_ids:
            continue

        city = (rec.get("city") or "").lower().strip()
        state = (rec.get("state") or "").lower().strip()
        event_type = (rec.get("event_type") or "").lower().strip()
        source = (rec.get("source") or "").lower().strip()
        title_norm = re.sub(r'\W+', '', (rec.get("title") or "").lower())[:30]

        dedup_key = f"{city}_{state}_{event_type}_{source}"

        if dedup_key in seen_keys:
            continue
        if title_norm and title_norm in seen_titles:
            continue

        if e_id:
            seen_event_ids.add(e_id)
        seen_keys.add(dedup_key)
        if title_norm:
            seen_titles.add(title_norm)

        unique_records.append(rec)

    # 2. Diversity Re-ranking: Prefer diverse locations, event types, and timestamps
    diverse_records = []
    seen_locations = set()
    remaining = []

    # First pass: Pick top-scoring observation for each unique location
    for rec in unique_records:
        loc = (rec.get("city") or rec.get("state") or "unknown").lower().strip()
        if loc not in seen_locations:
            seen_locations.add(loc)
            diverse_records.append(rec)
        else:
            remaining.append(rec)

    # Second pass: Fill remaining slots up to top_k from remaining deduplicated records
    for rec in remaining:
        if len(diverse_records) >= top_k:
            break
        diverse_records.append(rec)

    final_results = diverse_records[:top_k]
    return final_results, query_vec

