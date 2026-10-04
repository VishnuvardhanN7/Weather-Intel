import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.config import settings
from app.collectors.api_collector import api_collector
from app.services.ingestion_service import run_ingestion


@pytest.mark.asyncio
async def test_missing_api_key_behavior():
    """Test that missing OPENWEATHER_API_KEY does not produce mock data unless requested."""
    with patch.object(settings, "OPENWEATHER_API_KEY", ""):
        with patch.object(api_collector, "openweather_key", ""):
            res = await api_collector.fetch_openweather_current("Bengaluru", use_sample_data=False)
            assert res is None


@pytest.mark.asyncio
async def test_mock_data_not_used_when_real_key_exists():
    """Test that mock data generator is bypassed when OPENWEATHER_API_KEY is present."""
    fake_response = {
        "coord": {"lat": 12.97, "lon": 77.59},
        "weather": [{"main": "Rain", "description": "heavy rain"}],
        "main": {"temp": 24.5, "humidity": 80},
        "wind": {"speed": 5.2, "deg": 180},
        "name": "Bengaluru",
        "sys": {}
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response
    mock_resp.raise_for_status = MagicMock()

    with patch.object(settings, "OPENWEATHER_API_KEY", "real_dummy_key"):
        with patch.object(api_collector, "openweather_key", "real_dummy_key"):
            with patch("httpx.AsyncClient.get", return_value=mock_resp):
                with patch.object(api_collector, "_mock_openweather") as mock_gen:
                    res = await api_collector.fetch_openweather_current("Bengaluru", use_sample_data=True)
                    assert res is not None
                    assert res["city"] == "Bengaluru"
                    assert res["event_type"] == "rainfall"
                    mock_gen.assert_not_called()


@pytest.mark.asyncio
async def test_publish_raw_weather_event_to_kafka():
    """Test real API response publishes directly to Kafka weather.raw without DB insert."""
    mock_weather = {
        "title": "Rain: heavy rain in Mumbai, India",
        "description": "Current weather in Mumbai",
        "event_type": "rainfall",
        "severity": "high",
        "city": "Mumbai",
        "state": "",
        "latitude": 19.07,
        "longitude": 72.87,
        "metadata": {"source_api": "openweathermap"},
        "reported_at": "2026-10-01T12:00:00Z"
    }

    with patch.object(settings, "KAFKA_ENABLED", True):
        with patch.object(api_collector, "fetch_openweather_current", return_value=mock_weather):
            with patch("app.services.kafka_service.kafka_service.publish_raw_event", return_value=True) as mock_pub:
                success = await api_collector.publish_raw_weather_event("Mumbai")
                assert success is True
                mock_pub.assert_called_once()
                payload = mock_pub.call_args[0][0]
                assert payload["source"] == "api"
                assert payload["processing_status"] == "RAW"
                assert payload["location"]["city"] == "Mumbai"


@pytest.mark.asyncio
async def test_no_direct_db_insertion_in_streaming_mode():
    """Test public_api ingestion in streaming mode publishes to Kafka without DB insertion."""
    mock_db = AsyncMock()
    with patch.object(settings, "KAFKA_ENABLED", True):
        with patch.object(settings, "OPENWEATHER_API_KEY", "valid_key"):
            with patch.object(api_collector, "publish_raw_weather_bulk", return_value={"Mumbai": True, "Delhi": True}) as mock_bulk:
                with patch.object(api_collector, "store_api_events") as mock_store:
                    res = await run_ingestion(mock_db, sources=["public_api"])
                    assert res["sources"]["public_api"]["published_to_raw"] == 2
                    mock_bulk.assert_called_once()
                    mock_store.assert_not_called()
