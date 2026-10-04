"""
Comprehensive Test Suite for Kafka Streaming Pipeline, AI Engines, and Integration.

Tests cover:
1. Kafka configuration
2. Kafka message serialization
3. Raw topic publishing
4. Clean topic publishing
5. Verified topic publishing
6. Event schema compatibility
7. Event Organization fallback (IndicBERT & CLIP)
8. Fake News Engine (BaseFakeNewsEngine wrapper)
9. Deduplication Engine (BaseDeduplicationEngine wrapper)
10. Raw -> Processing -> Clean flow
11. JEV rejection (< 0.6)
12. JEV acceptance (>= 0.6)
13. Admin approval -> Verified topic
14. Admin rejection -> No verified event
15. Kafka disabled mode (KAFKA_ENABLED=False)
16. Existing RAG pipeline compatibility
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.kafka_service import kafka_service, ensure_event_id, KafkaService
from app.ai.event_organization import (
    IndicBERTEventOrganizer,
    CLIPEventOrganizer,
    event_organization_engine,
)
from app.ai.fake_news_engine import fake_news_engine
from app.ai.deduplication_engine import deduplication_engine
from app.spark.weather_stream_processor import process_event_with_ai_engines, weather_stream_processor
from app.models.weather_event import WeatherEvent, EventSource, EventType, SeverityLevel, VerificationStatus
from app.services.rag_service import evaluate_jev, search_rag_knowledge_base
from app.api.weather import _apply_verification_pipeline
from app.core.database import async_session_factory


@pytest.fixture
async def db_session():
    async with async_session_factory() as session:
        yield session



# 1. Kafka Configuration Test
def test_kafka_configuration():
    assert hasattr(settings, "KAFKA_ENABLED")
    assert hasattr(settings, "KAFKA_BOOTSTRAP_SERVERS")
    assert hasattr(settings, "KAFKA_RAW_TOPIC")
    assert hasattr(settings, "KAFKA_CLEAN_TOPIC")
    assert hasattr(settings, "KAFKA_VERIFIED_TOPIC")
    assert settings.KAFKA_RAW_TOPIC == "weather.raw"
    assert settings.KAFKA_CLEAN_TOPIC == "weather.clean"
    assert settings.KAFKA_VERIFIED_TOPIC == "weather.verified"
    assert settings.JEV_THRESHOLD == 0.6


# 2. Kafka Message Serialization Test
def test_kafka_message_serialization():
    raw_event = {"title": "Test Event", "city": "Bengaluru"}
    ensured = ensure_event_id(raw_event)
    assert "event_id" in ensured
    assert ensured["event_id"].startswith("weather_")
    assert "timestamp" in ensured

    serialized = json.dumps(ensured, default=str)
    deserialized = json.loads(serialized)
    assert deserialized["event_id"] == ensured["event_id"]
    assert deserialized["title"] == "Test Event"


# 3. Raw Topic Publishing Test
@patch("app.services.kafka_service.get_kafka_producer")
def test_publish_raw_event(mock_get_producer):
    mock_producer = MagicMock()
    mock_get_producer.return_value = mock_producer
    with patch.object(settings, "KAFKA_ENABLED", True):
        event = {"title": "Torrential Downpour", "city": "Mumbai"}
        success = kafka_service.publish_raw_event(event)
        assert success is True
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert args[0] == "weather.raw"


# 4. Clean Topic Publishing Test
@patch("app.services.kafka_service.get_kafka_producer")
def test_publish_clean_event(mock_get_producer):
    mock_producer = MagicMock()
    mock_get_producer.return_value = mock_producer
    with patch.object(settings, "KAFKA_ENABLED", True):
        event = {"event_id": "weather_clean_1", "clean_text": "Heavy Rains", "category": "rainfall"}
        success = kafka_service.publish_clean_event(event)
        assert success is True
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert args[0] == "weather.clean"


# 5. Verified Topic Publishing Test
@patch("app.services.kafka_service.get_kafka_producer")
def test_publish_verified_event(mock_get_producer):
    mock_producer = MagicMock()
    mock_get_producer.return_value = mock_producer
    with patch.object(settings, "KAFKA_ENABLED", True):
        event = {"event_id": "weather_verified_1", "verification_status": "VERIFIED", "category": "flooding"}
        success = kafka_service.publish_verified_event(event)
        assert success is True
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert args[0] == "weather.verified"


# 6. Event Schema Compatibility Test
def test_event_schema_compatibility():
    raw_event = {
        "event_id": "weather_test_schema",
        "source": "social_twitter",
        "timestamp": "2026-10-01T12:00:00Z",
        "title": "Severe Flash Flood in Guwahati",
        "description": "Rising Brahmaputra waters submerge main road.",
        "location": {"latitude": 26.1445, "longitude": 91.7362, "city": "Guwahati", "state": "Assam"},
        "media": ["http://example.com/flood.jpg"],
        "metadata": {"source_api": "twitter"},
    }
    clean = process_event_with_ai_engines(raw_event)
    assert clean["event_id"] == "weather_test_schema"
    assert clean["category"] == "flooding"
    assert clean["processing_status"] == "CLEAN"
    assert "location" in clean
    assert clean["location"]["city"] == "Guwahati"


# 7. Event Organization Fallback Test (IndicBERT & CLIP)
def test_event_organization_fallback():
    indicbert = IndicBERTEventOrganizer()
    res_text = indicbert.organize_text("Heavy thunderstorm warning and dark clouds in Pune", title="Thunderstorm")
    assert res_text["category"] == "thunderstorms"
    assert res_text["confidence"] > 0.0
    assert "normalized_text" in res_text
    assert "language" in res_text

    clip = CLIPEventOrganizer()
    res_img = clip.organize_image("http://example.com/rain.jpg")
    assert "verification_pass" in res_img


# 8. Fake News Engine Wrapper Test
def test_fake_news_engine():
    res_fake = fake_news_engine.detect_fake_news("UNCONFIRMED HOAX", "Pink water alien flood hoax claim")
    assert res_fake["is_fake"] is True
    assert res_fake["fake_score"] >= 0.7

    res_real = fake_news_engine.detect_fake_news("Monsoon Update", "Normal 25mm rain recorded in IMD station")
    assert res_real["is_fake"] is False


# 9. Deduplication Engine Wrapper Test
def test_deduplication_engine():
    existing = [{"event_id": "weather_101", "title": "Heavy rain in Mumbai", "location": {"city": "Mumbai"}}]
    event_new = {"event_id": "weather_102", "title": "Heavy rain in Mumbai", "location": {"city": "Mumbai"}}
    res = deduplication_engine.check_duplicate_dict(event_new, existing_events=existing)
    assert res["is_duplicate"] is True
    assert res["duplicate_of_id"] == "weather_101"


# 10. Raw -> Processing -> Clean Flow Test
def test_raw_to_processing_to_clean_flow():
    raw_event = {
        "event_id": "weather_flow_1",
        "title": "Severe Heatwave Alert",
        "description": "Temperature crosses 44 degrees in Nagpur",
        "city": "Nagpur",
    }
    clean_event = process_event_with_ai_engines(raw_event)
    assert clean_event["category"] == "heatwaves"
    assert clean_event["is_fake"] is False
    assert clean_event["processing_status"] == "CLEAN"


from app.core.database import async_session_factory, engine


def _run_async(coro_fn):
    """Execute coroutine with a fresh event loop."""
    asyncio.run(coro_fn())



# 11. JEV Rejection Test (< 0.6)
@pytest.mark.asyncio
async def test_jev_rejection():
    async with async_session_factory() as db:
        event = WeatherEvent(
            title="UNCONFIRMED FAKE FLOOD REPORT!! HOAX!!",
            description="Aliens flooded city with pink water! Completely fake rumor fake fake fake.",
            event_type="flooding",
            severity=SeverityLevel.LOW,
            source=EventSource.CITIZEN_REPORT,
            verification_status=VerificationStatus.PENDING,
            fake_confidence=0.95,
            is_fake=True,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        jev_info = await evaluate_jev(event, db=db)
        assert jev_info["probability"] < settings.JEV_THRESHOLD
        assert event.verification_status == VerificationStatus.REJECTED

        await db.delete(event)
        await db.commit()


# 12. JEV Acceptance Test (>= 0.6)
@pytest.mark.asyncio
async def test_jev_acceptance():
    async with async_session_factory() as db:
        event = WeatherEvent(
            title="Heavy Rainfall in Colaba Mumbai",
            description="Continuous heavy monsoon rains cause 100mm rainfall near Colaba.",
            event_type="rainfall",
            severity=SeverityLevel.HIGH,
            source=EventSource.API,
            verification_status=VerificationStatus.PENDING,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        jev_info = await evaluate_jev(event, db=db)
        assert jev_info["probability"] >= settings.JEV_THRESHOLD

        await db.delete(event)
        await db.commit()


# 13. Admin Approval -> Verified Topic Test
@pytest.mark.asyncio
@patch("app.services.kafka_service.KafkaService.publish_verified_event")
async def test_admin_approval_publishes_verified(mock_publish_verified):
    async with async_session_factory() as db:
        with patch.object(settings, "KAFKA_ENABLED", True):
            event = WeatherEvent(
                title="Heavy Rain in Mumbai",
                description="Verified monsoon showers.",
                event_type="rainfall",
                severity=SeverityLevel.HIGH,
                source=EventSource.API,
                verification_status=VerificationStatus.PENDING,
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)

            await _apply_verification_pipeline(event, VerificationStatus.VERIFIED, db)
            assert event.verification_status == VerificationStatus.VERIFIED
            mock_publish_verified.assert_called_once()

            await db.delete(event)
            await db.commit()


# 14. Admin Rejection -> No Verified Event Test
@pytest.mark.asyncio
@patch("app.services.kafka_service.KafkaService.publish_verified_event")
async def test_admin_rejection_no_verified_published(mock_publish_verified):
    async with async_session_factory() as db:
        with patch.object(settings, "KAFKA_ENABLED", True):
            event = WeatherEvent(
                title="Spam Report",
                description="Fake marketing ad.",
                event_type="other",
                severity=SeverityLevel.LOW,
                source=EventSource.CITIZEN_REPORT,
                verification_status=VerificationStatus.PENDING,
            )
            db.add(event)
            await db.commit()

            await _apply_verification_pipeline(event, VerificationStatus.REJECTED, db)
            assert event.verification_status == VerificationStatus.REJECTED
            mock_publish_verified.assert_not_called()

            await db.delete(event)
            await db.commit()


# 15. Kafka Disabled Mode Test
def test_kafka_disabled_mode():
    with patch.object(settings, "KAFKA_ENABLED", False):
        published = kafka_service.publish_raw_event({"title": "Disabled Test"})
        assert published is False
        events = kafka_service.consume_raw_events()
        assert events == []


# 16. Existing RAG Pipeline Test
@pytest.mark.asyncio
async def test_existing_rag_pipeline():
    async with async_session_factory() as db:
        event = WeatherEvent(
            title="Severe Thunderstorm in Bengaluru",
            description="High winds and heavy rain recorded near MG Road.",
            event_type="thunderstorm",
            severity=SeverityLevel.HIGH,
            source=EventSource.API,
            verification_status=VerificationStatus.VERIFIED,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        await _apply_verification_pipeline(event, VerificationStatus.VERIFIED, db)
        docs, _ = await search_rag_knowledge_base(db, "Thunderstorm in Bengaluru", top_k=5)
        retrieved_ids = [d["event_id"] for d in docs]
        assert event.id in retrieved_ids

        await db.delete(event)
        await db.commit()



# 17. Confluent-Kafka Consumer Helper Test
@patch("confluent_kafka.Consumer")
def test_confluent_kafka_consumer_helper(mock_consumer_cls):
    mock_consumer = MagicMock()
    mock_consumer_cls.return_value = mock_consumer

    mock_msg = MagicMock()
    mock_msg.error.return_value = None
    mock_msg.value.return_value = json.dumps({"event_id": "test_ck_1", "title": "Confluent Test"}).encode("utf-8")

    mock_consumer.consume.return_value = [mock_msg]

    with patch.object(settings, "KAFKA_ENABLED", True):
        events = kafka_service.consume_raw_events(max_records=5, timeout_ms=1000)
        assert len(events) == 1
        assert events[0]["event_id"] == "test_ck_1"
        mock_consumer.subscribe.assert_called_once_with(["weather.raw"])
        mock_consumer.consume.assert_called_once_with(num_messages=5, timeout=1.0)
        mock_consumer.close.assert_called_once()


# 18. JEV Processor Kafka Disabled Fallback Test
def test_jev_processor_kafka_disabled_fallback():
    from app.services.streaming_pipeline import jev_stream_processor
    clean_evt = {
        "event_id": "test_fallback_1",
        "source": "api",
        "title": "Severe Rainstorm in Bengaluru",
        "description": "Heavy rainfall 80mm recorded near MG Road",
        "severity": "high",
        "is_fake": False,
        "fake_score": 0.0,
    }
    with patch.object(settings, "KAFKA_ENABLED", False):
        res = jev_stream_processor.process_clean_event(clean_evt)
        assert res is not None
        assert res["event_id"] == "test_fallback_1"
        assert res["jev_probability"] >= 0.60
        assert res["alertness_score"] > 0.90





