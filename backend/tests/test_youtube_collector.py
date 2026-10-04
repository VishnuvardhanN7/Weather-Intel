import pytest
from unittest.mock import MagicMock, patch
from httpx import RequestError

from app.collectors.youtube_collector import youtube_collector, YouTubeCollector
from app.core.config import settings

SAMPLE_YOUTUBE_RESPONSE = {
    "items": [
        {
            "id": {"videoId": "abc123xyz"},
            "snippet": {
                "title": "Heavy rainfall causes severe flooding in Mumbai",
                "description": "Live report on torrential rains affecting suburban trains and road traffic across Mumbai.",
                "publishedAt": "2026-10-02T05:30:00Z",
                "channelTitle": "NDTV India",
                "thumbnails": {"high": {"url": "https://img.youtube.com/vi/abc123xyz/hqdefault.jpg"}}
            }
        }
    ]
}


@pytest.mark.asyncio
async def test_youtube_disabled_configuration():
    collector = YouTubeCollector()
    with patch.object(settings, "YOUTUBE_ENABLED", False):
        valid, msg = collector.validate_config()
        assert not valid
        events, results = await collector.fetch_and_publish_all()
        assert events == []
        assert collector.health_state == "DISABLED"


def test_youtube_missing_credentials():
    collector = YouTubeCollector()
    with patch.object(settings, "YOUTUBE_ENABLED", True):
        with patch.object(settings, "YOUTUBE_API_KEY", ""):
            valid, msg = collector.validate_config()
            assert not valid
            assert "missing" in msg.lower()


def test_youtube_deterministic_event_id():
    collector = YouTubeCollector()
    item = SAMPLE_YOUTUBE_RESPONSE["items"][0]
    event = collector.normalize_video(item, "heavy rainfall India")
    assert event["id"] is not None
    assert "youtube_abc123xyz" in event["id"]


def test_youtube_normalization_and_city_extraction():
    collector = YouTubeCollector()
    item = SAMPLE_YOUTUBE_RESPONSE["items"][0]
    event = collector.normalize_video(item, "heavy rainfall India")
    assert event["event_type"] == "weather_social_report"
    assert event["source"] == "youtube"
    assert event["city"] == "Mumbai"
    assert event["state"] == "Maharashtra"
    assert event["latitude"] == 19.0760
    assert event["longitude"] == 72.8777
    assert event["verification_status"] == "SOURCE_REPORTED"
    assert event["pipeline"]["stage"] == "RAW"


@pytest.mark.asyncio
async def test_youtube_auth_failure():
    collector = YouTubeCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 403

    with patch.object(settings, "YOUTUBE_ENABLED", True):
        with patch.object(settings, "YOUTUBE_API_KEY", "invalid_key"):
            with patch("httpx.AsyncClient.get", return_value=mock_resp):
                events, results = await collector.fetch_and_publish_all()
                assert events == []
                assert collector.health_state == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_youtube_successful_response():
    collector = YouTubeCollector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_YOUTUBE_RESPONSE

    with patch.object(settings, "YOUTUBE_ENABLED", True):
        with patch.object(settings, "YOUTUBE_API_KEY", "valid_key"):
            with patch("httpx.AsyncClient.get", return_value=mock_resp):
                with patch("app.collectors.youtube_collector.kafka_service.publish_raw_event", return_value=True):
                    events, results = await collector.fetch_and_publish_all()
                    assert len(events) > 0
                    assert events[0]["event_type"] == "weather_social_report"
                    assert collector.health_state == "HEALTHY"
