"""
RainViewer Doppler Weather Radar Collector (PS-26069).
Fetches Doppler radar mosaic maps and precipitation frame metadata.
Publishes normalized events directly to Kafka `weather.raw`.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

import httpx

from app.core.config import settings
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)

RAINVIEWER_API_URL = "https://api.rainviewer.com/public/weather-maps.json"


class RainViewerCollector:
    """Async collector for RainViewer radar and precipitation tile frames."""

    def __init__(self):
        self.source_id = "rainviewer"
        self.collector_name = "rainviewer_collector"
        self.authority = "RainViewer_Radar"
        self.health_state = "DISABLED" if not getattr(settings, "RAINVIEWER_ENABLED", False) else "READY"
        self._cache: Optional[Tuple[datetime, List[Dict[str, Any]]]] = None

    def is_enabled(self) -> bool:
        return getattr(settings, "RAINVIEWER_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "RainViewer collector is disabled in configuration (RAINVIEWER_ENABLED=false)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "RainViewer Radar API"
        meta["source_type"] = "radar_weather"
        return meta

    def generate_deterministic_event_id(self, frame_ts: int, frame_path: str) -> str:
        p_hash = hashlib.md5(frame_path.encode()).hexdigest()[:8]
        return f"weather_rainviewer_radar_{frame_ts}_{p_hash}"

    def normalize_radar_frame(self, frame: Dict[str, Any], host: str = "https://tilecache.rainviewer.com") -> Dict[str, Any]:
        ts = frame.get("time", int(datetime.now(timezone.utc).timestamp()))
        path = frame.get("path", "")
        dt_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if isinstance(ts, (int, float)) else datetime.now(timezone.utc).isoformat()
        ev_id = self.generate_deterministic_event_id(ts, path)

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"RainViewer Radar Frame ({dt_iso})",
            "description": f"Global Doppler radar mosaic frame observation. Host: {host}, Frame Path: {path}",
            "event_type": "radar_observation",
            "severity": "low",
            "city": "Pan-India Coverage",
            "state": "India",
            "latitude": 20.5937,
            "longitude": 78.9629,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "rainviewer",
            "source_url": f"{host}{path}/256/3/4/2/1/0_0.png",
            "timestamp": dt_iso,
            "reported_at": dt_iso,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": "SOURCE_REPORTED",
            "metadata": {
                "radar_timestamp": ts,
                "frame_path": path,
                "tile_host": host,
                "coverage": "Global_Doppler_Mosaic",
                "is_radar_observation": True,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def fetch_radar_data(self) -> List[Dict[str, Any]]:
        return await self.fetch_radar_frames()

    async def fetch_radar_frames(self) -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return []

        if self._cache:
            cached_at, cached_events = self._cache
            ttl = getattr(settings, "RAINVIEWER_CACHE_SECONDS", 300)
            if (datetime.now(timezone.utc) - cached_at).total_seconds() < ttl:
                return cached_events

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(RAINVIEWER_API_URL, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()

                radar_frames = data.get("radar", {}).get("past", []) + data.get("radar", {}).get("nowcast", [])
                host = data.get("host", "https://tilecache.rainviewer.com")

                for frame in radar_frames:
                    ts = frame.get("time")
                    path = frame.get("path")
                    if not ts or not path:
                        continue
                    event = self.normalize_radar_frame(frame, host)
                    events.append(event)

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(radar_frames), len(events), latency_ms=latency)
                else:
                    self.health_state = "NO_DATA"
        except Exception as e:
            logger.info(f"[RAINVIEWER] Radar API request note: {e}")
            self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        self._cache = (datetime.now(timezone.utc), events)
        return events

    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return [], {}

        events = await self.fetch_radar_frames()
        results = {}
        for ev in events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return events, results


rainviewer_collector = RainViewerCollector()
