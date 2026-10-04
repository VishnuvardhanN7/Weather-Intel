"""
Mastodon Fediverse Weather Status Collector (PS-26069).
Decentralized Fediverse Mastodon API collector searching weather hashtags and public statuses.
Publishes normalized social reports directly to Kafka `weather.raw`.
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

import httpx

from app.core.config import settings
from app.core.location_registry import get_all_locations
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)


def clean_html_text(raw_html: str) -> str:
    return re.sub(r"<[^>]+>", "", raw_html).strip()


class MastodonCollector:
    """Async collector for Mastodon public weather hashtag statuses."""

    def __init__(self):
        self.source_id = "mastodon"
        self.collector_name = "mastodon_collector"
        self.authority = "Mastodon_Network"
        self.health_state = "DISABLED" if not getattr(settings, "MASTODON_ENABLED", False) else "READY"

    def is_enabled(self) -> bool:
        return getattr(settings, "MASTODON_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "Mastodon collector is disabled in configuration (MASTODON_ENABLED=false)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "Mastodon Decentralized Fediverse"
        meta["source_type"] = "social_media"
        return meta

    def generate_deterministic_event_id(self, status_id: str) -> str:
        clean_id = str(status_id).lower().replace(" ", "_")
        return f"weather_mastodon_{clean_id}"

    def normalize_status(self, item: Dict[str, Any], tag: str = "WeatherIndia") -> Dict[str, Any]:
        status_id = item.get("id", "unknown_status")
        raw_content = item.get("content", "")
        clean_text = clean_html_text(raw_content)
        created_at = item.get("created_at") or datetime.now(timezone.utc).isoformat()
        instance = getattr(settings, "MASTODON_INSTANCE", "mastodon.social").rstrip("/")
        url_link = item.get("url") or f"{instance}/@{item.get('account', {}).get('username', 'user')}/{status_id}"

        ev_id = self.generate_deterministic_event_id(str(status_id))

        city = None
        state = None
        lat = None
        lon = None
        text = clean_text.lower()
        for loc in get_all_locations():
            if loc["city"].lower() in text:
                city = loc["city"]
                state = loc["state"]
                lat = loc["latitude"]
                lon = loc["longitude"]
                break

        media_attachments = item.get("media_attachments", [])
        media_list = []
        photos_list = []
        for att in media_attachments:
            u = att.get("url") or att.get("preview_url")
            if u:
                att_type = att.get("type", "image")
                if att_type in ("image", "gifv"):
                    photos_list.append(u)
                media_list.append({
                    "type": att_type,
                    "url": u,
                    "thumbnail_url": att.get("preview_url") or u,
                    "source_url": url_link,
                    "alt_text": att.get("description") or "",
                    "provider": "mastodon"
                })

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"Mastodon Report (#{tag}): {clean_text[:80]}...",
            "description": f"Decentralized Fediverse status: {clean_text}",
            "event_type": "weather_social_report",
            "severity": "moderate",
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "mastodon",
            "source_url": url_link,
            "timestamp": created_at,
            "reported_at": created_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": "SOURCE_REPORTED",
            "photos": photos_list,
            "media": media_list,
            "metadata": {
                "status_id": str(status_id),
                "hashtag": tag,
                "instance": instance,
                "is_mastodon_status": True,
                "image_url": photos_list[0] if photos_list else None,
                "media": media_list,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def fetch_hashtag_timeline(self, tag: str = "WeatherIndia") -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return []

        instance = getattr(settings, "MASTODON_INSTANCE", "mastodon.social").rstrip("/")
        if not instance.startswith("http"):
            instance = f"https://{instance}"

        url = f"{instance}/api/v1/timelines/tag/{tag}"
        headers = {}
        token = getattr(settings, "MASTODON_ACCESS_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15.0, follow_redirects=True)
                if resp.status_code in (401, 403):
                    self.health_state = "AUTH_REQUIRED"
                    metrics_tracker.record_failure(self.source_id, "AUTH_REQUIRED")
                    return []
                resp.raise_for_status()
                records = resp.json() if isinstance(resp.json(), list) else []

                for item in records:
                    events.append(self.normalize_status(item, tag))

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(records), len(events), latency_ms=latency)
                else:
                    self.health_state = "NO_DATA"
        except Exception as e:
            logger.info(f"[MASTODON] API request note for tag #{tag}: {e}")
            if self.health_state != "AUTH_REQUIRED":
                self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        return events

    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return [], {}

        tags_str = getattr(settings, "MASTODON_HASHTAGS", "IMD,WeatherIndia,Rain,Flood,Cyclone,Heatwave")
        tags = [t.strip().replace("#", "") for t in tags_str.split(",") if t.strip()]

        all_events = []
        for tag in tags[:2]:
            evs = await self.fetch_hashtag_timeline(tag)
            all_events.extend(evs)

        results = {}
        for ev in all_events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return all_events, results


mastodon_collector = MastodonCollector()
