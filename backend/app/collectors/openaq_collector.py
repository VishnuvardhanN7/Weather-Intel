"""
OpenAQ Atmospheric Air Quality Collector (PS-26069).
Global real-time air quality sensor network providing PM2.5, PM10, NO2, and SO2 metrics.
Publishes normalized observations directly to Kafka `weather.raw`.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

import httpx

from app.core.config import settings
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)

OPENAQ_API_V3_URL = "https://api.openaq.org/v3/locations"


class OpenAQCollector:
    """Async collector for OpenAQ global air quality monitoring stations (API v3)."""

    def __init__(self):
        self.source_id = "openaq"
        self.collector_name = "openaq_collector"
        self.authority = "OpenAQ_Global"
        self.health_state = "DISABLED" if not getattr(settings, "OPENAQ_ENABLED", False) else "READY"

    def is_enabled(self) -> bool:
        return getattr(settings, "OPENAQ_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "OpenAQ collector is disabled in configuration (OPENAQ_ENABLED=false)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "OpenAQ Global Platform"
        meta["source_type"] = "environmental"
        return meta

    def generate_deterministic_event_id(self, city_or_station: str, ts_str: str, parameter: str) -> str:
        clean_name = city_or_station.lower().replace(" ", "_")
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ts_sec = int(dt.timestamp())
        except Exception:
            ts_sec = int(datetime.now(timezone.utc).timestamp() // 3600 * 3600)
        return f"weather_openaq_{clean_name}_{ts_sec}_{parameter}"

    def normalize_measurement(self, item: Dict[str, Any]) -> Dict[str, Any]:
        city = item.get("locality") or item.get("city") or "Delhi"
        location_name = item.get("name") or item.get("location") or city
        sensors = item.get("sensors", [])
        param = sensors[0].get("parameter", {}).get("name", "pm25") if sensors else "pm25"
        val = item.get("value", 0)
        unit = item.get("unit", "µg/m³")
        coords = item.get("coordinates", {})
        lat = coords.get("latitude")
        lon = coords.get("longitude")
        utc_ts = datetime.now(timezone.utc).isoformat()

        ev_id = self.generate_deterministic_event_id(city, utc_ts, param)

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"OpenAQ Air Quality Observation ({city}): {param.upper()}",
            "description": f"Environmental air quality sensor station at {location_name}, {city}.",
            "event_type": "air_quality_observation",
            "severity": "low",
            "city": city,
            "state": None,
            "latitude": lat,
            "longitude": lon,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "openaq",
            "source_url": "https://openaq.org",
            "timestamp": utc_ts,
            "reported_at": utc_ts,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "weather": {
                "parameter": param,
                "value": val,
                "unit": unit,
            },
            "verification_status": "SOURCE_REPORTED",
            "metadata": {
                "location_name": location_name,
                "parameter": param,
                "value": val,
                "unit": unit,
                "is_air_quality_observation": True,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def fetch_air_quality_measurements(self, country_code: str = "IN") -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return []

        headers = {}
        api_key = getattr(settings, "OPENAQ_API_KEY", "")
        if api_key:
            headers["X-API-Key"] = api_key

        params = {
            "limit": 50,
        }

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(OPENAQ_API_V3_URL, headers=headers, params=params, timeout=15.0)
                if resp.status_code in (401, 403, 410):
                    logger.info("[OPENAQ] OpenAQ v3 API key required or unauthorized (HTTP %d).", resp.status_code)
                    self.health_state = "AUTH_REQUIRED"
                    metrics_tracker.record_failure(self.source_id, "AUTH_REQUIRED")
                    return []
                if resp.status_code == 429:
                    self.health_state = "DEGRADED"
                    metrics_tracker.record_failure(self.source_id, "HTTP 429 Rate Limit")
                    return []
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                for item in results:
                    events.append(self.normalize_measurement(item))

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(results), len(events), latency_ms=latency)
                else:
                    self.health_state = "NO_DATA"
        except Exception as e:
            logger.info(f"[OPENAQ] API request note: {e}")
            if self.health_state != "AUTH_REQUIRED":
                self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        return events

    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return [], {}

        events = await self.fetch_air_quality_measurements()
        results = {}
        for ev in events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return events, results


openaq_collector = OpenAQCollector()
