import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import Response, RequestError, HTTPStatusError

from app.collectors.open_meteo_collector import open_meteo_collector, OpenMeteoCollector, generate_deterministic_event_id
from app.services.source_registry import SOURCE_REGISTRY, metrics_tracker, get_source_metadata
from app.core.location_registry import INDIAN_LOCATIONS, get_locations_by_names


SAMPLE_MULTI_LOCATION_RESPONSE = [
    {
        "latitude": 28.61,
        "longitude": 77.2,
        "timezone": "Asia/Kolkata",
        "current": {
            "time": "2026-10-02T12:00",
            "interval": 900,
            "temperature_2m": 28.5,
            "relative_humidity_2m": 65,
            "apparent_temperature": 30.2,
            "precipitation": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "weather_code": 1,
            "cloud_cover": 20,
            "visibility": 9000,
            "wind_speed_10m": 3.6,
            "wind_direction_10m": 120,
            "wind_gusts_10m": 5.4,
            "surface_pressure": 1012,
        }
    },
    {
        "latitude": 19.07,
        "longitude": 72.87,
        "timezone": "Asia/Kolkata",
        "current": {
            "time": "2026-10-02T12:00",
            "interval": 900,
            "temperature_2m": 31.0,
            "relative_humidity_2m": 78,
            "apparent_temperature": 36.5,
            "precipitation": 12.4,
            "rain": 12.4,
            "showers": 0.0,
            "weather_code": 63,
            "cloud_cover": 85,
            "visibility": 5000,
            "wind_speed_10m": 6.8,
            "wind_direction_10m": 240,
            "wind_gusts_10m": 11.2,
            "surface_pressure": 1008,
        }
    }
]

SAMPLE_HISTORICAL_RESPONSE = {
    "latitude": 28.61,
    "longitude": 77.2,
    "timezone": "Asia/Kolkata",
    "hourly": {
        "time": ["2025-01-01T00:00", "2025-01-01T01:00"],
        "temperature_2m": [12.4, 11.8],
        "relative_humidity_2m": [82, 85],
        "precipitation": [0.0, 0.0],
        "rain": [0.0, 0.0],
        "weather_code": [45, 45],
        "wind_speed_10m": [1.5, 1.2],
    }
}


# 1. Request Construction & Batching
@pytest.mark.asyncio
async def test_open_meteo_request_construction_and_batching():
    """Verify batching multiple coordinates into single HTTP requests."""
    collector = OpenMeteoCollector()
    locations = get_locations_by_names(["Delhi", "Mumbai"])
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_MULTI_LOCATION_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
        events = await collector.fetch_current_batch(locations)
        assert len(events) == 2
        mock_get.assert_called_once()
        
        # Verify URL parameters contain coordinate list
        params_called = mock_get.call_args[1].get("params", {})
        assert "28.6139" in params_called.get("latitude", "")
        assert "77.209" in params_called.get("longitude", "")


# 2. Response Normalization & Routine Weather Classification
def test_open_meteo_normalization_routine_weather():
    """Verify conversion of Open-Meteo current payload into normalized event schema with routine observation status."""
    collector = OpenMeteoCollector()
    loc = INDIAN_LOCATIONS[0]  # Delhi
    raw_data = SAMPLE_MULTI_LOCATION_RESPONSE[0]

    event = collector.normalize_current_observation(loc=loc, raw=raw_data)

    assert event["event_id"].startswith("weather_open_meteo_delhi_")
    assert event["source"] == "open_meteo"
    assert event["source_metadata"]["provider"] == "Open-Meteo"
    assert event["source_metadata"]["collector"] == "open_meteo_collector"
    assert event["location"]["city"] == "Delhi"
    assert event["location"]["state"] == "Delhi"
    assert event["weather"]["temperature"] == 28.5
    assert event["weather"]["humidity"] == 65
    assert event["event_type"] == "weather_observation"
    assert event["severity"] == "low"
    assert event["pipeline"]["stage"] == "RAW"


# 3. Missing Values & Robust Defaults
def test_open_meteo_missing_values():
    """Verify collector gracefully handles missing/null weather fields."""
    collector = OpenMeteoCollector()
    loc = INDIAN_LOCATIONS[0]
    sparse_raw = {
        "current": {
            "time": "2026-10-02T12:00",
            "temperature_2m": None,
            "relative_humidity_2m": None,
            "precipitation": None,
        }
    }

    event = collector.normalize_current_observation(loc=loc, raw=sparse_raw)
    assert event["weather"]["temperature"] == 0.0
    assert event["weather"]["humidity"] is None
    assert event["weather"]["precipitation"] == 0.0
    assert event["event_type"] == "weather_observation"


