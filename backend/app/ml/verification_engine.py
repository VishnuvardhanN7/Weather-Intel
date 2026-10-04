"""
Verification Engine — the core intelligence that determines whether
a weather event report is trustworthy.

Computes a verification score (0-100) based on multiple evidence signals:

  SOURCE RELIABILITY       (0-25 points)
  CROSS-SOURCE CORROBORATION (0-25 points)
  GEOGRAPHIC CONSISTENCY   (0-20 points)
  TEMPORAL CONSISTENCY     (0-10 points)
  OFFICIAL EVIDENCE        (0-10 points)
  MEDIA EVIDENCE           (0-5 points)
  - MISINFORMATION RISK    (up to -20 penalty)

Verification statuses:
  VERIFIED     — score >= 75 AND high confidence
  PROBABLE     — score >= 50 OR medium confidence with corroborating sources
  NEEDS_REVIEW — score >= 25 OR uncertain classification
  UNVERIFIED   — score < 25 AND single source
  REJECTED     — fake_confidence >= 0.8 OR explicit admin rejection

Configurable weights allow tuning without code changes.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math

VERIFICATION_ENGINE_VERSION = "verification-v1-intelligence"

DEFAULT_WEIGHTS = {
    "source_reliability": 25,
    "cross_source_corroboration": 25,
    "geographic_consistency": 20,
    "temporal_consistency": 10,
    "official_evidence": 10,
    "media_evidence": 5,
    "misinformation_penalty": -20,
}

STATUS_THRESHOLDS = {
    "VERIFIED": 75,
    "PROBABLE": 50,
    "NEEDS_REVIEW": 25,
}


@dataclass
class VerificationBreakdown:
    source_reliability: float = 0.0
    cross_source_corroboration: float = 0.0
    geographic_consistency: float = 0.0
    temporal_consistency: float = 0.0
    official_evidence: float = 0.0
    media_evidence: float = 0.0
    misinformation_penalty: float = 0.0

    def to_dict(self) -> dict:
        return {
            "source_reliability": round(self.source_reliability, 1),
            "cross_source_corroboration": round(self.cross_source_corroboration, 1),
            "geographic_consistency": round(self.geographic_consistency, 1),
            "temporal_consistency": round(self.temporal_consistency, 1),
            "official_evidence": round(self.official_evidence, 1),
            "media_evidence": round(self.media_evidence, 1),
            "misinformation_penalty": round(self.misinformation_penalty, 1),
        }


@dataclass
class VerificationResult:
    score: float
    status: str
    breakdown: VerificationBreakdown
    evidence: List[str]
    reasoning: str
    version: str = VERIFICATION_ENGINE_VERSION


class VerificationEngine:
    """
    Multi-signal verification engine that evaluates weather event reports
    against multiple evidence dimensions.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()

    async def verify(
        self,
        event,
        related_events: List[Any] = None,
        source_trust_score: float = 50.0,
        has_official_weather_data: bool = False,
        db=None,
    ) -> VerificationResult:
        related_events = related_events or []
        breakdown = VerificationBreakdown()
        evidence = []

        breakdown.source_reliability = self._score_source_reliability(
            source_trust_score, event
        )
        if breakdown.source_reliability > 15:
            evidence.append(f"Source trust: {source_trust_score:.0f}/100")
        elif breakdown.source_reliability < 8:
            evidence.append("Low source reliability")

        breakdown.cross_source_corroboration = self._score_corroboration(
            event, related_events
        )
        num_sources = len(set(
            (e.get("source", "") if isinstance(e, dict) else getattr(e, "source", ""))
            for e in related_events
        )) + 1
        if num_sources >= 3:
            evidence.append(f"{num_sources} independent sources corroborate")
        elif num_sources >= 2:
            evidence.append(f"{num_sources} sources agree")

        breakdown.geographic_consistency = self._score_geographic_consistency(
            event, related_events
        )
        close_sources = sum(1 for e in related_events
                          if self._events_nearby(event, e, max_km=25))
        if close_sources >= 2:
            evidence.append(f"{close_sources} nearby reports (within 25 km)")

        breakdown.temporal_consistency = self._score_temporal_consistency(
            event, related_events
        )
        recent_sources = sum(1 for e in related_events
                           if self._events_temporally_close(event, e, hours=3))
        if recent_sources >= 1:
            evidence.append(f"{recent_sources} reports within 3 hours")

        breakdown.official_evidence = self._score_official_evidence(
            has_official_weather_data, event
        )
        if has_official_weather_data:
            evidence.append("Official weather data supports this event")

        breakdown.media_evidence = self._score_media_evidence(event)
        has_media = bool(
            (getattr(event, 'photos', None) and len(getattr(event, 'photos', []) or []) > 0) or
            (getattr(event, 'videos', None) and len(getattr(event, 'videos', []) or []) > 0)
        )
        if has_media:
            evidence.append("Visual evidence available")

        breakdown.misinformation_penalty = self._compute_misinfo_penalty(
            getattr(event, 'fake_confidence', 0.0)
        )
        if breakdown.misinformation_penalty < -5:
            evidence.append(f"Misinformation risk: {abs(breakdown.misinformation_penalty):.0f} penalty")

        score = self._compute_total_score(breakdown)
        score = max(0, min(100, score))

        status = self._determine_status(score, event, num_sources)
        reasoning = self._build_reasoning(score, status, breakdown, evidence)

        return VerificationResult(
            score=score,
            status=status,
            breakdown=breakdown,
            evidence=evidence,
            reasoning=reasoning,
        )

    def _score_source_reliability(self, trust_score: float, event) -> float:
        max_points = self.weights["source_reliability"]
        normalized = trust_score / 100.0
        base = normalized * max_points

        source = getattr(event, 'source', '') or ''
        if source in ('api', 'WEB'):
            base = min(base + 3, max_points)
        elif source in ('CITIZEN_REPORT',):
            base = base * 0.9

        return round(base, 1)

    def _score_corroboration(self, event, related_events: List) -> float:
        max_points = self.weights["cross_source_corroboration"]
        src = getattr(event, 'source', '') if not isinstance(event, dict) else event.get('source', '')
        if src in ('api', 'WEB'):
            return max_points * 0.70
        if not related_events:
            return max_points * 0.2

        unique_sources = set()
        unique_sources.add(getattr(event, 'source', 'unknown') if not isinstance(event, dict) else event.get('source', 'unknown'))
        for re in related_events:
            s = re.get("source", "") if isinstance(re, dict) else getattr(re, "source", "")
            unique_sources.add(s)

        source_count = len(unique_sources)
        if source_count >= 5:
            return max_points
        elif source_count >= 4:
            return max_points * 0.95
        elif source_count >= 3:
            return max_points * 0.80
        elif source_count >= 2:
            return max_points * 0.55
        else:
            return max_points * 0.20

    def _score_geographic_consistency(self, event, related_events: List) -> float:
        max_points = self.weights["geographic_consistency"]
        src = getattr(event, 'source', '') if not isinstance(event, dict) else event.get('source', '')
        if src in ('api', 'WEB'):
            return max_points * 0.85
        if not related_events:
            return max_points * 0.3

        event_lat = getattr(event, 'latitude', None) if not isinstance(event, dict) else event.get('latitude')
        event_lng = getattr(event, 'longitude', None) if not isinstance(event, dict) else event.get('longitude')
        if event_lat is None or event_lng is None:
            event_city = getattr(event, 'city', '') if not isinstance(event, dict) else event.get('city', '')
            if event_city:
                return max_points * 0.5
            return max_points * 0.2

        nearby_count = 0
        for re in related_events:
            if self._events_nearby(event, re, max_km=25):
                nearby_count += 1

        total = len(related_events)
        if total == 0:
            return max_points * 0.3

        ratio = nearby_count / total
        return round(max_points * (0.3 + 0.7 * ratio), 1)

    def _score_temporal_consistency(self, event, related_events: List) -> float:
        max_points = self.weights["temporal_consistency"]
        src = getattr(event, 'source', '') if not isinstance(event, dict) else event.get('source', '')
        if src in ('api', 'WEB'):
            return max_points * 0.90
        if not related_events:
            return max_points * 0.3

        event_time = getattr(event, 'reported_at', None) if not isinstance(event, dict) else event.get('reported_at')
        if event_time is None:
            return max_points * 0.3

        recent_count = 0
        for re in related_events:
            if self._events_temporally_close(event, re, hours=6):
                recent_count += 1

        total = len(related_events)
        ratio = recent_count / total if total > 0 else 0
        return round(max_points * (0.3 + 0.7 * ratio), 1)

    def _score_official_evidence(self, has_official: bool, event) -> float:
        max_points = self.weights["official_evidence"]
        src = getattr(event, 'source', '') if not isinstance(event, dict) else event.get('source', '')
        if has_official or src == 'api':
            return max_points
        return 0.0

    def _score_media_evidence(self, event) -> float:
        max_points = self.weights["media_evidence"]
        photos = (getattr(event, 'photos', None) if not isinstance(event, dict) else event.get('photos')) or []
        videos = (getattr(event, 'videos', None) if not isinstance(event, dict) else event.get('videos')) or []
        if videos:
            return max_points
        if photos:
            return max_points * 0.7
        return 0.0

    def _compute_misinfo_penalty(self, fake_confidence: float) -> float:
        max_penalty = abs(self.weights["misinformation_penalty"])
        if fake_confidence >= 0.8:
            return -max_penalty
        elif fake_confidence >= 0.6:
            return -max_penalty * 0.6
        elif fake_confidence >= 0.4:
            return -max_penalty * 0.3
        elif fake_confidence >= 0.2:
            return -max_penalty * 0.1
        return 0.0

    def _compute_total_score(self, breakdown: VerificationBreakdown) -> float:
        total = (
            breakdown.source_reliability
            + breakdown.cross_source_corroboration
            + breakdown.geographic_consistency
            + breakdown.temporal_consistency
            + breakdown.official_evidence
            + breakdown.media_evidence
            + breakdown.misinformation_penalty
        )
        return total

    def _determine_status(self, score: float, event, num_sources: int) -> str:
        verification_status = getattr(event, 'verification_status', '') if not isinstance(event, dict) else event.get('verification_status', '')
        if verification_status == 'rejected':
            return 'REJECTED'

        fake_conf = getattr(event, 'fake_confidence', 0.0) if not isinstance(event, dict) else event.get('fake_confidence', 0.0)
        if fake_conf >= 0.8:
            return 'REJECTED'

        cat_conf = getattr(event, 'category_confidence', 0.0) if not isinstance(event, dict) else event.get('category_confidence', 0.0)
        src = getattr(event, 'source', '') if not isinstance(event, dict) else event.get('source', '')

        if (score >= STATUS_THRESHOLDS["VERIFIED"] and (cat_conf >= 0.5 or src == 'api')) or (src == 'api' and score >= 65):
            return 'VERIFIED'
        elif score >= STATUS_THRESHOLDS["PROBABLE"] and (num_sources >= 2 or cat_conf >= 0.6 or src == 'api'):
            return 'PROBABLE'
        elif score >= STATUS_THRESHOLDS["NEEDS_REVIEW"]:
            return 'NEEDS_REVIEW'
        else:
            return 'UNVERIFIED'

    def _events_nearby(self, event, other, max_km: float = 25) -> bool:
        lat1 = getattr(event, 'latitude', None)
        lng1 = getattr(event, 'longitude', None)
        if isinstance(other, dict):
            lat2 = other.get('latitude')
            lng2 = other.get('longitude')
        else:
            lat2 = getattr(other, 'latitude', None)
            lng2 = getattr(other, 'longitude', None)

        if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
            city1 = getattr(event, 'city', '')
            city2 = other.get('city', '') if isinstance(other, dict) else getattr(other, 'city', '')
            return bool(city1 and city2 and city1.lower() == city2.lower())

        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return (R * c) <= max_km

    def _events_temporally_close(self, event, other, hours: float = 6) -> bool:
        t1 = getattr(event, 'reported_at', None)
        if isinstance(other, dict):
            t2_str = other.get('reported_at')
            t2 = t2_str if isinstance(t2_str, datetime) else None
        else:
            t2 = getattr(other, 'reported_at', None)

        if t1 is None or t2 is None:
            return False

        if isinstance(t1, str):
            try:
                t1 = datetime.fromisoformat(t1.replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                return False
        if isinstance(t2, str):
            try:
                t2 = datetime.fromisoformat(t2.replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                return False

        diff = abs((t2 - t1).total_seconds() / 3600)
        return diff <= hours

    def _build_reasoning(self, score: float, status: str, breakdown: VerificationBreakdown, evidence: List[str]) -> str:
        parts = [f"Verification score: {score:.0f}/100 → {status}"]
        if evidence:
            parts.append("Evidence: " + "; ".join(evidence[:5]))
        if score < 30:
            parts.append("Insufficient corroboration — needs manual review")
        return ". ".join(parts)


verification_engine = VerificationEngine()
