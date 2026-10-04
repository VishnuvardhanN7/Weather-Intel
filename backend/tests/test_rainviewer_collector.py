import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.rainviewer_collector import rainviewer_collector, RainViewerCollector
from app.core.config import settings

SAMPLE_RAINVIEWER_RESPONSE = {
    "version": "2.0",
    "generated": 1700000000,
    "host": "https://tilecache.rainviewer.com",
    "radar": {
        "past": [
            {"time": 1700000000, "path": "/v2/radar/1700000000/256/{z}/{x}/{y}/0/0_0.png"},
            {"time": 1700000300, "path": "/v2/radar/1700000300/256/{z}/{x}/{y}/0/0_0.png"}
        ],
        "nowcast": [
            {"time": 1700000600, "path": "/v2/radar/1700000600/256/{z}/{x}/{y}/0/0_0.png"}
        ]
    }
}


@pytest.mark.asyncio
async def test_rainviewer_disabled_configuration():
    collector = RainViewerCollector()
    with patch.object(settings, "RAINVIEWER_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_rainviewer_config_validation():
    collector = RainViewerCollector()
    with patch.object(settings, "RAINVIEWER_ENABLED", True):
        valid, msg = collector.validate_config()
        assert valid


def test_rainviewer_deterministic_event_id():
    collector = RainViewerCollector()
    frame = {"time": 1700000000, "path": "/v2/radar/1700000000/256/{z}/{x}/{y}/0/0_0.png"}
    event = collector.normalize_radar_frame(frame, "https://tilecache.rainviewer.com")
    assert event["id"] is not None
    assert "rainviewer_" in event["id"]


def test_rainviewer_normalization():
    collector = RainViewerCollector()
    frame = {"time": 1700000000, "path": "/v2/radar/1700000000/256/{z}/{x}/{y}/0/0_0.png"}
    event = collector.normalize_radar_frame(frame, "https://tilecache.rainviewer.com")
    assert event["event_type"] == "radar_observation"
    assert event["source"] == "rainviewer"
    assert event["city"] == "Pan-India Coverage"
    assert event["state"] == "India"
    assert event["latitude"] == 20.5937
    assert event["longitude"] == 78.9629
    assert event["verification_status"] == "SOURCE_REPORTED"
    assert event["pipeline"]["stage"] == "RAW"


@pytest.mark.asyncio
async def test_rainviewer_malformed_response():
    collector = RainViewerCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"invalid": "schema"}

    with patch.object(settings, "RAINVIEWER_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            events = await collector.fetch_radar_data()
            assert events == []


@pytest.mark.asyncio
async def test_rainviewer_timeout_handling():
    collector = RainViewerCollector()
    with patch.object(settings, "RAINVIEWER_ENABLED", True):
        with patch("httpx.AsyncClient.get", side_effect=RequestError("Network timeout")):
            events = await collector.fetch_radar_data()
            assert events == []
            assert collector.health_state == "DEGRADED"


@pytest.mark.asyncio
async def test_rainviewer_successful_response():
    collector = RainViewerCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_RAINVIEWER_RESPONSE

    with patch.object(settings, "RAINVIEWER_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            events = await collector.fetch_radar_data()
            assert len(events) == 3
            assert events[0]["event_type"] == "radar_observation"
            assert collector.health_state == "HEALTHY"


@pytest.mark.asyncio
async def test_rainviewer_kafka_publication_no_direct_db():
    collector = RainViewerCollector()
    frame = {"time": 1700000000, "path": "/v2/radar/1700000000/256/{z}/{x}/{y}/0/0_0.png"}
    mock_events = [collector.normalize_radar_frame(frame, "https://tilecache.rainviewer.com")]

    with patch.object(settings, "RAINVIEWER_ENABLED", True):
        with patch.object(collector, "fetch_radar_frames", return_value=mock_events):
            with patch("app.collectors.rainviewer_collector.kafka_service.publish_raw_event", return_value=True) as mock_pub:
                events, results = await collector.fetch_and_publish_all()
                assert len(events) == 1
                assert all(results.values())
                mock_pub.assert_called_once()
                assert mock_pub.call_args[0][0]["source"] == "rainviewer"
