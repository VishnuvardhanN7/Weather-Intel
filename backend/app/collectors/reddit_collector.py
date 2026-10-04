"""
Reddit Public Weather Post Collector (PS-26069).
Reddit API collector searching public community posts and crowdsourced weather discussions.
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

REDDIT_SEARCH_URL = "https://www.reddit.com/r/india/search.json"


class RedditCollector:
    """Async collector for Reddit public weather posts and community reports."""

    def __init__(self):
        self.source_id = "reddit"
        self.collector_name = "reddit_collector"
        self.authority = "Reddit_API"
        self.health_state = "DISABLED" if not getattr(settings, "REDDIT_ENABLED", False) else "READY"

    def is_enabled(self) -> bool:
        return getattr(settings, "REDDIT_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "Reddit collector is disabled in configuration (REDDIT_ENABLED=false)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "Reddit Public API"
        meta["source_type"] = "social_media"
        return meta

    def generate_deterministic_event_id(self, post_id: str) -> str:
        clean_id = post_id.lower().replace("t3_", "")
        return f"weather_reddit_{clean_id}"

    def normalize_post(self, post_data: Dict[str, Any], query: str = "weather India") -> Dict[str, Any]:
        post_id = post_data.get("id", "unknown_post")
        title = post_data.get("title", "Reddit Weather Post")
        selftext = post_data.get("selftext", title)
        subreddit = post_data.get("subreddit", "india")
        permalink = post_data.get("permalink", "")
        created_utc = post_data.get("created_utc")
        score = post_data.get("score", 0)

        ts_iso = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else datetime.now(timezone.utc).isoformat()
        ev_id = self.generate_deterministic_event_id(post_id)

        city = None
        state = None
        lat = None
        lon = None
        text = f"{title} {selftext}".lower()
        for loc in get_all_locations():
            if loc["city"].lower() in text:
                city = loc["city"]
                state = loc["state"]
                lat = loc["latitude"]
                lon = loc["longitude"]
                break

        # Extract real post image/thumbnail if available
        post_url = post_data.get("url") or ""
        thumb = post_data.get("thumbnail") or ""
        img_url = None
        if post_url.startswith("http") and any(post_url.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
            img_url = post_url
        elif thumb.startswith("http") and not thumb.startswith("data:"):
            img_url = thumb

        photos_list = [img_url] if img_url else []
        media_list = [{
            "type": "image",
            "url": img_url,
            "thumbnail_url": img_url,
            "source_url": f"https://www.reddit.com{permalink}" if permalink else "https://www.reddit.com",
            "provider": "reddit"
        }] if img_url else []

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"Reddit Report (r/{subreddit}): {title}",
            "description": f"Community post on r/{subreddit}: {selftext[:300]}",
            "event_type": "weather_social_report",
            "severity": "moderate",
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "reddit",
            "source_url": f"https://www.reddit.com{permalink}" if permalink else "https://www.reddit.com",
            "timestamp": ts_iso,
            "reported_at": ts_iso,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": "SOURCE_REPORTED",
            "photos": photos_list,
            "media": media_list,
            "metadata": {
                "post_id": post_id,
                "subreddit": subreddit,
                "score": score,
                "search_query": query,
                "is_reddit_post": True,
                "image_url": img_url,
                "media": media_list,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def search_reddit_posts(self, query: str = "weather India") -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return []

        client_id = getattr(settings, "REDDIT_CLIENT_ID", "")
        client_secret = getattr(settings, "REDDIT_CLIENT_SECRET", "")
        user_agent = getattr(settings, "REDDIT_USER_AGENT", "ATMOS-WeatherPlatform/1.0")

        headers = {"User-Agent": user_agent}

        if client_id and client_secret:
            try:
                async with httpx.AsyncClient() as client:
                    token_resp = await client.post(
                        "https://www.reddit.com/api/v1/access_token",
                        auth=(client_id, client_secret),
                        data={"grant_type": "client_credentials"},
                        headers=headers,
                        timeout=10.0
                    )
                    if token_resp.status_code == 200:
                        token_data = token_resp.json()
                        access_token = token_data.get("access_token")
                        if access_token:
                            headers["Authorization"] = f"bearer {access_token}"
                    elif token_resp.status_code in (401, 403):
                        self.health_state = "AUTH_REQUIRED"
                        metrics_tracker.record_failure(self.source_id, "AUTH_REQUIRED")
                        return []
            except Exception as e:
                logger.info(f"[REDDIT] OAuth error note: {e}")

        params = {
            "q": query,
            "restrict_sr": "off",
            "sort": "new",
            "limit": 10,
        }

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(REDDIT_SEARCH_URL, headers=headers, params=params, timeout=15.0)
                if resp.status_code == 429:
                    self.health_state = "DEGRADED"
                    metrics_tracker.record_failure(self.source_id, "HTTP_429")
                    return []
                if resp.status_code in (401, 403):
                    logger.info(f"[REDDIT] API request returned status {resp.status_code}.")
                    self.health_state = "AUTH_REQUIRED"
                    metrics_tracker.record_failure(self.source_id, f"HTTP_{resp.status_code}")
                    return []
                resp.raise_for_status()
                data = resp.json()

                children = data.get("data", {}).get("children", [])
                for child in children:
                    post_data = child.get("data", {})
                    events.append(self.normalize_post(post_data, query))

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(children), len(events), latency_ms=latency)
                else:
                    self.health_state = "NO_DATA"
        except Exception as e:
            logger.info(f"[REDDIT] API request note for '{query}': {e}")
            if self.health_state != "AUTH_REQUIRED":
                self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        return events

    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return [], {}

        terms_str = getattr(settings, "REDDIT_SEARCH_TERMS", "weather India")
        queries = [q.strip() for q in terms_str.split(",") if q.strip()]

        all_events = []
        for q in queries[:2]:
            evs = await self.search_reddit_posts(q)
            all_events.extend(evs)

        results = {}
        for ev in all_events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return all_events, results


reddit_collector = RedditCollector()
