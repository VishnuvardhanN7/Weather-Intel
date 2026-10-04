import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.reddit_collector import reddit_collector, RedditCollector
from app.core.config import settings

SAMPLE_REDDIT_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "id": "post_12345",
                    "title": "Severe heatwave warning issued for Jaipur Rajasthan",
                    "selftext": "Temperatures cross 45°C in Jaipur today according to latest IMD updates.",
                    "subreddit": "india",
                    "author": "weather_watcher",
                    "created_utc": 1700000000,
                    "permalink": "/r/india/comments/post_12345/severe_heatwave/",
                    "score": 142,
                    "url": "https://reddit.com/r/india/comments/post_12345/"
                }
            }
        ]
    }
}


@pytest.mark.asyncio
async def test_reddit_disabled_configuration():
    collector = RedditCollector()
    with patch.object(settings, "REDDIT_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_reddit_deterministic_event_id():
    collector = RedditCollector()
    post = SAMPLE_REDDIT_RESPONSE["data"]["children"][0]["data"]
    event = collector.normalize_post(post, "weather India")
    assert event["id"] is not None
    assert "reddit_post_12345" in event["id"]


def test_reddit_normalization_and_city_extraction():
    collector = RedditCollector()
    post = SAMPLE_REDDIT_RESPONSE["data"]["children"][0]["data"]
    event = collector.normalize_post(post, "weather India")
    assert event["event_type"] == "weather_social_report"
    assert event["source"] == "reddit"
    assert event["city"] == "Jaipur"
    assert event["state"] == "Rajasthan"
    assert event["latitude"] == 26.9124
    assert event["longitude"] == 75.7873
    assert event["verification_status"] == "SOURCE_REPORTED"
    assert event["pipeline"]["stage"] == "RAW"


@pytest.mark.asyncio
async def test_reddit_rate_limit_handling():
    collector = RedditCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch.object(settings, "REDDIT_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            events, results = await collector.fetch_and_publish_all()
            assert events == []
            assert collector.health_state == "DEGRADED"


@pytest.mark.asyncio
async def test_reddit_successful_response():
    collector = RedditCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE

    with patch.object(settings, "REDDIT_ENABLED", True):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            with patch("app.collectors.reddit_collector.kafka_service.publish_raw_event", return_value=True):
                events, results = await collector.fetch_and_publish_all()
                assert len(events) > 0
                assert events[0]["event_type"] == "weather_social_report"
                assert collector.health_state == "HEALTHY"
