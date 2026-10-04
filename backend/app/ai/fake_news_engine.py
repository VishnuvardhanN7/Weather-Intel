"""
AI Engine 2: Fake News Detection Service.

Wraps the existing backend/app/ml/fake_detector.py behind BaseFakeNewsEngine interface,
preserving all existing fake detection behavior, thresholds, and feature scoring.
"""

import logging
from typing import Any, Dict, Tuple

from app.ml.fake_detector import fake_detector

logger = logging.getLogger(__name__)


class BaseFakeNewsEngine:
    """Base interface for Fake News Detection AI Engine."""

    def detect_fake_news(self, title: str, description: str) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement detect_fake_news()")


class FakeNewsEngine(BaseFakeNewsEngine):
    """
    Fake News Engine wrapping existing ML fake_detector implementation.
    """

    def __init__(self, detector=None):
        self.detector = detector or fake_detector

    def detect_fake_news(self, title: str, description: str) -> Dict[str, Any]:
        """
        Run fake detection using existing fake_detector.
        Returns dictionary with is_fake, fake_score, and reason.
        """
        try:
            is_fake, fake_score = self.detector.predict(title, description)
            reasons = []

            text = f"{title} {description}".lower()
            suspicious_keywords = ["unconfirmed", "hoax", "alien", "pink water", "conspiracy", "deepfake", "clickbait"]
            matched_keywords = [kw for kw in suspicious_keywords if kw in text]
            if matched_keywords:
                reasons.append(f"Contains suspicious keywords: {', '.join(matched_keywords)}")

            if fake_score >= 0.7:
                reasons.append(f"High misinformation probability score ({fake_score:.2f})")

            return {
                "is_fake": bool(is_fake),
                "fake_score": float(fake_score),
                "reason": "; ".join(reasons) if reasons else "Normal content patterns",
            }
        except Exception as exc:
            logger.error("Error running FakeNewsEngine: %s", exc)
            return {
                "is_fake": False,
                "fake_score": 0.0,
                "reason": f"Detection error fallback: {exc}",
            }


# Default shared instance
fake_news_engine = FakeNewsEngine()
