"""
Incident Priority Score — how urgently should authorities respond.

Factors:
  severity (40%)
  verification confidence (25%)
  population/area impact (15%)
  event type risk (10%)
  recency (5%)
  corroborating report count (5%)

Clearly DISTINCT from:
  Classification Confidence (WHAT is this event?)
  Verification Score (IS the report genuine?)
  Severity (HOW serious is it?)
"""

from typing import Optional
from datetime import datetime, timedelta
import math

PRIORITY_SERVICE_VERSION = "priority-v1"

SEVERITY_WEIGHT = 0.40
VERIFICATION_WEIGHT = 0.25
IMPACT_WEIGHT = 0.15
EVENT_TYPE_WEIGHT = 0.10
RECENCY_WEIGHT = 0.05
CORROBORATION_WEIGHT = 0.05

EVENT_TYPE_RISK = {
    "cyclone": 1.0,
    "flooding": 0.95,
    "thunderstorm": 0.80,
    "heatwave": 0.65,
    "rainfall": 0.55,
    "strong_winds": 0.60,
    "dust_storm": 0.50,
    "fog": 0.45,
    "other": 0.30,
}

SEVERITY_SCORES = {
    "CRITICAL": 1.0,
    "HIGH": 0.75,
    "MODERATE": 0.50,
    "LOW": 0.25,
}


class PriorityScoreService:

    def compute(
        self,
        severity: str,
        verification_score: float = 50.0,
        verification_status: str = "NEEDS_REVIEW",
        event_type: str = "other",
        reported_at: Optional[datetime] = None,
        corroboration_count: int = 0,
        major_city: bool = False,
    ) -> dict:
        """Compute priority score 0-100 with breakdown."""
        severity_score = SEVERITY_SCORES.get(severity, 0.5)

        # Verification confidence
        verification_normalized = verification_score / 100.0
        if verification_status == "REJECTED":
            verification_normalized = 0.0
        elif verification_status == "VERIFIED":
            verification_normalized = max(verification_normalized, 0.75)

        # Event type risk
        type_risk = EVENT_TYPE_RISK.get(event_type, 0.3)

        # Population impact: major city adds weight
        impact_score = 0.5
        if major_city:
            impact_score = 0.9
        if severity in ("HIGH", "CRITICAL"):
            impact_score = min(impact_score + 0.1, 1.0)

        # Recency: events in last 2 hours = high recency
        recency = 0.5
        if reported_at:
            age_hours = (datetime.utcnow() - reported_at).total_seconds() / 3600
            recency = max(0.0, 1.0 - age_hours / 24.0)

        # Corroboration
        corroboration = min(corroboration_count / 5.0, 1.0)

        priority = (
            severity_score * SEVERITY_WEIGHT
            + verification_normalized * VERIFICATION_WEIGHT
            + impact_score * IMPACT_WEIGHT
            + type_risk * EVENT_TYPE_WEIGHT
            + recency * RECENCY_WEIGHT
            + corroboration * CORROBORATION_WEIGHT
        ) * 100

        priority = max(0, min(100, round(priority, 1)))

        if priority >= 75:
            level = "CRITICAL"
        elif priority >= 50:
            level = "HIGH"
        elif priority >= 25:
            level = "MODERATE"
        else:
            level = "LOW"

        return {
            "priority_score": priority,
            "priority_level": level,
            "breakdown": {
                "severity": round(severity_score * SEVERITY_WEIGHT * 100, 1),
                "verification_confidence": round(verification_normalized * VERIFICATION_WEIGHT * 100, 1),
                "impact": round(impact_score * IMPACT_WEIGHT * 100, 1),
                "event_type_risk": round(type_risk * EVENT_TYPE_WEIGHT * 100, 1),
                "recency": round(recency * RECENCY_WEIGHT * 100, 1),
                "corroboration": round(corroboration * CORROBORATION_WEIGHT * 100, 1),
            },
            "version": PRIORITY_SERVICE_VERSION,
        }


priority_service = PriorityScoreService()