import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.usgs_water_collector import usgs_water_collector, USGSWaterCollector
from app.core.config import settings

SAMPLE_USGS_RESPONSE = {
    "value": {
        "timeSeries": [
            {
                "sourceInfo": {
                    "siteName": "POTOMAC RIVER NEAR WASHINGTON DC",
                    "siteCode": [{"value": "01646500"}],
                    "geoLocation": {
                        "geogLocation": {"latitude": 38.9497, "longitude": -77.1276}
                    }
                },
                "variable": {
                    "variableName": "Discharge, cubic feet per second",
                    "unit": {"unitCode": "cfs"}
                },
                "values": [
                    {
                        "value": [
                            {"value": "12500", "dateTime": "2026-10-02T06:00:00Z"}
                        ]
                    }
                ]
            }
        ]
    }
}


@pytest.mark.asyncio
async def test_usgs_disabled_configuration():
    collector = USGSWaterCollector()
    with patch.object(settings, "USGS_WATER_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_usgs_deterministic_event_id():
    collector = USGSWaterCollector()
    ts = SAMPLE_USGS_RESPONSE["value"]["timeSeries"][0]
    event = collector.normalize_time_series(ts)
    assert event["id"] is not None
    assert "usgs_water_01646500_" in event["id"]


def test_usgs_normalization_and_geo_filtering():
    collector = USGSWaterCollector()
    ts = SAMPLE_USGS_RESPONSE["value"]["timeSeries"][0]
    event = collector.normalize_time_series(ts)
    assert event["event_type"] == "hydrology_observation"
    assert event["source"] == "usgs_water"
    assert event["latitude"] == 38.9497
    assert event["longitude"] == -77.1276
    # Note: USGS site is in US, so city/state for India remain None
    assert event["city"] is None
    assert event["state"] is None
    assert event["metadata"]["site_code"] == "01646500"
    assert event["metadata"]["value"] == "12500"


@pytest.mark.asyncio
async def test_usgs_successful_response():
    collector = USGSWaterCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_USGS_RESPONSE

    with patch.object(settings, "USGS_WATER_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            with patch("app.collectors.usgs_water_collector.kafka_service.publish_raw_event", return_value=True):
                events, results = await collector.fetch_and_publish_all()
                assert len(events) == 1
                assert events[0]["event_type"] == "hydrology_observation"
                assert collector.health_state == "HEALTHY"
