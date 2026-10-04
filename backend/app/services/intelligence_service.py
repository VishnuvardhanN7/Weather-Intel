"""
Intelligence Pipeline Service — the central orchestrator for the
COLLECT → UNDERSTAND → CLASSIFY → VERIFY → CORRELATE → SCORE → EXPLAIN
processing flow.

Every incoming report flows through this service:
  1. Classification (with top-3 candidates)
  2. Severity estimation (with reason)
  3. Misinformation risk (fake detection)
  4. Source trust lookup
  5. Incident clustering (related reports)
  6. Contradiction detection
  7. Verification score
  8. Data quality score
  9. Priority score
  10. Lifecycle determination
  11. AI explanation construction
  12. Timeline reconstruction
"""

from typing import Optional, Dict, Any, List
import json
from datetime import datetime, timezone
from enum import Enum

from app.ml.classifier_engine import classifier_engine
from app.ml.severity_engine import severity_engine
from app.ml.source_trust import get_source_info, compute_trust_record
from app.ml.incident_clusterer import incident_clusterer
from app.ml.contradiction import detect_contradictions
from app.ml.data_quality import compute_data_quality
from app.ml.priority_score import priority_service
from app.ml.stale_detection import determine_lifecycle
from app.ml.explainability import explainability_service
from app.ml.timeline import build_timeline
from app.ml.verification_engine import verification_engine
from app.services.rag_service import evaluate_jev, purify_weather_data, index_approved_event_embedding


