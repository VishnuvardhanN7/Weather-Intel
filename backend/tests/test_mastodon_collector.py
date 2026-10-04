import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.mastodon_collector import mastodon_collector, MastodonCollector
from app.core.config import settings

SAMPLE_MASTODON_RESPONSE = [
    {
        "id": "111222333444",
        "created_at": "2026-10-02T06:00:00.000Z",
        "content": "<p>Heavy rainfall recorded in Chennai Tamil Nadu today #Rain #IMD</p>",
        "url": "https://mastodon.social/@user/111222333444",
        "account": {
            "username": "chennai_weather",
            "display_name": "Chennai Weather Tracker"
        },
        "media_attachments": [],
        "tags": [{"name": "Rain"}, {"name": "IMD"}]
    }
]


@pytest.mark.asyncio
async def test_mastodon_disabled_configuration():
    collector = MastodonCollector()
    with patch.object(settings, "MASTODON_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_mastodon_deterministic_event_id():
    collector = MastodonCollector()
    status = SAMPLE_MASTODON_RESPONSE[0]
    event = collector.normalize_status(status, "Rain")
    assert event["id"] is not None
    assert "mastodon_111222333444" in event["id"]


def test_mastodon_normalization_and_city_extraction():
    collector = MastodonCollector()
    status = SAMPLE_MASTODON_RESPONSE[0]
    event = collector.normalize_status(status, "Rain")
    assert event["event_type"] == "weather_social_report"
    assert event["source"] == "mastodon"
    assert event["city"] == "Chennai"
    assert event["state"] == "Tamil Nadu"
    assert event["latitude"] == 13.0827
    assert event["longitude"] == 80.2707
    assert event["verification_status"] == "SOURCE_REPORTED"
    assert event["pipeline"]["stage"] == "RAW"


@pytest.mark.asyncio
async def test_mastodon_timeout_handling():
    collector = MastodonCollector()
    with patch.object(settings, "MASTODON_ENABLED", True):
        with patch("httpx.AsyncClient.get", side_effect=RequestError("Network error")):
            events, results = await collector.fetch_and_publish_all()
            assert events == []
            assert collector.health_state == "DEGRADED"


@pytest.mark.asyncio
async def test_mastodon_successful_response():
    collector = MastodonCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_MASTODON_RESPONSE

    with patch.object(settings, "MASTODON_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            with patch("app.collectors.mastodon_collector.kafka_service.publish_raw_event", return_value=True):
                events, results = await collector.fetch_and_publish_all()
                assert len(events) > 0
                assert events[0]["event_type"] == "weather_social_report"
                assert collector.health_state == "HEALTHY"
