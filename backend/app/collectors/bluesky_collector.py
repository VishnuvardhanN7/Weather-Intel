"""
Bluesky AT Protocol Weather Post Collector (PS-26069).
Bluesky Social / AT Protocol public post search collector for real-time weather reports.
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

BLUESKY_SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"


class BlueskyCollector:
    """Async collector for Bluesky AT Protocol public weather posts."""

    def __init__(self):
        self.source_id = "bluesky"
        self.collector_name = "bluesky_collector"
        self.authority = "Bluesky_ATProtocol"
        self.health_state = "DISABLED" if not getattr(settings, "BLUESKY_ENABLED", False) else "READY"

    def is_enabled(self) -> bool:
        return getattr(settings, "BLUESKY_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "Bluesky collector is disabled in configuration (BLUESKY_ENABLED=false)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "Bluesky Social / AT Protocol"
        meta["source_type"] = "social_media"
        return meta

    def generate_deterministic_event_id(self, post_uri: str) -> str:
        u_hash = hashlib.md5(post_uri.encode()).hexdigest()[:10]
        return f"weather_bluesky_{u_hash}"

    def normalize_post(self, item: Dict[str, Any], query: str = "weather India") -> Dict[str, Any]:
        uri = item.get("uri", "at://unknown/post/0")
        record = item.get("record", {})
        text = record.get("text", "")
        created_at = record.get("createdAt") or datetime.now(timezone.utc).isoformat()

        author = item.get("author", {})
        handle = author.get("handle", "user.bsky.social")
        post_id = uri.split("/")[-1]
        public_url = f"https://bsky.app/profile/{handle}/post/{post_id}"

        ev_id = self.generate_deterministic_event_id(uri)

        city = None
        state = None
        lat = None
        lon = None
        txt_lower = text.lower()
        for loc in get_all_locations():
            if loc["city"].lower() in txt_lower:
                city = loc["city"]
                state = loc["state"]
                lat = loc["latitude"]
                lon = loc["longitude"]
                break

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"Bluesky Post (@{handle}): {text[:80]}...",
            "description": f"Bluesky Social post by @{handle}: {text}",
            "event_type": "weather_social_report",
            "severity": "moderate",
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "bluesky",
            "source_url": public_url,
            "timestamp": created_at,
            "reported_at": created_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": "SOURCE_REPORTED",
            "metadata": {
                "post_uri": uri,
                "handle": handle,
                "search_query": query,
                "is_bluesky_post": True,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def search_bluesky_posts(self, query: str = "weather India") -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return []

        params = {
            "q": query,
            "limit": 10,
        }

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(BLUESKY_SEARCH_URL, params=params, timeout=15.0)
                if resp.status_code in (401, 403):
                    logger.info("[BLUESKY] Bluesky search API requires authentication credentials (BLUESKY_APP_PASSWORD).")
                    self.health_state = "AUTH_REQUIRED"
                    metrics_tracker.record_failure(self.source_id, "AUTH_REQUIRED")
                    return []
                resp.raise_for_status()
                data = resp.json()

                posts = data.get("posts", [])
                for item in posts:
                    events.append(self.normalize_post(item, query))

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(posts), len(events), latency_ms=latency)
                else:
                    self.health_state = "NO_DATA"
        except Exception as e:
            logger.info(f"[BLUESKY] API request note for query '{query}': {e}")
            self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        return events

    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return [], {}

        terms_str = getattr(settings, "BLUESKY_SEARCH_TERMS", "weather India")
        queries = [q.strip() for q in terms_str.split(",") if q.strip()]

        all_events = []
        for q in queries[:2]:
            evs = await self.search_bluesky_posts(q)
            all_events.extend(evs)

        results = {}
        for ev in all_events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return all_events, results


bluesky_collector = BlueskyCollector()
