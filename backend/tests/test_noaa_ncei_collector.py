import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.noaa_ncei_collector import noaa_ncei_collector, NOAACollector
from app.core.config import settings

SAMPLE_NOAA_RESPONSE = {
    "results": [
        {
            "date": "2026-10-02T00:00:00",
            "datatype": "TMAX",
            "station": "GHCND:IN001010100",
            "value": 320
        },
        {
            "date": "2026-10-02T00:00:00",
            "datatype": "PRCP",
            "station": "GHCND:IN001010100",
            "value": 45
        }
    ]
}


@pytest.mark.asyncio
async def test_noaa_disabled_configuration():
    collector = NOAACollector()
    with patch.object(settings, "NOAA_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_noaa_missing_credentials():
    collector = NOAACollector()
    with patch.object(settings, "NOAA_ENABLED", True):
        with patch.object(settings, "NOAA_API_KEY", ""):
            valid, msg = collector.validate_config()
            assert not valid
            assert "missing" in msg.lower()


def test_noaa_deterministic_event_id():
    collector = NOAACollector()
    obs = SAMPLE_NOAA_RESPONSE["results"][0]
    event = collector.normalize_observation(obs)
    assert event["id"] is not None
    assert "noaa_" in event["id"]


def test_noaa_normalization():
    collector = NOAACollector()
    obs = SAMPLE_NOAA_RESPONSE["results"][0]
    event = collector.normalize_observation(obs)
    assert event["event_type"] == "climate_weather"
    assert event["source"] == "noaa_ncei"
    assert event["verification_status"] == "SOURCE_REPORTED"
    assert event["pipeline"]["stage"] == "RAW"


@pytest.mark.asyncio
async def test_noaa_auth_failure():
    collector = NOAACollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch.object(settings, "NOAA_ENABLED", True):
        with patch.object(settings, "NOAA_API_KEY", "invalid_key"):
            with patch("httpx.AsyncClient.get", return_value=mock_resp):
                events, results = await collector.fetch_and_publish_all()
                assert events == []
                assert collector.health_state == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_noaa_successful_response():
    collector = NOAACollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_NOAA_RESPONSE

    with patch.object(settings, "NOAA_ENABLED", True):
        with patch.object(settings, "NOAA_API_KEY", "valid_token"):
            with patch("httpx.AsyncClient.get", return_value=mock_resp):
                with patch("app.collectors.noaa_ncei_collector.kafka_service.publish_raw_event", return_value=True):
                    events, results = await collector.fetch_and_publish_all()
                    assert len(events) == 2
                    assert collector.health_state == "HEALTHY"
