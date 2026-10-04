"""
Processing Layer Orchestration Service.

Acts as the unified orchestration service for the Processing Layer:
- Event Organization / Classification (model-agnostic adapter wrapping classifier_engine)
- Misinformation / Fake News Detection (reusing fake_detector)
- Deduplication (reusing deduplicator)

Logical Ingestion Buffer:
Provides an application-level boundary abstraction between Ingestion (Collectors) and Processing.
"""

import logging
from typing import Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.classifier_engine import classifier_engine
from app.ml.categorizer import categorizer
from app.ml.fake_detector import fake_detector
from app.ml.deduplicator import deduplicator

logger = logging.getLogger(__name__)


class BaseClassifierAdapter:
    """
    Model-agnostic classifier interface / base adapter.
    Enables future replacement with fine-tuned BERT models or other classifier architectures
    without redesigning or modifying the processing pipeline orchestration logic.
    """
    def classify(self, title: str, description: str) -> Tuple[str, float]:
        raise NotImplementedError("Classifier adapters must implement classify()")


class RuleBasedClassifierAdapter(BaseClassifierAdapter):
    """
    Model-agnostic adapter wrapping existing ClassifierEngine and Categorizer implementations.
    """
    def classify(self, title: str, description: str) -> Tuple[str, float]:
        category_label, conf_cat = categorizer.categorize(title, description)
        classification_res = classifier_engine.classify(title, description)

        event_type = category_label or "other"
        final_conf = conf_cat

        if classification_res.category and classification_res.confidence >= conf_cat:
            event_type = classification_res.category
            final_conf = classification_res.confidence

        return event_type, float(final_conf)


class ProcessingService:
    """
    Processing Layer Orchestrator service.

    Pipeline stages:
      Event Received
      → Event Organization / Classification
      → Fake News Detection
      → Deduplication
      → Processing Completed
    """

    def __init__(self, classifier_adapter: Optional[BaseClassifierAdapter] = None):
        self.classifier = classifier_adapter or RuleBasedClassifierAdapter()

    def classify_event(self, title: str, description: str) -> Tuple[str, float]:
        """
        Run event organization / classification.
        Reuses existing classifier_engine / categorizer via model-agnostic adapter.
        """
        try:
            return self.classifier.classify(title, description)
        except Exception as exc:
            logger.error("Error during classify_event stage: %s", exc)
            return "other", 0.0

    def run_fake_detection(self, title: str, description: str) -> Tuple[bool, float]:
        """
        Run misinformation and fake news detection.
        Reuses existing fake_detector implementation.
        """
        try:
            return fake_detector.predict(title, description)
        except Exception as exc:
            logger.error("Error during run_fake_detection stage: %s", exc)
            # Data Safety: Fail gracefully, return safe neutral state without bypassing verification
            return False, 0.0

    async def check_duplicate(self, db: AsyncSession, event: Any) -> Optional[Any]:
        """
        Run deduplication check against database.
        Reuses existing deduplicator implementation.
        """
        try:
            return await deduplicator.find_duplicate(db, event)
        except Exception as exc:
            event_id = getattr(event, 'id', 'new')
            logger.error("Error during check_duplicate stage for event %s: %s", event_id, exc)
            return None

    async def process_event(self, db: AsyncSession, event: Any) -> Any:
        """
        Orchestrate complete processing pipeline for an incoming weather event.
        Logs every stage cleanly and handles component failures gracefully.
        """
        title = getattr(event, 'title', '') or ''
        description = getattr(event, 'description', '') or ''

        logger.info("ProcessingService: event received -> title: '%s'", title[:60])

        # Stage 1: Event Organization / Classification
        try:
            cat, cat_conf = self.classify_event(title, description)
            if hasattr(event, 'event_type'):
                setattr(event, 'event_type', cat)
            if hasattr(event, 'category_confidence'):
                setattr(event, 'category_confidence', cat_conf)
            logger.info("ProcessingService: -> classification category: '%s', confidence: %.3f", cat, cat_conf)
        except Exception as exc:
            logger.error("ProcessingService: classification stage error for '%s': %s", title[:60], exc)

        # Stage 2: Fake News Detection
        try:
            is_fake, fake_conf = self.run_fake_detection(title, description)
            if hasattr(event, 'is_fake'):
                setattr(event, 'is_fake', is_fake)
            if hasattr(event, 'fake_confidence'):
                setattr(event, 'fake_confidence', fake_conf)
            logger.info("ProcessingService: -> fake-news result: is_fake=%s, confidence: %.3f", is_fake, fake_conf)
        except Exception as exc:
            logger.error("ProcessingService: fake-news stage error for '%s': %s", title[:60], exc)

        # Stage 3: Deduplication
        try:
            duplicate = await self.check_duplicate(db, event)
            if duplicate:
                dup_id = getattr(duplicate, 'id', None)
                if hasattr(event, 'duplicate_of_id'):
                    setattr(event, 'duplicate_of_id', dup_id)
                logger.info("ProcessingService: -> deduplication result: duplicate found (ID %s)", dup_id)
            else:
                logger.info("ProcessingService: -> deduplication result: unique event (no duplicate)")
        except Exception as exc:
            logger.error("ProcessingService: deduplication stage error for '%s': %s", title[:60], exc)

        logger.info("ProcessingService: -> processing completed for event '%s'", title[:60])
        return event


class IngestionBuffer:
    """
    Logical / application-level boundary between ingestion collectors and processing service.
    Exposes push_to_processing interface without changing storage or transport layer.
    """
    def __init__(self, service: ProcessingService):
        self._service = service

    async def push_to_processing(self, db: AsyncSession, event: Any) -> Any:
        """Pass event across logical boundary into Processing Layer orchestration."""
        logger.debug("IngestionBuffer: Passing event into Processing Layer")
        return await self._service.process_event(db, event)


processing_service = ProcessingService()
ingestion_buffer = IngestionBuffer(processing_service)
