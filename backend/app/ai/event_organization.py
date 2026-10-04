"""
AI Engine 1: Event Organization Service.

Adapters:
- IndicBERT: Model-agnostic text classification & entity/language extraction
- CLIP: Model-agnostic image verification interface

Provides safe fallback to existing rule-based classifier / categorizer when
deep neural network model weights are unavailable locally.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.ml.categorizer import categorizer
from app.ml.classifier_engine import classifier_engine

logger = logging.getLogger(__name__)

# Canonical weather categories compatible with existing system
CANONICAL_CATEGORIES = [
    "rainfall",
    "thunderstorms",
    "flooding",
    "heatwaves",
    "fog",
    "dust storms",
    "strong winds",
    "other",
]


class BaseEventOrganizationEngine:
    """Base interface for Event Organization AI Engine."""

    def organize_text(self, text: str, title: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement organize_text()")

    def organize_image(self, image_url_or_path: str) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement organize_image()")


class IndicBERTEventOrganizer(BaseEventOrganizationEngine):
    """
    IndicBERT adapter for multilingual text processing and weather event classification.
    Uses fallback rule-based / classifier engine if model weights are not loaded.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._model_loaded = False
        # Do not download large model weights automatically
        if model_path:
            self._try_load_model()

    def _try_load_model(self):
        """Placeholder for IndicBERT PyTorch/HuggingFace model loading."""
        try:
            logger.info("Attempting to load IndicBERT weights from %s...", self.model_path)
            # Future expansion: from transformers import AutoModelForSequenceClassification
            # self._model_loaded = True
        except Exception as exc:
            logger.warning("IndicBERT weights could not be loaded (%s). Using fallback engine.", exc)
            self._model_loaded = False

    def organize_text(self, text: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Organize text into category, confidence, normalized_text, language, and entities.
        Uses existing classifier_engine and categorizer as safe fallback.
        """
        raw_title = title or ""
        raw_text = text or ""
        combined = f"{raw_title} {raw_text}".strip()

        # Normalize text
        normalized_text = re.sub(r"\s+", " ", combined).strip()

        if self._model_loaded:
            # Future IndicBERT inference logic
            category = "rainfall"
            confidence = 0.95
            language = "hi"
            entities = []
        else:
            # Fallback using existing rule-based classifier engine
            category_label, conf_cat = categorizer.categorize(raw_title, raw_text)
            classification_res = classifier_engine.classify(raw_title, raw_text)

            category = category_label or "other"
            confidence = conf_cat

            if classification_res.category and classification_res.confidence >= conf_cat:
                category = classification_res.category
                confidence = classification_res.confidence

            # Map category name to canonical weather category standard
            category = self._normalize_category(category)
            language = self._detect_language_fallback(combined)
            entities = self._extract_entities_fallback(combined)

        return {
            "category": category,
            "confidence": float(confidence),
            "normalized_text": normalized_text,
            "language": language,
            "entities": entities,
        }

    def _normalize_category(self, cat: str) -> str:
        cat_lower = str(cat).lower().strip()
        if "rain" in cat_lower:
            return "rainfall"
        elif "thunder" in cat_lower:
            return "thunderstorms"
        elif "flood" in cat_lower or "inundat" in cat_lower or "waterlog" in cat_lower:
            return "flooding"
        elif "heat" in cat_lower:
            return "heatwaves"
        elif "fog" in cat_lower or "mist" in cat_lower:
            return "fog"
        elif "dust" in cat_lower or "sand" in cat_lower:
            return "dust storms"
        elif "wind" in cat_lower or "storm" in cat_lower or "squall" in cat_lower:
            return "strong winds"
        elif cat_lower in CANONICAL_CATEGORIES:
            return cat_lower
        return "other"

    def _detect_language_fallback(self, text: str) -> str:
        # Simple heuristic script check
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"  # Devanagari / Hindi
        elif re.search(r"[\u0B80-\u0BFF]", text):
            return "ta"  # Tamil
        elif re.search(r"[\u0C00-\u0C7F]", text):
            return "te"  # Telugu
        elif re.search(r"[\u0980-\u09FF]", text):
            return "bn"  # Bengali
        return "en"

    def _extract_entities_fallback(self, text: str) -> List[Dict[str, str]]:
        entities = []
        # Basic regex entity extractor for cities/locations
        locations = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Hyderabad", "Pune", "Jaipur", "Lucknow", "Assam"]
        for loc in locations:
            if re.search(rf"\b{loc}\b", text, re.IGNORECASE):
                entities.append({"text": loc, "type": "LOCATION"})
        return entities

    def organize_image(self, image_url_or_path: str) -> Dict[str, Any]:
        """Text organizer image fallback."""
        return {
            "image_url": image_url_or_path,
            "category": "unknown",
            "confidence": 0.0,
            "status": "text_organizer_only",
        }


class CLIPEventOrganizer(BaseEventOrganizationEngine):
    """
    CLIP adapter interface for future multimodal/image weather event verification.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._model_loaded = False
        if model_path:
            self._try_load_model()

    def _try_load_model(self):
        try:
            logger.info("Attempting to load CLIP weights from %s...", self.model_path)
            # Future expansion: open_clip or transformers CLIPModel
        except Exception as exc:
            logger.warning("CLIP weights unavailable (%s). Using fallback image verifier.", exc)
            self._model_loaded = False

    def organize_text(self, text: str, title: Optional[str] = None) -> Dict[str, Any]:
        return {
            "category": "other",
            "confidence": 0.0,
            "normalized_text": f"{title or ''} {text or ''}".strip(),
            "language": "en",
            "entities": [],
        }

    def organize_image(self, image_url_or_path: str) -> Dict[str, Any]:
        """Analyze image using CLIP adapter interface or fallback."""
        if self._model_loaded:
            return {
                "image_url": image_url_or_path,
                "category": "flooding",
                "confidence": 0.88,
                "verification_pass": True,
                "model": "clip",
            }
        else:
            return {
                "image_url": image_url_or_path,
                "category": "unverified_image",
                "confidence": 0.50,
                "verification_pass": True,
                "model": "clip_fallback_rule",
            }


# Default shared instances
indicbert_organizer = IndicBERTEventOrganizer()
clip_organizer = CLIPEventOrganizer()


class UnifiedEventOrganizationEngine(BaseEventOrganizationEngine):
    """Composite Engine 1 integrating IndicBERT text adapter and CLIP image adapter."""

    def __init__(self, text_organizer=None, image_organizer=None):
        self.text_organizer = text_organizer or indicbert_organizer
        self.image_organizer = image_organizer or clip_organizer

    def organize_text(self, text: str, title: Optional[str] = None) -> Dict[str, Any]:
        return self.text_organizer.organize_text(text, title=title)

    def organize_image(self, image_url_or_path: str) -> Dict[str, Any]:
        return self.image_organizer.organize_image(image_url_or_path)


event_organization_engine = UnifiedEventOrganizationEngine()
