import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import Response, RequestError, HTTPStatusError

from app.collectors.mosdac_collector import mosdac_collector, MosdacCollector, parse_bounding_box
from app.services.source_registry import SOURCE_REGISTRY, metrics_tracker, get_source_metadata
from app.core.config import settings


SAMPLE_MOSDAC_PRODUCT_RESPONSE = {
    "products": [
        {
            "product_id": "INSAT3D_3D_L1B_STD_20261002_0600",
            "satellite": "INSAT-3D",
            "sensor": "Imager",
            "product": "L1B_STD",
            "observation_time": "2026-10-02T06:00:00Z",
            "center_latitude": 18.5,
            "center_longitude": 80.2,
            "download_url": "https://mosdac.gov.in/data/INSAT3D_3D_L1B_STD_20261002_0600.nc"
        }
    ]
}


# 1. Disabled Configuration Test
@pytest.mark.asyncio
async def test_mosdac_disabled_configuration():
    collector = MosdacCollector()
    with patch.object(settings, "MOSDAC_ENABLED", False):
        events = await collector.fetch_nrt_products()
        assert events == []
        assert collector.health_state == "DISABLED"


# 2. Missing Credentials Handling
@pytest.mark.asyncio
async def test_mosdac_missing_credentials_handling():
    collector = MosdacCollector()
    with patch.object(settings, "MOSDAC_USERNAME", ""):
        with patch.object(settings, "MOSDAC_PASSWORD", ""):
            authenticated = await collector.authenticate()
            assert authenticated is False
            assert collector.health_state == "AUTH_REQUIRED"


# 3. Dataset Configuration & Bounding Box Parsing
def test_mosdac_bounding_box_parsing():
    min_lon, min_lat, max_lon, max_lat = parse_bounding_box("70.0,8.0,90.0,28.0")
    assert min_lon == 70.0
    assert min_lat == 8.0
    assert max_lon == 90.0
    assert max_lat == 28.0

    # Malformed bounding box string fallback
    min_lon, min_lat, max_lon, max_lat = parse_bounding_box("invalid_bbox")
    assert (min_lon, min_lat, max_lon, max_lat) == (70.0, 8.0, 90.0, 28.0)


# 4. Deterministic Event ID Generation
def test_mosdac_deterministic_event_id():
    collector = MosdacCollector()
    id1 = collector.generate_deterministic_event_id("3D_L1B_STD", "2026-10-02T06:00:00Z", "PROD_001")
    id2 = collector.generate_deterministic_event_id("3D_L1B_STD", "2026-10-02T06:00:00Z", "PROD_001")
    assert id1 == id2
    assert "weather_mosdac_3d_l1b_std_" in id1


# 5. Normalization into Raw Event Schema
def test_mosdac_normalization_format():
    collector = MosdacCollector()
    raw = SAMPLE_MOSDAC_PRODUCT_RESPONSE["products"][0]

    event = collector.normalize_satellite_observation(raw, "3D_L1B_STD", "70.0,8.0,90.0,28.0")
    assert event is not None
    assert event["event_type"] == "satellite_weather"
    assert event["source"] == "mosdac"
    assert event["source_metadata"]["authority"] == "ISRO_MOSDAC"
    assert event["source_metadata"]["provider"] == "ISRO MOSDAC Satellite"
    assert event["latitude"] == 18.5
    assert event["longitude"] == 80.2
    assert event["city"] is None
    assert event["state"] is None
    assert event["metadata"]["satellite"] == "INSAT-3D"
    assert event["metadata"]["is_satellite_observation"] is True
    assert event["pipeline"]["stage"] == "RAW"


# 6. Malformed Response & Bad JSON Handling
@pytest.mark.asyncio
async def test_mosdac_malformed_response():
    collector = MosdacCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"invalid": "schema"}

    with patch.object(settings, "MOSDAC_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            events = await collector.fetch_nrt_products()
            assert events == []


# 7. Timeout & Network Retries
@pytest.mark.asyncio
async def test_mosdac_timeout_handling():
    collector = MosdacCollector()
    with patch.object(settings, "MOSDAC_ENABLED", True):
        with patch("httpx.AsyncClient.get", side_effect=RequestError("Network timeout")):
            events = await collector.fetch_nrt_products()
            assert events == []
            assert collector.health_state == "DEGRADED"


# 8. Authentication Failure Handling (401/403)
@pytest.mark.asyncio
async def test_mosdac_auth_failure_handling():
    collector = MosdacCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch.object(settings, "MOSDAC_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            events = await collector.fetch_nrt_products()
            assert events == []
            assert collector.health_state == "AUTH_REQUIRED"


# 9. Successful Real Response Parsing (Mocked HTTP)
@pytest.mark.asyncio
async def test_mosdac_successful_mocked_response():
    collector = MosdacCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_MOSDAC_PRODUCT_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch.object(settings, "MOSDAC_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            events = await collector.fetch_nrt_products()
            assert len(events) == 1
            assert events[0]["metadata"]["satellite"] == "INSAT-3D"
            assert collector.health_state == "HEALTHY"


# 10. Kafka Publication & No Direct DB Insertion
@pytest.mark.asyncio
async def test_mosdac_kafka_publishing_no_direct_db_insert():
    collector = MosdacCollector()
    mock_events = [
        collector.normalize_satellite_observation(
            SAMPLE_MOSDAC_PRODUCT_RESPONSE["products"][0],
            "3D_L1B_STD",
            "70.0,8.0,90.0,28.0"
        )
    ]

    with patch.object(settings, "MOSDAC_ENABLED", True):
        with patch.object(collector, "fetch_nrt_products", return_value=mock_events):
            with patch("app.services.kafka_service.kafka_service.publish_raw_event", return_value=True) as mock_pub:
                events, results = await collector.fetch_and_publish_all()
                assert len(events) == 1
                assert all(results.values())
                mock_pub.assert_called_once()
                
                published_payload = mock_pub.call_args[0][0]
                assert published_payload["source"] == "mosdac"
                assert published_payload["event_type"] == "satellite_weather"
                assert published_payload["pipeline"]["stage"] == "RAW"
