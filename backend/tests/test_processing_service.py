"""
Unit tests for backend/app/services/processing_service.py.

Verifies:
1. Model-agnostic classifier adapter integration.
2. Reuse of classifier_engine, fake_detector, and deduplicator.
3. Graceful error handling and data safety.
4. Logical IngestionBuffer routing.
"""

import asyncio
import unittest
from typing import Tuple
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.processing_service import (
    ProcessingService,
    IngestionBuffer,
    BaseClassifierAdapter,
    RuleBasedClassifierAdapter,
    processing_service,
    ingestion_buffer,
)


class MockCustomAdapter(BaseClassifierAdapter):
    def classify(self, title: str, description: str) -> Tuple[str, float]:
        return "cyclone", 0.99


class TestEvent:
    def __init__(self, title: str, description: str):
        self.id = 1
        self.title = title
        self.description = description
        self.event_type = "other"
        self.category_confidence = 0.0
        self.is_fake = False
        self.fake_confidence = 0.0
        self.duplicate_of_id = None


class ProcessingServiceTests(unittest.TestCase):
    def test_classify_event_rule_based(self):
        cat, conf = processing_service.classify_event(
            "Cyclone Mocha landfall in Odisha tomorrow",
            "Severe cyclone with storm surge expected along the coast.",
        )
        self.assertEqual(cat, "cyclone")
        self.assertGreaterEqual(conf, 0.80)

    def test_run_fake_detection(self):
        is_fake, conf = processing_service.run_fake_detection(
            "URGENT FORWARD TO EVERYONE DEEPFAKE HOAX ALERT",
            "100% true government hiding pink water flood!! share before deleted",
        )
        self.assertTrue(is_fake)
        self.assertGreaterEqual(conf, 0.70)

    def test_model_agnostic_adapter_pluggability(self):
        custom_service = ProcessingService(classifier_adapter=MockCustomAdapter())
        cat, conf = custom_service.classify_event("Any weather text", "Description")
        self.assertEqual(cat, "cyclone")
        self.assertEqual(conf, 0.99)

    def test_graceful_error_handling_in_classification(self):
        failing_adapter = MagicMock()
        failing_adapter.classify.side_effect = Exception("Classifier crashed")
        svc = ProcessingService(classifier_adapter=failing_adapter)
        cat, conf = svc.classify_event("Title", "Desc")
        self.assertEqual(cat, "other")
        self.assertEqual(conf, 0.0)

    def test_graceful_error_handling_in_fake_detection(self):
        with patch("app.services.processing_service.fake_detector.predict", side_effect=Exception("Fake detector error")):
            is_fake, conf = processing_service.run_fake_detection("Title", "Desc")
            self.assertFalse(is_fake)
            self.assertEqual(conf, 0.0)

    def test_process_event_orchestration(self):
        event = TestEvent(
            "Heavy rain in Mumbai",
            "Continuous heavy rain causing waterlogging near Colaba.",
        )
        db_mock = MagicMock()
        with patch.object(processing_service, "check_duplicate", new=AsyncMock(return_value=None)):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                processed = loop.run_until_complete(processing_service.process_event(db_mock, event))
            finally:
                loop.close()

        self.assertIn(processed.event_type, ("rainfall", "flooding"))
        self.assertGreater(processed.category_confidence, 0.0)
        self.assertFalse(processed.is_fake)

    def test_ingestion_buffer_routing(self):
        event = TestEvent("Moderate rain in Jaipur", "Light to moderate rain recorded.")
        db_mock = MagicMock()
        with patch.object(processing_service, "process_event", new=AsyncMock(return_value=event)) as mock_process:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(ingestion_buffer.push_to_processing(db_mock, event))
            finally:
                loop.close()

            mock_process.assert_called_once_with(db_mock, event)
            self.assertEqual(result, event)


if __name__ == "__main__":
    unittest.main()
