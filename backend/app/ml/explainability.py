"""
AI Explainability Service — generates human-readable explanations for
every AI decision (classification, verification, severity, priority).

These explanations power the "WHY TRUST THIS EVENT?" and "AI DECISION CARD"
features in the UI, making the platform transparent instead of a black box.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

EXPLAINABILITY_VERSION = "explainability-v1"


@dataclass
class AIExplanation:
    classification_reason: str = ""
    verification_reason: str = ""
    severity_reason: str = ""
    classification_evidence: List[str] = field(default_factory=list)
    verification_evidence: List[str] = field(default_factory=list)
    why_not_alternatives: List[str] = field(default_factory=list)
    confidence_level: str = ""
    key_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "classification_reason": self.classification_reason,
            "verification_reason": self.verification_reason,
            "severity_reason": self.severity_reason,
            "classification_evidence": self.classification_evidence,
            "verification_evidence": self.verification_evidence,
            "why_not_alternatives": self.why_not_alternatives,
            "confidence_level": self.confidence_level,
            "key_factors": self.key_factors,
            "version": EXPLAINABILITY_VERSION,
        }


class ExplainabilityService:

    def build_explanation(
        self,
        event: Any,
        classification: Optional[dict] = None,
        verification: Optional[dict] = None,
        severity: Optional[dict] = None,
        candidates: Optional[List[dict]] = None,
        related_reports: Optional[List[dict]] = None,
        metadata: Optional[dict] = None,
    ) -> AIExplanation:
        """Build a complete AI explanation for an event."""
        explanation = AIExplanation()
        metadata = metadata or {}

        # --- Classification explanation ---
        if classification:
            category = classification.get("category") or getattr(event, "event_type", "")
            confidence = classification.get("confidence", 0.0)
            matched = classification.get("matched_patterns") or []
            state = classification.get("state", "AUTO_CLASSIFIED")

            if category:
                explanation.classification_reason = (
                    f"Classified as {category} with {confidence:.0%} confidence. "
                    f"{self._perspective_label(confidence)}."
                )
            if matched:
                explanation.classification_evidence = matched[:6]
            explanation.confidence_level = self._confidence_label(confidence)
            explanation.key_factors.append(f"classification: {category} ({confidence:.0%})")

            if candidates:
                for alt in candidates[1:]:
                    alt_cat = alt.get("category")
                    alt_conf = alt.get("confidence", 0)
                    if alt_cat and alt_cat != category:
                        explanation.why_not_alternatives.append(
                            f"{alt_cat} scored lower ({alt_conf:.0%}) because {alt.get('matched_patterns', [])[:2] or 'evidence was weaker'}"
                        )

        # --- Verification explanation ---
        if verification:
            score = verification.get("score", 0)
            status = verification.get("status", "")
            evidence = verification.get("evidence") or []
            reasoning = verification.get("reasoning", "")
            if score:
                explanation.verification_reason = (
                    f"Verification score {score:.0f}/100 → {status}. {reasoning}"
                )
            if evidence:
                explanation.verification_evidence = evidence[:6]
            explanation.key_factors.append(f"verification: {status} ({score:.0f}/100)")

        # --- Severity explanation ---
        if severity:
            level = severity.get("severity", "")
            reason = severity.get("reason", "")
            sev_conf = severity.get("confidence", 0)
            explanation.severity_reason = f"Severity: {level} ({sev_conf:.0%}). {reason}".strip()
            explanation.key_factors.append(f"severity: {level}")

        # --- Corroboration (from related reports) ---
        if related_reports:
            unique_sources = set()
            for rep in related_reports:
                src = rep.get("source", "")
                if src:
                    unique_sources.add(src)
            if len(unique_sources) >= 2:
                explanation.key_factors.append(f"{len(unique_sources)} corroborating sources")
            explanation.key_factors.append(f"{len(related_reports)} related reports")

        # --- Data quality signals ---
        if metadata:
            signals = metadata.get("signals") or []
            for sig in signals[:3]:
                explanation.key_factors.append(sig)

        return explanation

    def _confidence_label(self, confidence: float) -> str:
        if confidence >= 0.80:
            return "HIGH"
        elif confidence >= 0.60:
            return "MEDIUM"
        elif confidence >= 0.40:
            return "LOW"
        return "UNCERTAIN"

    def _perspective_label(self, confidence: float) -> str:
        if confidence >= 0.80:
            return "High confidence classification"
        elif confidence >= 0.60:
            return "Medium confidence — likely correct"
        elif confidence >= 0.40:
            return "Low confidence — manual review advised"
        return "Uncertain — needs manual review"


explainability_service = ExplainabilityService()