class IntelligenceService:
    """
    Runs the full intelligence pipeline on an incoming or existing event.
    All scores are stored in the event's intelligence metadata for explainability.
    """

    @staticmethod
    def _json_safe(value):
        """Recursively convert datetimes, enums, and models to JSON-safe types."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (dict,)):
            return {k: IntelligenceService._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [IntelligenceService._json_safe(v) for v in value]
        if isinstance(value, Enum):
            return value.value
        if hasattr(value, "value") and isinstance(getattr(value, "value"), (str, int, float)):
            return getattr(value, "value")
        if hasattr(value, "to_dict"):
            return IntelligenceService._json_safe(value.to_dict())
        return str(value)

    async def process_event(
        self,
        db,
        event,
        has_official_weather_data: bool = False,
        force_recompute: bool = False,
    ) -> Dict[str, Any]:
        """Run the full intelligence pipeline on an event."""
        title = getattr(event, 'title', '') or ''
        description = getattr(event, 'description', '') or ''
        city = getattr(event, 'city', '') or ''
        source = getattr(event, 'source', '') or ''
        source_url = getattr(event, 'source_url', '') or ''
        metadata = getattr(event, 'metadata_', None) or {}

        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        intelligence = metadata.get('intelligence', {}) if isinstance(metadata, dict) else {}
        if intelligence and not force_recompute:
            return intelligence

        # 1. Classification (always recompute or retrieve stored)
        category, raw_confidence = self._get_or_classify(event)

        # 2. Severity
        severity, severity_confidence, severity_reason = severity_engine.determine(
            title, description, category, city
        )

        # 3. Source trust
        source_type, source_name = get_source_info(event)
        try:
            trust_record = await compute_trust_record(db, source_type, source_name)
        except Exception:
            trust_record = {
                "source_type": source_type,
                "source_name": source_name,
                "trust_score": 50.0,
                "total_reports": 0,
                "reliability_reason": "Trust unavailable",
            }
        source_trust_score = trust_record.get("trust_score", 50.0)

        # 4. Related reports (incident clustering)
        related_reports = []
        try:
            related_reports = await incident_clusterer.find_related_reports(db, event)
        except Exception:
            related_reports = []

        # 5. Contradiction detection
        contradiction_texts = [title, description]
        for rep in related_reports[:5]:
            contradiction_texts.append(rep.get('title', ''))
        contradiction = detect_contradictions(contradiction_texts)
        if contradiction.get("has_conflict"):
            try:
                from app.models.weather_event import VerificationStatus
                event.verification_status = VerificationStatus.NEEDS_REVIEW
            except Exception:
                event.verification_status = 'needs_review'

        # 6. Verification score
        has_official = has_official_weather_data or source == 'api'
        verification = await verification_engine.verify(
            event,
            related_events=related_reports,
            source_trust_score=source_trust_score,
            has_official_weather_data=has_official,
            db=db,
        )

        # JEV Verification Gate & LLM Purification
        jev_decision = await evaluate_jev(event, db=db)
        if jev_decision.get("probability", 0.0) >= 0.6:
            await purify_weather_data(event)
            v_stat = str(getattr(event, 'verification_status', '')).lower()
            if 'verified' in v_stat:
                await index_approved_event_embedding(db, event)

        # 7. Data quality
        dq = compute_data_quality(
            city=city,
            state=getattr(event, 'state', None),
            latitude=getattr(event, 'latitude', None),
            longitude=getattr(event, 'longitude', None),
            reported_at=getattr(event, 'reported_at', None),
            source=source,
            source_url=source_url,
            description=description,
            photos=getattr(event, 'photos', None),
            videos=getattr(event, 'videos', None),
            duplicate_of_id=getattr(event, 'duplicate_of_id', None),
        )

        # 8. Priority score
        is_major_city = self._is_major_city(city)
        priority = priority_service.compute(
            severity=severity if isinstance(severity, str) else (getattr(event, 'severity', 'moderate')).upper(),
            verification_score=verification.score,
            verification_status=verification.status,
            event_type=category,
            reported_at=getattr(event, 'reported_at', None),
            corroboration_count=len(related_reports),
            major_city=is_major_city,
        )

        # 9. Lifecycle
        lifecycle = determine_lifecycle(
            verification_status=verification.status.lower(),
            reported_at=(getattr(event, 'reported_at', None) or datetime.utcnow()).replace(tzinfo=None),
            updated_at=getattr(event, 'updated_at', None),
            severity=severity,
        )

        # 10. Classification candidates for explainability
        cands = []
        try:
            result = classifier_engine.classify(title, description)
            cands = [{
                "category": c.category,
                "confidence": c.confidence,
                "matched_patterns": c.matched_patterns[:3],
            } for c in result.candidates]
        except Exception:
            cands = [{
                "category": category,
                "confidence": raw_confidence,
                "matched_patterns": [],
            }]

        # 11. Build explanation
        explanation = explainability_service.build_explanation(
            event,
            classification={
                "category": category,
                "confidence": raw_confidence,
                "state": "AUTO_CLASSIFIED" if raw_confidence >= 0.6 else "REVIEW_REQUIRED",
                "matched_patterns": cands[0].get("matched_patterns", []) if cands else [],
            },
            verification={
                "score": verification.score,
                "status": verification.status,
                "evidence": verification.evidence,
                "reasoning": verification.reasoning,
            },
            severity={
                "severity": severity,
                "confidence": severity_confidence,
                "reason": severity_reason,
            },
            candidates=cands,
            related_reports=related_reports,
            metadata={"signals": [f"data quality: {dq.get('data_quality', 'n/a')}"]},
        )

        # 12. Timeline
        timeline = self._build_event_timeline(event, related_reports, verification)

        intelligence_result = {
            "classification": {
                "category": category,
                "confidence": round(raw_confidence, 3),
                "candidates": cands,
                "state": "AUTO_CLASSIFIED" if raw_confidence >= 0.6 else "REVIEW_REQUIRED",
                "version": classifier_engine.version,
            },
            "severity": {
                "severity": severity,
                "confidence": severity_confidence,
                "reason": severity_reason,
            },
            "source_trust": {
                "source_type": source_type,
                "source_name": source_name,
                "trust_score": source_trust_score,
                "reliability_reason": trust_record.get("reliability_reason", ""),
                "total_reports": trust_record.get("total_reports", 0),
                "has_sufficient_data": trust_record.get("has_sufficient_data", False),
            },
            "verification": {
                "score": round(verification.score, 1),
                "status": verification.status,
                "breakdown": verification.breakdown.to_dict(),
                "evidence": verification.evidence,
                "reasoning": verification.reasoning,
                "version": verification.version,
            },
            "data_quality": dq,
            "priority": priority,
            "lifecycle": lifecycle,
            "contradiction": contradiction,
            "corroboration": {
                "related_report_count": len(related_reports),
                "source_count": len({r.get('source') for r in related_reports}),
                "is_corroborated": len({r.get('source') for r in related_reports}) >= 2,
                "related_reports": related_reports[:5],
            },
            "explanation": explanation.to_dict(),
            "timeline": timeline,
            "version": "intelligence-pipeline-v1",
            "processed_at": datetime.utcnow().isoformat(),
        }

        curr_metadata = getattr(event, 'metadata_', None) or {}
        if isinstance(curr_metadata, str):
            try:
                curr_metadata = json.loads(curr_metadata)
            except Exception:
                curr_metadata = {}
        if isinstance(curr_metadata, dict):
            curr_metadata['intelligence'] = self._json_safe(intelligence_result)
            setattr(event, 'metadata_', curr_metadata)

        # Mirror key scores onto indexed columns so dashboards can query them
        # without JSON traversal.
        try:
            setattr(event, 'verification_score', verification.score)
            setattr(event, 'priority_score', priority.get('priority_score'))
            setattr(event, 'source_trust_score', source_trust_score)
            setattr(event, 'data_quality_score', dq.get('data_quality_score'))
            setattr(event, 'lifecycle', lifecycle.get('lifecycle'))
            if related_reports and getattr(event, 'incident_id', None) is None:
                setattr(event, 'incident_id', related_reports[0].get('id'))
        except Exception:
            pass

        return self._json_safe(intelligence_result)

    def _get_or_classify(self, event) -> tuple:
        """Get existing classification or run classifier."""
        metadata = getattr(event, 'metadata_', None) or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        intelligence = metadata.get('intelligence', {}) if isinstance(metadata, dict) else {}
        stored_cat = intelligence.get('classification', {}).get('category')
        stored_conf = intelligence.get('classification', {}).get('confidence')

        if stored_cat and stored_conf:
            return stored_cat, stored_conf

        category = getattr(event, 'event_type', None) or 'other'
        confidence = getattr(event, 'category_confidence', 0.0) or 0.0
        if not confidence:
            try:
                _, confidence = classifier_engine._categorizer.categorize(
                    getattr(event, 'title', '') or '',
                    getattr(event, 'description', '') or '',
                )
            except Exception:
                confidence = 0.3
        return category, confidence

    def _is_major_city(self, city: str) -> bool:
        if not city:
            return False
        return city.lower() in {
            "mumbai", "delhi", "kolkata", "chennai", "bangalore", "bengaluru",
            "hyderabad", "ahmedabad", "pune", "surat", "jaipur", "lucknow",
            "kanpur", "nagpur", "visakhapatnam", "patna", "indore", "bhopal",
            "vijayawada", "kochi",
        }

    def _build_event_timeline(self, event, related_reports, verification) -> List[dict]:
        """Build timeline entries from the event data."""
        entries = []
        reported_at = getattr(event, 'reported_at', None)
        now = datetime.utcnow()

        if reported_at:
            entries.append({
                "time": reported_at.isoformat() if isinstance(reported_at, datetime) else str(reported_at),
                "label": "Report received",
                "kind": "ingestion",
            })

        category = getattr(event, 'event_type', None)
        conf = getattr(event, 'category_confidence', 0.0)
        if category:
            entries.append({
                "time": now.isoformat(),
                "label": f"Classified: {category} ({conf:.0%})",
                "kind": "classification",
            })

        if related_reports:
            entries.append({
                "time": now.isoformat(),
                "label": f"Incident clustered ({len(related_reports)} related reports)",
                "kind": "clustering",
            })

        entries.append({
            "time": now.isoformat(),
            "label": f"Verification: {verification.score:.0f}/100 → {verification.status}",
            "kind": "verification",
        })

        return entries


intelligence_service = IntelligenceService()