import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.weatherapi_collector import weatherapi_collector, WeatherAPICollector
from app.core.config import settings

SAMPLE_WEATHERAPI_RESPONSE = {
    "location": {
        "name": "Delhi",
        "region": "Delhi",
        "country": "India",
        "lat": 28.6139,
        "lon": 77.2090
    },
    "current": {
        "last_updated_epoch": 1700000000,
        "temp_c": 28.4,
        "condition": {"text": "Partly cloudy"},
        "wind_kph": 12.5,
        "wind_dir": "NW",
        "humidity": 65,
        "precip_mm": 0.0
    }
}


@pytest.mark.asyncio
async def test_weatherapi_disabled_configuration():
    collector = WeatherAPICollector()
    with patch.object(settings, "WEATHERAPI_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_weatherapi_missing_credentials():
    collector = WeatherAPICollector()
    with patch.object(settings, "WEATHERAPI_ENABLED", True):
        with patch.object(settings, "WEATHERAPI_API_KEY", ""):
            valid, msg = collector.validate_config()
            assert not valid
            assert "missing" in msg.lower()


def test_weatherapi_deterministic_event_id():
    collector = WeatherAPICollector()
    event = collector.normalize_observation(SAMPLE_WEATHERAPI_RESPONSE, "Delhi", "Delhi")
    import hashlib
    expected_id = hashlib.md5("weatherapi_Delhi_1700000000".encode("utf-8")).hexdigest()
    assert event["id"] == expected_id


def test_weatherapi_normalization():
    collector = WeatherAPICollector()
    event = collector.normalize_observation(SAMPLE_WEATHERAPI_RESPONSE, "Delhi", "Delhi")
    assert event["event_type"] == "weather_observation"
    assert event["source"] == "weatherapi"
    assert event["city"] == "Delhi"
    assert event["state"] == "Delhi"
    assert event["latitude"] == 28.6139
    assert event["longitude"] == 77.2090
    assert event["metadata"]["temp_c"] == 28.4
    assert event["verification_status"] == "SOURCE_REPORTED"
    assert event["pipeline"]["stage"] == "RAW"


@pytest.mark.asyncio
async def test_weatherapi_auth_failure():
    collector = WeatherAPICollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch.object(settings, "WEATHERAPI_ENABLED", True):
        with patch.object(settings, "WEATHERAPI_API_KEY", "invalid_key"):
            with patch("httpx.AsyncClient.get", return_value=mock_resp):
                events, results = await collector.fetch_and_publish_all()
                assert events == []
                assert collector.health_state == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_weatherapi_successful_response():
    collector = WeatherAPICollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_WEATHERAPI_RESPONSE

    with patch.object(settings, "WEATHERAPI_ENABLED", True):
        with patch.object(settings, "WEATHERAPI_API_KEY", "valid_key"):
            with patch("httpx.AsyncClient.get", return_value=mock_resp):
                with patch("app.collectors.weatherapi_collector.kafka_service.publish_raw_event", return_value=True):
                    events, results = await collector.fetch_and_publish_all()
                    assert len(events) > 0
                    assert events[0]["event_type"] == "weather_observation"
                    assert collector.health_state == "HEALTHY"
