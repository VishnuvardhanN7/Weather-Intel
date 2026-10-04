"""
Enhanced Severity Engine — determines severity (LOW/MODERATE/HIGH/CRITICAL)
from multiple signals with an explainable reason.

Signals:
  - event type baseline risk
  - language intensity keywords
  - affected area (city/state population proxy)
  - infrastructure impact terms
  - casualty/injury mentions (only if explicitly reported)
  - official warnings
  - corroboration strength
  - misinformation risk (reduces severity if high)
"""

from typing import Tuple, Dict, List
import re

SEVERITY_ENGINE_VERSION = "severity-v1-intelligence"

EVENT_BASELINE_SEVERITY = {
    "cyclone": "CRITICAL",
    "flooding": "HIGH",
    "thunderstorm": "HIGH",
    "heatwave": "MODERATE",
    "rainfall": "MODERATE",
    "strong_winds": "MODERATE",
    "dust_storm": "MODERATE",
    "fog": "LOW",
    "other": "LOW",
}

CRITICAL_TERMS = [
    "catastrophic", "disaster", "massive", "emergency", "evacuation",
    "devastating", "worst", "historic", "death", "fatalit", "killed",
    "destroy", "submerge", "dam breach", "dam failure", "flash flood",
    "rescue", "trapped", "collapse", "casualty", "injured", "hospital",
    "widespread", "total loss", "unprecedented", "extreme", "severe",
]

HIGH_TERMS = [
    "heavy rain", "intense", "flooding", "cyclone", "storm surge",
    "landfall", "major", "significant", "warning", "red alert",
    "dangerous", "threatening", "critical", "urgent", "damaging",
    "downpour", "waterlogging", "inundat", "overflow", "burst",
]

MODERATE_TERMS = [
    "moderate", "advisory", "watch", "affected", "damage", "disrupt",
    "impact", "strong wind", "heavy", "risk", "caution", "gust",
]

LOW_TERMS = [
    "light rain", "drizzle", "clear", "normal", "mild", "slight",
    "minor", "patchy", "intermittent",
]

INFRASTRUCTURE_TERMS = [
    "road", "bridge", "power", "electricity", "rail", "metro",
    "building", "house", "transport", "highway", "communication",
]

AREA_SCALE_TERMS = {
    "state_wide": ["entire state", "statewide", "all districts"],
    "multi_city": ["multiple cities", "several cities", "multiple districts"],
    "city_wide": ["entire city", "across the city", "city wide"],
}

# Large Indian cities get a slight severity bump (more people affected)
MAJOR_CITIES = {
    "mumbai", "delhi", "kolkata", "chennai", "bangalore", "bengaluru",
    "hyderabad", "ahmedabad", "pune", "surat", "jaipur", "lucknow",
    "kanpur", "nagpur", "visakhapatnam", "patna", "indore", "bhopal",
    "vijayawada", "kochi", "kozhikode", "thiruvananthapuram",
    "goa", "panaji", "dehradun", "guwahati",
}


class SeverityEngine:
    def __init__(self):
        self.version = SEVERITY_ENGINE_VERSION

    def determine(
        self,
        title: str,
        description: str,
        event_type: str,
        city: str = "",
        corroboration_count: int = 0,
        fake_confidence: float = 0.0,
    ) -> Tuple[str, float, str]:
        """Return (severity, confidence, reason)."""
        text = f"{title} {description}".lower()
        reason_parts = []

        # 1. Baseline by event type
        baseline = EVENT_BASELINE_SEVERITY.get(event_type, "LOW")
        severity_score = {"LOW": 1, "MODERATE": 2, "HIGH": 3, "CRITICAL": 4}[baseline]
        reason_parts.append(f"{event_type or 'weather'} baseline: {baseline.lower()}")

        # 2. Language intensity
        critical_hits = self._count_terms(text, CRITICAL_TERMS)
        high_hits = self._count_terms(text, HIGH_TERMS)
        moderate_hits = self._count_terms(text, MODERATE_TERMS)
        low_hits = self._count_terms(text, LOW_TERMS)

        if critical_hits >= 2:
            severity_score = max(severity_score, 4)
            reason_parts.append(f"{critical_hits} critical indicators")
        elif critical_hits == 1:
            severity_score = max(severity_score, 3)
            reason_parts.append("critical terminology present")

        if high_hits >= 3:
            severity_score = max(severity_score, 3)
            reason_parts.append(f"{high_hits} high-intensity indicators")
        elif high_hits >= 1 and severity_score < 3:
            severity_score = max(severity_score, 2)
            reason_parts.append("moderate-to-high indicators")

        # 2b. Low-intensity language dampens severity claims
        if low_hits >= 1 and (critical_hits + high_hits + moderate_hits) == 0:
            severity_score = 1
            reason_parts.append("normal/low-intensity weather observation")
        elif low_hits >= 2:
            severity_score = max(1, severity_score - 1)
            reason_parts.append("low-intensity language")

        # 3. Infrastructure impact
        infra_hits = self._count_terms(text, INFRASTRUCTURE_TERMS)
        if infra_hits >= 2:
            severity_score = min(severity_score + 1, 4)
            reason_parts.append(f"infrastructure impact ({infra_hits} signals)")

        # 4. Affected area scale
        if any(term in text for term in AREA_SCALE_TERMS["state_wide"]):
            severity_score = min(severity_score + 1, 4)
            reason_parts.append("state-wide impact")
        elif any(term in text for term in AREA_SCALE_TERMS["multi_city"]):
            severity_score = min(severity_score, 3)
            severity_score = max(severity_score, 3)
            reason_parts.append("multi-city impact")

        # 5. Major city context (only bumps severity if actual elevated hazard exists)
        if city and city.lower() in MAJOR_CITIES and severity_score > 1 and event_type not in ("other", None, ""):
            severity_score = min(severity_score + 1, 4)
            reason_parts.append("major city population context")

        # 6. Corroboration boosts credibility of severity
        if corroboration_count >= 3:
            severity_score = min(severity_score + 1, 4)
            reason_parts.append(f"{corroboration_count} corroborating reports")

        # 7. High fake risk reduces severity claim
        if fake_confidence >= 0.6:
            severity_score = max(severity_score - 1, 1)
            reason_parts.append("high misinformation risk — severity dampened")

        severity = {
            1: "LOW",
            2: "MODERATE",
            3: "HIGH",
            4: "CRITICAL",
        }[severity_score]

        confidence = self._compute_confidence(severity_score, critical_hits, high_hits, corroboration_count)
        reason = "; ".join(reason_parts) if reason_parts else "No specific severity indicators"

        return severity, confidence, reason

    def _count_terms(self, text: str, terms: List[str]) -> int:
        return sum(1 for term in terms if term in text)

    def _compute_confidence(self, score: int, critical: int, high: int, corroboration: int) -> float:
        base = {4: 0.95, 3: 0.90, 2: 0.80, 1: 0.75}[score]
        boost = min(critical * 0.02 + high * 0.01 + corroboration * 0.02, 0.1)
        return round(min(0.99, base + boost), 2)


severity_engine = SeverityEngine()