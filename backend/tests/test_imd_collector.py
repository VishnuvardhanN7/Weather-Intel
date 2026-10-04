import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import Response, RequestError, HTTPStatusError

from app.collectors.imd_collector import imd_collector, IMDCollector
from app.services.source_registry import SOURCE_REGISTRY, metrics_tracker, get_source_metadata
from app.core.imd_locations import resolve_imd_location


SAMPLE_IMD_CURRENT_RESPONSE = [
    {
        "station": "Vijayawada",
        "state": "Andhra Pradesh",
        "temperature": 32.4,
        "humidity": 70,
        "rainfall": 15.2,
        "wind_speed": 4.5,
        "wind_direction": "SE",
        "pressure": 1009,
        "timestamp": "2026-10-02T12:00:00Z"
    }
]

SAMPLE_IMD_WARNING_RESPONSE = [
    {
        "warning_id": "WARN_AP_001",
        "district": "Krishna",
        "state": "Andhra Pradesh",
        "warning_text": "Extremely Heavy Rainfall and Thunderstorm expected",
        "valid_until": "18:00 IST"
    }
]

SAMPLE_IMD_FORECAST_RESPONSE = [
    {
        "city": "Mumbai",
        "forecast_date": "2026-10-03",
        "temp_max": 33.0,
        "temp_min": 25.0,
        "weather_condition": "Moderate Rain / Thundershowers"
    }
]

SAMPLE_IMD_RAINFALL_DISTRICT_RESPONSE = [
    {
        "district": "Chennai",
        "state": "Tamil Nadu",
        "date": "2026-10-02",
        "rainfall_mm": 45.8
    }
]

SAMPLE_IMD_RAINFALL_STATE_RESPONSE = [
    {
        "state": "Maharashtra",
        "date": "2026-10-02",
        "actual_rainfall_mm": 120.5
    }
]

SAMPLE_IMD_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>IMD District Nowcast</title>
    <link>https://mausam.imd.gov.in</link>
    <item>
      <title>Moderate Thunderstorm and Heavy Rain Warning</title>
      <description>District: Delhi. Heavy rain accompanied by squally winds likely during next 3 hours.</description>
      <pubDate>Fri, 02 Oct 2026 12:00:00 IST</pubDate>
    </item>
  </channel>
