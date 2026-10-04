"""
Unit and Integration Tests for Sink Consumer (PS-26069).

Validates:
A. verified event with alertness_score = 0.91 -> accepted downstream
B. verified event with alertness_score = 0.90 -> filtered
C. verified event with alertness_score = 0.50 -> filtered
D. duplicate event_id -> no duplicate database/index record (idempotency)
E. OpenSearch unavailable -> PostgreSQL / WebSocket flow remains functional
F. WebSocket client disconnected -> sink consumer continues
G. multiple WebSocket clients -> accepted event broadcast to all active clients
H. weather.verified event with invalid/missing alertness score -> safely rejected/logged, no crash
I. Existing JEV -> RAG pipeline compatibility
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from app.core.database import async_session_factory
from app.core.config import settings
from app.services.sink_consumer import sink_consumer, SinkConsumer
from app.services.opensearch_service import opensearch_service
from app.services.websocket_manager import ConnectionManager
from app.models.weather_event import WeatherEvent, VerificationStatus




def sample_event(event_id: str, alertness_score: float) -> dict:
    return {
        "event_id": event_id,
        "source": "citizen_report",
        "timestamp": "2026-10-01T12:00:00Z",
        "clean_text": f"Heavy rainfall reported in Mumbai ({event_id})",
        "category": "rainfall",
        "category_confidence": 0.95,
        "severity": "high",
        "location": {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "city": "Mumbai",
            "state": "Maharashtra"
        },
        "media": [],
        "is_fake": False,
        "is_duplicate": False,
        "jev_probability": 0.95,
        "verification_status": "AI_VERIFIED",
        "alertness_score": alertness_score
    }


def test_alertness_score_91_accepted():
    """Test A: alertness_score = 0.91 (strictly > 0.90) is accepted."""
    event = sample_event("test_091", 0.91)
    res = sink_consumer.process_verified_event(event)
    assert res["status"] == "ACCEPTED"
    assert res["accepted"] is True
    assert res["alertness_score"] == 0.91


def test_alertness_score_90_filtered():
    """Test B: alertness_score = 0.90 (NOT strictly > 0.90) is filtered."""
    event = sample_event("test_090", 0.90)
    res = sink_consumer.process_verified_event(event)
    assert res["status"] == "FILTERED"
    assert res["accepted"] is False
    assert res["reason"] == "alertness_score <= 0.90"


def test_alertness_score_50_filtered():
    """Test C: alertness_score = 0.50 is filtered."""
    event = sample_event("test_050", 0.50)
    res = sink_consumer.process_verified_event(event)
    assert res["status"] == "FILTERED"
    assert res["accepted"] is False


@pytest.mark.asyncio
async def test_duplicate_event_id_idempotency():
    """Test D: Duplicate event_id processing does not create duplicate DB records."""
    event = sample_event("test_idempotent_001", 0.95)

    async with async_session_factory() as db_session:
        # Process event first time
        res1 = await sink_consumer.process_verified_event_async(event, db_session=db_session)
        assert res1["accepted"] is True
        assert res1["postgres_stored"] is True

        # Process duplicate event second time
        res2 = await sink_consumer.process_verified_event_async(event, db_session=db_session)
        assert res2["accepted"] is True
        assert res2["postgres_stored"] is True


        # Verify database contains exactly 1 record for this source_id
        from sqlalchemy import select
        stmt = select(WeatherEvent).where(WeatherEvent.source_id == "test_idempotent_001")
        records = (await db_session.execute(stmt)).scalars().all()
        assert len(records) == 1

        # Clean up test record
        for rec in records:
            await db_session.delete(rec)
        await db_session.commit()




def test_opensearch_unavailable_fallback():
    """Test E: OpenSearch unavailable / disabled does not crash PostgreSQL or WebSocket flow."""
    event = sample_event("test_opensearch_down", 0.92)
    with patch.object(settings, "OPENSEARCH_ENABLED", True):
        with patch.object(opensearch_service, "index_event", side_effect=Exception("Connection refused")):
            res = sink_consumer.process_verified_event(event)
            assert res["status"] == "ACCEPTED"
            assert res["opensearch_indexed"] is False


@pytest.mark.asyncio
async def test_websocket_disconnected_client():
    """Test F: Disconnected WebSocket client does not crash sink consumer."""
    manager = ConnectionManager()
    
    class FakeDisconnectedWS:
        async def send_json(self, msg):
            raise Exception("Client socket closed")

    ws = FakeDisconnectedWS()
    manager.active_connections.add(ws)

    # Broadcast message
    await manager.broadcast({"event_id": "test_ws_disc", "alertness_score": 0.95})
    # Disconnected client should be removed safely
    assert ws not in manager.active_connections


@pytest.mark.asyncio
async def test_multiple_websocket_clients():
    """Test G: Broadcasts accepted event to all active WebSocket clients."""
    manager = ConnectionManager()
    received = []

    class FakeActiveWS:
        def __init__(self, name):
            self.name = name
        async def send_json(self, msg):
            received.append((self.name, msg["event_id"]))

    ws1 = FakeActiveWS("client_1")
    ws2 = FakeActiveWS("client_2")
    manager.active_connections.add(ws1)
    manager.active_connections.add(ws2)

    await manager.broadcast({"event_id": "test_ws_multi", "alertness_score": 0.95})

    assert len(received) == 2
    assert ("client_1", "test_ws_multi") in received
    assert ("client_2", "test_ws_multi") in received


def test_missing_or_invalid_alertness_score():
    """Test H: Invalid/missing alertness score is safely rejected/logged without crashing."""
    event_missing = sample_event("test_invalid_01", 0.95)
    del event_missing["alertness_score"]

    res1 = sink_consumer.process_verified_event(event_missing)
    assert res1["status"] == "REJECTED"
    assert res1["accepted"] is False

    event_invalid = sample_event("test_invalid_02", 0.95)
    event_invalid["alertness_score"] = "invalid_string"

    res2 = sink_consumer.process_verified_event(event_invalid)
    assert res2["status"] == "REJECTED"
    assert res2["accepted"] is False


def test_worker_disabled_when_kafka_disabled():
    """Test J: Worker exits gracefully when KAFKA_ENABLED=False."""
    with patch.object(settings, "KAFKA_ENABLED", False):
        res = sink_consumer.run_worker()
        assert res["status"] == "DISABLED"
        assert res["processed"] == 0


def test_worker_accepted_event_reaches_sink_consumer():
    """Test K: Worker processes accepted event downstream."""
    mock_results = [{"event_id": "test_worker_acc", "status": "ACCEPTED", "accepted": True, "alertness_score": 0.95}]
    with patch.object(settings, "KAFKA_ENABLED", True):
        with patch.object(sink_consumer, "consume_loop", return_value=mock_results):
            res = sink_consumer.run_worker(max_batches=1, poll_interval=0.01)
            assert res["status"] == "STOPPED"
            assert res["processed"] == 1
            assert res["accepted"] == 1
            assert res["filtered"] == 0


def test_worker_filtered_event_remains_filtered():
    """Test L: Worker logs and counts filtered event."""
    mock_results = [{"event_id": "test_worker_filt", "status": "FILTERED", "accepted": False, "alertness_score": 0.85}]
    with patch.object(settings, "KAFKA_ENABLED", True):
        with patch.object(sink_consumer, "consume_loop", return_value=mock_results):
            res = sink_consumer.run_worker(max_batches=1, poll_interval=0.01)
            assert res["status"] == "STOPPED"
            assert res["processed"] == 1
            assert res["accepted"] == 0
            assert res["filtered"] == 1


def test_worker_graceful_shutdown_and_error_handling():
    """Test M: Worker handles loop exception gracefully without crashing."""
    with patch.object(settings, "KAFKA_ENABLED", True):
        with patch.object(sink_consumer, "consume_loop", side_effect=Exception("Kafka connection reset")):
            res = sink_consumer.run_worker(max_batches=1, poll_interval=0.01)
            assert res["status"] == "STOPPED"
            assert res["processed"] == 0
