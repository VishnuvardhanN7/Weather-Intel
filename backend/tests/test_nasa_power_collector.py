import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.nasa_power_collector import nasa_power_collector, NasaPowerCollector
from app.core.config import settings

SAMPLE_NASA_POWER_RESPONSE = {
    "properties": {
        "parameter": {
            "T2M": {"20261002": 31.5},
            "PRECTOTCORR": {"20261002": 12.4},
            "RH2M": {"20261002": 78.0},
            "WS10M": {"20261002": 15.2},
            "PS": {"20261002": 100.8}
        }
    }
}


@pytest.mark.asyncio
async def test_nasa_power_disabled_configuration():
    collector = NasaPowerCollector()
    with patch.object(settings, "NASA_POWER_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_nasa_power_config_validation():
    collector = NasaPowerCollector()
    with patch.object(settings, "NASA_POWER_ENABLED", True):
        valid, msg = collector.validate_config()
        assert valid


def test_nasa_power_deterministic_event_id():
    collector = NasaPowerCollector()
    city_info = {"city": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090}
    event = collector.normalize_point_observation(SAMPLE_NASA_POWER_RESPONSE, city_info, "20261002")
    assert event["id"] is not None
    assert "nasa_power_delhi_20261002" in event["id"]


def test_nasa_power_normalization():
    collector = NasaPowerCollector()
    city_info = {"city": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090}
    event = collector.normalize_point_observation(SAMPLE_NASA_POWER_RESPONSE, city_info, "20261002")
    assert event["event_type"] == "environmental_weather_observation"
    assert event["source"] == "nasa_power"
    assert event["city"] == "Delhi"
    assert event["state"] == "Delhi"
    assert event["latitude"] == 28.6139
    assert event["longitude"] == 77.2090
    assert event["metadata"]["temp_c"] == 31.5
    assert event["pipeline"]["stage"] == "RAW"


@pytest.mark.asyncio
async def test_nasa_power_malformed_response():
    collector = NasaPowerCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"invalid": "schema"}
    city_info = {"city": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090}

    with patch.object(settings, "NASA_POWER_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            event = await collector.fetch_location_data(MagicMock(), city_info)
            assert event is None


@pytest.mark.asyncio
async def test_nasa_power_timeout_handling():
    collector = NasaPowerCollector()
    city_info = {"city": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090}
    with patch.object(settings, "NASA_POWER_ENABLED", True):
        with patch("httpx.AsyncClient.get", side_effect=RequestError("Network timeout")):
            event = await collector.fetch_location_data(MagicMock(), city_info)
            assert event is None


@pytest.mark.asyncio
async def test_nasa_power_kafka_publication_no_direct_db():
    collector = NasaPowerCollector()
    city_info = {"city": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090}
    mock_events = [collector.normalize_point_observation(SAMPLE_NASA_POWER_RESPONSE, city_info, "20261002")]

    with patch.object(settings, "NASA_POWER_ENABLED", True):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = SAMPLE_NASA_POWER_RESPONSE
            mock_get.return_value = mock_resp

            with patch("app.collectors.nasa_power_collector.kafka_service.publish_raw_event", return_value=True) as mock_pub:
                events, results = await collector.fetch_and_publish_all()
                assert len(events) > 0
                assert all(results.values())
                mock_pub.assert_called()
                assert mock_pub.call_args[0][0]["source"] == "nasa_power"
