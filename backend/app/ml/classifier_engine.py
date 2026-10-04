"""
Enhanced Weather Event Classifier with confidence scoring and top-3 candidates.

Classification flow:
1. Normalize text (hashtag splitting, unicode, multilingual)
2. Score each category via pattern matching
3. Apply category priority rules
4. Compute confidence via score-to-confidence mapping
5. Return top-3 candidates for explainability
6. Determine classification state (AUTO_CLASSIFIED vs REVIEW_REQUIRED)

Configurable thresholds:
  HIGH_CONFIDENCE = 0.80
  MEDIUM_CONFIDENCE = 0.60
  LOW_CONFIDENCE = 0.40
  Below LOW = UNCERTAIN
"""

from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field

HIGH_CONFIDENCE_THRESHOLD = 0.80
MEDIUM_CONFIDENCE_THRESHOLD = 0.60
LOW_CONFIDENCE_THRESHOLD = 0.40

CLASSIFIER_VERSION = "classifier-v2-intelligence"


@dataclass
class ClassificationCandidate:
    category: str
    score: float
    confidence: float
    matched_patterns: List[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    candidates: List[ClassificationCandidate]
    state: str  # AUTO_CLASSIFIED or REVIEW_REQUIRED
    reason: str
    version: str = CLASSIFIER_VERSION


class ClassifierEngine:
    """
    Enhanced classifier that wraps the existing Categorizer
    and adds confidence thresholds, top-3 candidates, and
    classification state determination.
    """

    def __init__(self):
        from app.ml.categorizer import categorizer
        self._categorizer = categorizer
        self.version = CLASSIFIER_VERSION

    def classify(self, title: str, description: str) -> ClassificationResult:
        text = f"{title} {description}".strip()
        if not text:
            return ClassificationResult(
                category="other",
                confidence=0.0,
                candidates=[],
                state="REVIEW_REQUIRED",
                reason="Empty input text",
            )

        candidates = self._score_categories(text)

        if not candidates:
            if self._is_normal_weather_text(text):
                return ClassificationResult(
                    category="other",
                    confidence=0.85,
                    candidates=[ClassificationCandidate(
                        category="other",
                        score=5.0,
                        confidence=0.85,
                        matched_patterns=["normal_weather_observation"]
                    )],
                    state="AUTO_CLASSIFIED",
                    reason="Normal weather observation",
                )
            return ClassificationResult(
                category="other",
                confidence=0.4,
                candidates=[],
                state="REVIEW_REQUIRED",
                reason="No category patterns matched",
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        top = candidates[0]

        state = "AUTO_CLASSIFIED" if top.confidence >= MEDIUM_CONFIDENCE_THRESHOLD else "REVIEW_REQUIRED"

        reason = self._build_reason(candidates, top)

        return ClassificationResult(
            category=top.category,
            confidence=top.confidence,
            candidates=candidates[:3],
            state=state,
            reason=reason,
        )

    def _score_categories(self, text: str) -> List[ClassificationCandidate]:
        normalized = self._categorizer._normalize_text(text) if hasattr(self._categorizer, '_normalize_text') else text.lower()
        import re
        normalized = re.split(r'(?<=[a-z])(?=[A-Z])', normalized.replace('-', ' '))
        normalized = ' '.join(normalized)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = ' '.join(normalized.split())

        tokens = set(normalized.split())

        patterns = self._categorizer.patterns if hasattr(self._categorizer, 'patterns') else {}

        if not patterns:
            raw_category, raw_conf = self._categorizer.categorize(title, description)
            if raw_category:
                return [ClassificationCandidate(
                    category=raw_category,
                    score=raw_conf * 10,
                    confidence=raw_conf,
                    matched_patterns=[],
                )]
            return []

        category_scores: Dict[str, float] = {}
        category_matches: Dict[str, List[str]] = {}

        for cat, cat_patterns in patterns.items():
            score = 0.0
            matches = []
            for pattern in cat_patterns:
                p = pattern.lower().strip()
                if ' ' in p:
                    if p in normalized:
                        word_count = len(p.split())
                        weight = min(word_count, 4)
                        score += weight
                        matches.append(p)
                elif p in tokens:
                    score += 1.0
                    matches.append(p)
            if score > 0:
                category_scores[cat] = score
                category_matches[cat] = matches

        candidates = []
        for cat, score in category_scores.items():
            conf = self._score_to_confidence(score)
            candidates.append(ClassificationCandidate(
                category=cat,
                score=score,
                confidence=conf,
                matched_patterns=category_matches.get(cat, []),
            ))

        if candidates:
            candidates = self._apply_priority_rules(candidates)

        return candidates

    def _apply_priority_rules(self, candidates: List[ClassificationCandidate]) -> List[ClassificationCandidate]:
        cats = {c.category: c for c in candidates}

        if 'cyclone' in cats:
            cyclone = cats['cyclone']
            cyclone.confidence = min(0.85 + cyclone.score * 0.02, 0.99)
            return candidates

        if 'flooding' in cats and 'rainfall' in cats:
            flooding = cats['flooding']
            rainfall = cats['rainfall']
            if flooding.confidence >= rainfall.confidence * 0.7:
                flooding.confidence = max(flooding.confidence, rainfall.confidence * 1.05)
                rainfall.confidence *= 0.5

        for strong_cat, weak_cat in [
            ('cyclone', 'strong_winds'),
            ('dust_storm', 'strong_winds'),
            ('thunderstorm', 'strong_winds'),
        ]:
            if strong_cat in cats and weak_cat in cats:
                cats[weak_cat].confidence *= 0.4

        return list(cats.values())

    def _score_to_confidence(self, score: float) -> float:
        if score >= 8:
            return 0.98
        elif score >= 6:
            return 0.95
        elif score >= 4:
            return 0.90
        elif score >= 3:
            return 0.85
        elif score >= 2:
            return 0.80
        elif score >= 1:
            return 0.65
        else:
            return 0.40

    def _build_reason(self, candidates: List[ClassificationCandidate], top: ClassificationCandidate) -> str:
        parts = [f"Classified as {top.category} with {top.confidence:.0%} confidence"]
        if top.matched_patterns:
            pats = top.matched_patterns[:5]
            parts.append(f"Key evidence: {', '.join(pats)}")
        if len(candidates) > 1:
            alt = candidates[1]
            parts.append(f"Alternative: {alt.category} ({alt.confidence:.0%})")
        if top.confidence < MEDIUM_CONFIDENCE_THRESHOLD:
            parts.append("Low confidence - manual review recommended")
        return ". ".join(parts)

    def get_confidence_level(self, confidence: float) -> str:
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return "HIGH"
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return "MEDIUM"
        elif confidence >= LOW_CONFIDENCE_THRESHOLD:
            return "LOW"
        else:
            return "UNCERTAIN"

    def _is_normal_weather_text(self, text: str) -> bool:
        norm = text.lower()
        normal_phrases = [
            "clear sky", "clear skies", "few clouds", "scattered clouds",
            "broken clouds", "overcast", "cloudy", "partly cloudy",
            "mostly cloudy", "fair weather", "normal weather",
            "current weather", "temperature", "humidity", "visibility",
            "feels like", "mist", "haze"
        ]
        severe_keywords = [
            "thunderstorm", "flood", "flooding", "heavy rain", "cloudburst",
            "heatwave", "dust storm", "cyclone", "hurricane", "tornado",
            "squall", "strong wind", "gale", "high wind"
        ]
        has_normal = any(p in norm for p in normal_phrases)
        has_severe = any(k in norm for k in severe_keywords)
        return has_normal and not has_severe


classifier_engine = ClassifierEngine()
