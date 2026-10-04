import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.openaq_collector import openaq_collector, OpenAQCollector
from app.core.config import settings

SAMPLE_OPENAQ_RESPONSE = {
    "results": [
        {
            "id": 12345,
            "location": "Anand Vihar, Delhi",
            "parameter": "pm25",
            "value": 185.2,
            "unit": "µg/m³",
            "date": {"utc": "2026-10-02T06:00:00Z"},
            "coordinates": {"latitude": 28.6469, "longitude": 77.3162},
            "city": "Delhi",
            "country": "IN"
        }
    ]
}


@pytest.mark.asyncio
async def test_openaq_disabled_configuration():
    collector = OpenAQCollector()
    with patch.object(settings, "OPENAQ_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_openaq_deterministic_event_id():
    collector = OpenAQCollector()
    meas = SAMPLE_OPENAQ_RESPONSE["results"][0]
    event = collector.normalize_measurement(meas)
    assert event["id"] is not None
    assert "openaq_" in event["id"]


def test_openaq_normalization():
    collector = OpenAQCollector()
    meas = SAMPLE_OPENAQ_RESPONSE["results"][0]
    event = collector.normalize_measurement(meas)
    assert event["event_type"] == "air_quality_observation"
    assert event["source"] == "openaq"
    assert event["city"] == "Delhi"
    assert event["latitude"] == 28.6469
    assert event["longitude"] == 77.3162
    assert event["metadata"]["parameter"] == "pm25"
    assert event["metadata"]["value"] == 185.2
    assert event["verification_status"] == "SOURCE_REPORTED"


@pytest.mark.asyncio
async def test_openaq_rate_limit_handling():
    collector = OpenAQCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch.object(settings, "OPENAQ_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            events, results = await collector.fetch_and_publish_all()
            assert events == []
            assert collector.health_state == "DEGRADED"


@pytest.mark.asyncio
async def test_openaq_successful_response():
    collector = OpenAQCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_OPENAQ_RESPONSE

    with patch.object(settings, "OPENAQ_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            with patch("app.collectors.openaq_collector.kafka_service.publish_raw_event", return_value=True):
                events, results = await collector.fetch_and_publish_all()
                assert len(events) == 1
                assert events[0]["event_type"] == "air_quality_observation"
                assert collector.health_state == "HEALTHY"
