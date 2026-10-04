"""
YouTube Data API Weather Video Collector (PS-26069).
Google YouTube Data API v3 for discovering public weather reports and broadcasts.
Publishes normalized social reports directly to Kafka `weather.raw`.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

import httpx

from app.core.config import settings
from app.core.location_registry import get_all_locations
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


class YouTubeCollector:
    """Async collector for Google YouTube Data API v3 weather search."""

    def __init__(self):
        self.source_id = "youtube"
        self.collector_name = "youtube_collector"
        self.authority = "YouTube_API"
        self.health_state = "DISABLED" if not getattr(settings, "YOUTUBE_ENABLED", False) else "READY"

    def is_enabled(self) -> bool:
        return getattr(settings, "YOUTUBE_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "YouTube collector is disabled in configuration (YOUTUBE_ENABLED=false)"
        api_key = getattr(settings, "YOUTUBE_API_KEY", "") or ""
        if not api_key.strip():
            return False, "YouTube API key missing (YOUTUBE_API_KEY)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "Google YouTube Data API v3"
        meta["source_type"] = "social_media"
        return meta

    def generate_deterministic_event_id(self, video_id: str) -> str:
        return f"weather_youtube_{video_id}"

    def normalize_video(self, item: Dict[str, Any], query: str = "weather India") -> Dict[str, Any]:
        id_info = item.get("id", {})
        video_id = id_info.get("videoId") or "unknown_video"
        snippet = item.get("snippet", {})
        title = snippet.get("title", "Weather Report Video")
        description = snippet.get("description", title)
        pub_at = snippet.get("publishedAt") or datetime.now(timezone.utc).isoformat()
        channel = snippet.get("channelTitle", "YouTube Channel")
        thumb_url = snippet.get("thumbnails", {}).get("high", {}).get("url")

        ev_id = self.generate_deterministic_event_id(video_id)

        city = None
        state = None
        lat = None
        lon = None
        text = f"{title} {description}".lower()
        for loc in get_all_locations():
            if loc["city"].lower() in text:
                city = loc["city"]
                state = loc["state"]
                lat = loc["latitude"]
                lon = loc["longitude"]
                break

        photos_list = [thumb_url] if thumb_url else []
        media_list = [{
            "type": "image",
            "url": thumb_url,
            "thumbnail_url": thumb_url,
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "alt_text": title,
            "provider": "youtube"
        }] if thumb_url else []

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"YouTube Report: {title}",
            "description": f"Public YouTube Video Report by {channel}: {description}",
            "event_type": "weather_social_report",
            "severity": "moderate",
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "youtube",
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "timestamp": pub_at,
            "reported_at": pub_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": "SOURCE_REPORTED",
            "photos": photos_list,
            "media": media_list,
            "metadata": {
                "video_id": video_id,
                "channel_title": channel,
                "thumbnail_url": thumb_url,
                "image_url": thumb_url,
                "media": media_list,
                "search_query": query,
                "is_social_video_report": True,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def search_weather_videos(self, query: str = "weather India") -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            if not self.is_enabled():
                self.health_state = "DISABLED"
            else:
                self.health_state = "AUTH_REQUIRED"
            return []

        api_key = getattr(settings, "YOUTUBE_API_KEY", "")

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 10,
            "order": "date",
            "key": api_key,
        }

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(YOUTUBE_SEARCH_URL, params=params, timeout=15.0)
                if resp.status_code in (401, 403):
                    logger.warning("[YOUTUBE] API Key unauthorized or quota exceeded.")
                    self.health_state = "AUTH_REQUIRED"
                    metrics_tracker.record_failure(self.source_id, "AUTH_REQUIRED")
                    return []
                resp.raise_for_status()
                data = resp.json()

                items = data.get("items", [])
                for item in items:
                    events.append(self.normalize_video(item, query))

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(items), len(events), latency_ms=latency)
                else:
                    self.health_state = "NO_DATA"
        except Exception as e:
            logger.info(f"[YOUTUBE] API request note for '{query}': {e}")
            if self.health_state != "AUTH_REQUIRED":
                self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        return events

    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            if not self.is_enabled():
                self.health_state = "DISABLED"
            else:
                self.health_state = "AUTH_REQUIRED"
            return [], {}

        terms_str = getattr(settings, "YOUTUBE_SEARCH_TERMS", "weather India")
        queries = [q.strip() for q in terms_str.split(",") if q.strip()]

        all_events = []
        for q in queries[:2]:
            evs = await self.search_weather_videos(q)
            all_events.extend(evs)

        results = {}
        for ev in all_events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return all_events, results


youtube_collector = YouTubeCollector()
