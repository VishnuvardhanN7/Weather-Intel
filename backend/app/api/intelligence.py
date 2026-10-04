"""
Intelligence & Explainability API.

Endpoints:
  GET  /events/{event_id}           → full AI intelligence panel for an event
  GET  /events/{event_id}/audit     → classification / review audit trail
  POST /events/{event_id}/classify  → admin classification override (human-in-the-loop)
  GET  /sources                     → source health & trust table

Every intelligence block is versioned and reconstructable. History is stored
in event metadata so nothing is ever lost when the pipeline is improved.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.weather_event import WeatherEvent, EventType, EventSource, VerificationStatus
from app.models.user import User
from app.api.auth import get_current_user, get_current_admin
from app.services.intelligence_service import intelligence_service
from app.ml.source_trust import get_all_source_trusts
from app.ml.classifier_engine import classifier_engine

router = APIRouter()


class ClassificationOverride(BaseModel):
    event_type: EventType
    reason: str
    note: Optional[str] = None


def _get_intelligence(event) -> dict:
    metadata = event.metadata_ or {}
    return metadata.get("intelligence", {}) if isinstance(metadata, dict) else {}


@router.get("/events/{event_id}", response_model=dict)
async def event_intelligence(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the complete intelligence panel for an event.

    Lazy-computes the pipeline if the event predates the intelligence
    engine, so every historical event gets a score without a migration.
    """
    result = await db.execute(
        select(WeatherEvent).where(WeatherEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Weather event not found")

    intelligence = _get_intelligence(event)
    if not intelligence:
        intelligence = await intelligence_service.process_event(db, event)
        await db.commit()
        await db.refresh(event)
        intelligence = _get_intelligence(event)

    return {
        "event": event.to_dict(),
        "intelligence": intelligence,
    }


@router.get("/events/{event_id}/audit", response_model=dict)
async def event_audit_trail(
    event_id: int,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WeatherEvent)
        .options(
            selectinload(WeatherEvent.reported_by),
            selectinload(WeatherEvent.verified_by),
        )
        .where(WeatherEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Weather event not found")

    metadata = event.metadata_ or {}
    intelligence = metadata.get("intelligence", {}) if isinstance(metadata, dict) else {}
    classification_history = intelligence.get("classification_history", []) or []

    return {
        "event_id": event.id,
        "reported_at": event.reported_at.isoformat() if event.reported_at else None,
        "reported_by": (event.reported_by.username if event.reported_by else None),
        "verified_by": (event.verified_by.username if event.verified_by else None),
        "audit_entries": list(classification_history),
    }


def _ensure_classification_history(metadata: dict) -> list:
    intelligence = metadata.setdefault("intelligence", {})
    history = intelligence.setdefault("classification_history", [])
    return history


@router.post("/events/{event_id}/classify", response_model=dict)
async def classify_override(
    event_id: int,
    override: ClassificationOverride,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Human-in-the-loop classification override.

    Keeps the original AI decision + the manual decision + who/when/why in
    the audit trail. Marks the classification state MANUALLY_CLASSIFIED.
    """
    result = await db.execute(select(WeatherEvent).where(WeatherEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Weather event not found")

    metadata = event.metadata_ or {}
    if not isinstance(metadata, dict):
        metadata = {}

    intelligence = metadata.get("intelligence", {})
    if not isinstance(intelligence, dict):
        intelligence = {"version": "intelligence-pipeline-v1"}

    original = {
        "event_type": event.event_type.value if event.event_type else None,
        "confidence": getattr(event, "category_confidence", 0.0) or 0.0,
        "state": intelligence.get("classification", {}).get("state", "AUTO_CLASSIFIED"),
        "version": intelligence.get("classification", {}).get("version", classifier_engine.version),
    }

    history = _ensure_classification_history(metadata)
    history.append({
        "action": "manual_override",
        "timestamp": datetime.utcnow().isoformat(),
        "admin_id": current_user.id,
        "admin_username": current_user.username,
        "original": original,
        "new": {
            "event_type": override.event_type.value,
        },
        "reason": override.reason,
        "note": override.note,
    })

    classification = intelligence.setdefault("classification", {})
    classification["category"] = override.event_type.value
    classification["state"] = "MANUALLY_CLASSIFIED"
    classification["manual_override"] = {
        "approved_by": current_user.username,
        "approved_at": datetime.utcnow().isoformat(),
        "reason": override.reason,
    }

    intelligence["classification_history"] = history
    metadata["intelligence"] = intelligence
    event.metadata_ = metadata
    event.event_type = override.event_type

    await db.commit()
    await db.refresh(event)

    return {
        "event_id": event.id,
        "event_type": override.event_type.value,
        "state": "MANUALLY_CLASSIFIED",
        "ai_original": original,
        "approved_by": current_user.username,
    }


@router.get("/sources", response_model=dict)
async def source_health(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Source health & trust table for data provenance transparency."""
    trusts = await get_all_source_trusts(db)
    return {
        "version": "source-trust-v1",
        "min_samples_for_statistics": 10,
        "sources": trusts,
    }


class ChatQueryRequest(BaseModel):
    query: str


@router.post("/ask", response_model=dict)
async def ask_intelligence(
    body: ChatQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Conversational AI assistant endpoint for ATMOS Indian weather intelligence.

    Uses RAG vector similarity search over JEV-accepted and admin-approved RAG knowledge base.
    """
    import json
    import os
    from app.core.config import settings
    from app.services.rag_service import search_rag_knowledge_base

    query_text = (body.query or "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 1. Perform RAG Vector Similarity Search on APPROVED knowledge base only
    retrieved_docs, _ = await search_rag_knowledge_base(db, query_text, top_k=5, min_score=0.20)

    # 2. Handle insufficient RAG context (do NOT hallucinate!)
    if not retrieved_docs:
        return {
            "query": query_text,
            "answer": "I don't have enough verified information in the current weather knowledge base to answer that reliably.",
            "events_analyzed": 0,
            "high_priority_count": 0,
            "avg_verification_score": 0.0,
            "related_events": [],
            "verified_sources": [],
        }

    # 3. Grounded Context Construction
    context_lines = []
    verified_sources = []
    for doc in retrieved_docs:
        context_lines.append(
            f"• [{doc['event_type'].upper()}] {doc['title']} in {doc['city']}, {doc['state']} "
            f"(Severity: {doc['severity']}, Source: {doc['source']}, Reported: {doc['reported_at']}, JEV Prob: {doc['jev_probability']}): "
            f"{doc['description']}"
        )
        verified_sources.append({
            "id": doc["event_id"],
            "title": doc["title"],
            "city": doc["city"],
            "state": doc["state"],
            "source": doc["source"],
            "event_type": doc["event_type"],
            "reported_at": doc["reported_at"],
            "similarity_score": doc["similarity_score"],
        })

    context_str = "\n".join(context_lines)

    # 4. Generate Grounded Response using LLM
    ai_response = None
    gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
    openai_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None)

    if gemini_key:
        try:
            import httpx
            prompt = (
                f"You are ATMOS AI, a professional weather intelligence assistant for India.\n"
                f"Answer the user query based ONLY on the following verified RAG knowledge context:\n\n"
                f"{context_str}\n\n"
                f"User Question: {query_text}\n"
                f"Instructions: Mention relevant locations, event type, time and available metadata. "
                f"Be concise, grounded, and accurate."
            )
            async with httpx.AsyncClient(timeout=15.0) as client:
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
                            ai_response = parts[0].get("text", "").strip()
        except Exception:
            ai_response = None

    if not ai_response and openai_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": "You are ATMOS AI assistant for Indian weather intelligence based strictly on grounded context."},
                            {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {query_text}"}
                        ]
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    ai_response = data["choices"][0]["message"]["content"].strip()
        except Exception:
            ai_response = None

    # Fallback grounded summary synthesis from retrieved docs
    if not ai_response:
        num_docs = len(retrieved_docs)
        if num_docs == 1:
            intro = "Based on the current knowledge base, I found 1 unique verified observation:"
        else:
            intro = f"Based on {num_docs} verified observations in the ATMOS knowledge base:"

        obs_items = []
        for d in retrieved_docs:
            loc = f"{d['city']}" + (f", {d['state']}" if d.get('state') else "")
            title_text = d['title'] or d['description'][:100]
            obs_items.append(f"• **{loc}** — {title_text}")

        obs_summary = "\n".join(obs_items)
        ai_response = (
            f"{intro}\n\n"
            f"{obs_summary}\n\n"
            f"These observations were retrieved from the verified ATMOS knowledge base."
        )


    return {
        "query": query_text,
        "answer": ai_response,
        "events_analyzed": len(retrieved_docs),
        "high_priority_count": sum(1 for d in retrieved_docs if d.get("severity") in ("high", "critical")),
        "avg_verification_score": round(sum(d.get("verification_score", 85) for d in retrieved_docs) / len(retrieved_docs), 1),
        "related_events": [
            {
                "id": d["event_id"],
                "title": d["title"],
                "city": d["city"],
                "state": d["state"],
                "event_type": d["event_type"],
                "severity": d["severity"],
            }
            for d in retrieved_docs
        ],
        "verified_sources": verified_sources,
    }