</rss>
"""


# 1. Current Weather Normalization
@pytest.mark.asyncio
async def test_imd_current_weather_normalization():
    collector = IMDCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_IMD_CURRENT_RESPONSE

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_current_weather()
        assert len(events) == 1
        ev = events[0]
        assert ev["source"] == "imd"
        assert ev["source_metadata"]["provider"] == "India Meteorological Department"
        assert ev["source_metadata"]["authority"] == "official_government_source"
        assert ev["event_type"] == "weather_observation"
        assert ev["location"]["city"] == "Vijayawada"
        assert ev["weather"]["temperature"] == 32.4
        assert ev["verification_status"] == "SOURCE_REPORTED"


# 2. City Forecast Normalization
@pytest.mark.asyncio
async def test_imd_city_forecast_normalization():
    collector = IMDCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_IMD_FORECAST_RESPONSE

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_city_forecast()
        assert len(events) == 1
        ev = events[0]
        assert ev["event_type"] == "weather_forecast"
        assert ev["event_id"].startswith("weather_imd_forecast_mumbai_")
        assert ev["weather"]["temp_max"] == 33.0


# 3. District Warning Normalization & Severity Categorization
@pytest.mark.asyncio
async def test_imd_district_warning_normalization():
    collector = IMDCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_IMD_WARNING_RESPONSE

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_district_warnings()
        assert len(events) == 1
        ev = events[0]
        assert ev["event_type"] == "weather_warning"
        assert ev["category"] == "heavy_rainfall"
        assert ev["severity"] == "critical"
        assert ev["event_id"] == "weather_imd_warning_WARN_AP_001"
        assert ev["verification_status"] == "SOURCE_REPORTED"


# 4. District Rainfall Normalization
@pytest.mark.asyncio
async def test_imd_district_rainfall_normalization():
    collector = IMDCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_IMD_RAINFALL_DISTRICT_RESPONSE

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_district_rainfall()
        assert len(events) == 1
        ev = events[0]
        assert ev["event_type"] == "rainfall_observation"
        assert ev["weather"]["rainfall"] == 45.8


# 5. State Rainfall Normalization
@pytest.mark.asyncio
async def test_imd_state_rainfall_normalization():
    collector = IMDCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_IMD_RAINFALL_STATE_RESPONSE

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_state_rainfall()
        assert len(events) == 1
        ev = events[0]
        assert ev["event_type"] == "rainfall_observation"
        assert ev["weather"]["rainfall"] == 120.5


# 6. RSS Parsing & Secondary Public Ingestion
@pytest.mark.asyncio
async def test_imd_rss_parsing():
    collector = IMDCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_IMD_RSS_XML

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_imd_rss()
        assert len(events) >= 1
        ev = events[0]
        assert "OFFICIAL IMD RSS" in ev["title"]
        assert ev["source"] == "imd"
        assert ev["location"]["city"] == "Delhi"


# 7. Missing Values & Defaults
def test_imd_missing_values_handling():
    collector = IMDCollector()
    category, event_type, severity = collector.parse_warning_severity_and_category("Unknown weather report")
    assert category == "heavy_rainfall"
    assert event_type == "weather_warning"
    assert severity == "moderate"


# 8. Authentication Required Behavior
@pytest.mark.asyncio
async def test_imd_auth_required_behavior():
    collector = IMDCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_current_weather()
        # Must return empty events list without throwing or creating fake data
        assert events == []


# 9. Invalid Response / HTTP Errors
@pytest.mark.asyncio
async def test_imd_invalid_response_handling():
    collector = IMDCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = HTTPStatusError("Internal Server Error", request=MagicMock(), response=mock_resp)

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        events = await collector.fetch_current_weather()
        assert events == []


# 10. Timeout & Network Retries
@pytest.mark.asyncio
async def test_imd_timeout_handling():
    collector = IMDCollector()
    with patch("httpx.AsyncClient.get", side_effect=RequestError("Connection timeout")):
        events = await collector.fetch_current_weather()
        assert events == []


# 11. Deterministic Event IDs
def test_imd_deterministic_event_id_generation():
    collector = IMDCollector()
    id1 = collector.generate_deterministic_event_id("current", "Vijayawada", "2026-10-02T12:00:00Z")
    id2 = collector.generate_deterministic_event_id("current", "Vijayawada", "2026-10-02T12:00:00Z")
    assert id1 == id2
    assert "weather_imd_current_vijayawada_" in id1


# 12. Location Resolution
def test_imd_location_resolution():
    loc1 = resolve_imd_location("DELHI")
    assert loc1["city"] == "Delhi"
    assert loc1["latitude"] == 28.6139

    loc2 = resolve_imd_location("KRISHNA")
    assert loc2["city"] == "Vijayawada"


# 13. Kafka RAW Publishing
@pytest.mark.asyncio
async def test_imd_kafka_raw_publishing():
    collector = IMDCollector()
    mock_events = [
        {
            "event_id": "weather_imd_current_test_123",
            "source": "imd",
            "source_metadata": collector.get_source_header(),
            "pipeline": {"stage": "RAW"},
            "title": "IMD Test Event",
            "location": {"city": "Delhi"},
        }
    ]

    with patch.object(collector, "fetch_current_weather", return_value=mock_events):
        with patch.object(collector, "fetch_city_forecast", return_value=[]):
            with patch.object(collector, "fetch_district_nowcast", return_value=[]):
                with patch.object(collector, "fetch_district_warnings", return_value=[]):
                    with patch.object(collector, "fetch_district_rainfall", return_value=[]):
                        with patch.object(collector, "fetch_state_rainfall", return_value=[]):
                            with patch.object(collector, "fetch_imd_rss", return_value=[]):
                                with patch("app.services.kafka_service.kafka_service.publish_raw_event", return_value=True) as mock_pub:
                                    events, results = await collector.fetch_and_publish_all()
                                    assert len(events) == 1
                                    assert results["weather_imd_current_test_123"] is True
                                    mock_pub.assert_called_once()


# 14. Metrics Tracker Integration
def test_imd_source_metrics_integration():
    metrics_tracker.record_success("imd", records_received=10, records_published=10, latency_ms=150.0)
    m = metrics_tracker.get_metrics("imd")
    assert m["requests_success"] >= 1
    assert m["records_published"] >= 10
    assert m["status"] in ("healthy", "active")