# 4. Invalid API Response & Exceptions
@pytest.mark.asyncio
async def test_open_meteo_invalid_api_response():
    """Verify collector returns empty list on invalid status or bad JSON."""
    collector = OpenMeteoCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = HTTPStatusError("Server error", request=MagicMock(), response=mock_resp)

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_current_batch(INDIAN_LOCATIONS[:2])
        assert events == []


# 5. Retry & Backoff Mechanics
@pytest.mark.asyncio
async def test_open_meteo_timeout_retry():
    """Verify collector retries up to max_retries on timeout/connect error."""
    collector = OpenMeteoCollector()
    
    with patch("httpx.AsyncClient.get", side_effect=RequestError("Network timeout")):
        events = await collector.fetch_current_batch(INDIAN_LOCATIONS[:2], max_retries=2)
        assert events == []


# 6. Deterministic Event IDs & Idempotency
def test_deterministic_event_ids():
    """Verify same city and timestamp produces identical event_id."""
    collector = OpenMeteoCollector()
    loc = INDIAN_LOCATIONS[0]
    raw_data = {"current": {"time": "2026-10-02T12:00"}}
    
    e1 = collector.normalize_current_observation(loc=loc, raw=raw_data)
    e2 = collector.normalize_current_observation(loc=loc, raw=raw_data)

    assert e1["event_id"] == e2["event_id"]
    assert "weather_open_meteo_delhi_" in e1["event_id"]


# 7. Kafka RAW Publishing
@pytest.mark.asyncio
async def test_open_meteo_kafka_raw_publishing():
    """Verify normalized events are published directly to Kafka weather.raw topic."""
    collector = OpenMeteoCollector()
    mock_events = [
        collector.normalize_current_observation(INDIAN_LOCATIONS[0], SAMPLE_MULTI_LOCATION_RESPONSE[0]),
        collector.normalize_current_observation(INDIAN_LOCATIONS[1], SAMPLE_MULTI_LOCATION_RESPONSE[1]),
    ]

    with patch("app.collectors.open_meteo_collector.open_meteo_collector.fetch_current_batch", return_value=mock_events):
        with patch("app.services.kafka_service.kafka_service.publish_raw_event", return_value=True) as mock_pub:
            events, results = await collector.fetch_and_publish_live(INDIAN_LOCATIONS[:2])
            assert len(events) == 2
            assert all(results.values())
            assert mock_pub.call_count == 2
            
            published_payload = mock_pub.call_args_list[0][0][0]
            assert published_payload["source"] == "open_meteo"
            assert published_payload["pipeline"]["stage"] == "RAW"


# 8. Historical Date Range & Archive API Normalization
@pytest.mark.asyncio
async def test_open_meteo_historical_backfill():
    """Verify historical weather archive requests and hourly event normalization."""
    collector = OpenMeteoCollector()
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_HISTORICAL_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
        events = await collector.fetch_historical_archive(
            city="Delhi",
            start_date="2025-01-01",
            end_date="2025-01-01"
        )
        assert len(events) == 2  # 2 hourly observations
        assert events[0]["location"]["city"] == "Delhi"
        assert events[0]["weather"]["temperature"] == 12.4
        assert events[1]["weather"]["temperature"] == 11.8
        
        params_called = mock_get.call_args[1].get("params", {})
        assert params_called.get("start_date") == "2025-01-01"
        assert params_called.get("end_date") == "2025-01-01"


# 9. Source Metadata Helper & Metrics Tracker
def test_source_metadata_and_metrics():
    """Verify source metadata helper and metrics tracker incrementing."""
    meta = get_source_metadata("open_meteo")
    assert meta["source_id"] == "open_meteo"
    assert meta["provider"] == "Open-Meteo"
    assert meta["source_type"] == "weather_api"

    metrics_tracker.record_success(
        source_id="open_meteo",
        records_received=50,
        records_published=50,
        duplicates=0,
        latency_ms=120.5
    )

    m = metrics_tracker.get_metrics("open_meteo")
    assert m["requests_success"] >= 1
    assert m["records_published"] >= 50
    assert m["status"] == "healthy"


# 10. Optional Real API Integration Test (Skipped by default in CI)
@pytest.mark.skipif(os.getenv("RUN_LIVE_API_TESTS") != "1", reason="Live API test disabled by default")
@pytest.mark.asyncio
async def test_live_open_meteo_api_integration():
    """Manual integration test hitting actual Open-Meteo endpoints."""
    collector = OpenMeteoCollector()
    locations = get_locations_by_names(["Delhi", "Mumbai"])
    events = await collector.fetch_current_batch(locations)
    assert len(events) > 0
    assert events[0]["location"]["city"] in ["Delhi", "Mumbai"]
