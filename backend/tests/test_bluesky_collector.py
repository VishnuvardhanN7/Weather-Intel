import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.bluesky_collector import bluesky_collector, BlueskyCollector
from app.core.config import settings

SAMPLE_BLUESKY_RESPONSE = {
    "posts": [
        {
            "uri": "at://did:plc:12345/app.bsky.feed.post/3kxyz",
            "cid": "bafyreicid123",
            "author": {
                "handle": "bengaluru.bsky.social",
                "displayName": "Bengaluru Live"
            },
            "record": {
                "text": "Heavy thunderstorm in Bengaluru Karnataka causing traffic jams in Koramangala.",
                "createdAt": "2026-10-02T06:00:00.000Z"
            }
        }
    ]
}


@pytest.mark.asyncio
async def test_bluesky_disabled_configuration():
    collector = BlueskyCollector()
    with patch.object(settings, "BLUESKY_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_bluesky_deterministic_event_id():
    collector = BlueskyCollector()
    post = SAMPLE_BLUESKY_RESPONSE["posts"][0]
    event = collector.normalize_post(post, "weather India")
    assert event["id"] is not None
    assert "bluesky_" in event["id"]


def test_bluesky_normalization_and_city_extraction():
    collector = BlueskyCollector()
    post = SAMPLE_BLUESKY_RESPONSE["posts"][0]
    event = collector.normalize_post(post, "weather India")
    assert event["event_type"] == "weather_social_report"
    assert event["source"] == "bluesky"
    assert event["city"] == "Bengaluru"
    assert event["state"] == "Karnataka"
    assert event["latitude"] == 12.9716
    assert event["longitude"] == 77.5946
    assert event["verification_status"] == "SOURCE_REPORTED"
    assert event["pipeline"]["stage"] == "RAW"


@pytest.mark.asyncio
async def test_bluesky_timeout_handling():
    collector = BlueskyCollector()
    with patch.object(settings, "BLUESKY_ENABLED", True):
        with patch("httpx.AsyncClient.get", side_effect=RequestError("Network error")):
            events, results = await collector.fetch_and_publish_all()
            assert events == []
            assert collector.health_state == "DEGRADED"


@pytest.mark.asyncio
async def test_bluesky_successful_response():
    collector = BlueskyCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_BLUESKY_RESPONSE

    with patch.object(settings, "BLUESKY_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            with patch("app.collectors.bluesky_collector.kafka_service.publish_raw_event", return_value=True):
                events, results = await collector.fetch_and_publish_all()
                assert len(events) > 0
                assert events[0]["event_type"] == "weather_social_report"
                assert collector.health_state == "HEALTHY"
