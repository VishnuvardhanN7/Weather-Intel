"""
NOAA NCEI Climate Data Online Collector (PS-26069).
National Oceanic and Atmospheric Administration (NOAA) National Centers for Environmental Information.
Publishes normalized climate events directly to Kafka `weather.raw`.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

import httpx

from app.core.config import settings
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)

NOAA_API_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"


class NOAACollector:
    """Async collector for NOAA NCEI Climate Data Online archives."""

    def __init__(self):
        self.source_id = "noaa_ncei"
        self.collector_name = "noaa_ncei_collector"
        self.authority = "NOAA_NCEI"
        self.health_state = "DISABLED" if not getattr(settings, "NOAA_ENABLED", False) else "READY"

    def is_enabled(self) -> bool:
        return getattr(settings, "NOAA_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "NOAA NCEI collector is disabled in configuration (NOAA_ENABLED=false)"
        api_key = getattr(settings, "NOAA_API_KEY", "") or ""
        if not api_key.strip():
            return False, "NOAA API key missing (NOAA_API_KEY)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "NOAA National Centers for Environmental Information"
        meta["source_type"] = "climate_weather"
        return meta

    def generate_deterministic_event_id(self, station_id: str, date_str: str) -> str:
        clean_station = station_id.lower().replace(":", "_").replace(" ", "_")
        return f"weather_noaa_ncei_{clean_station}_{date_str}"

    def normalize_observation(self, item: Dict[str, Any]) -> Dict[str, Any]:
        station = item.get("station", "GHCND:UNKNOWN")
        date_str = item.get("date", "").split("T")[0]
        datatype = item.get("datatype", "TEMP")
        val = item.get("value")

        ev_id = self.generate_deterministic_event_id(station, f"{date_str}_{datatype}")

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"NOAA NCEI Climate Observation ({station})",
            "description": f"NOAA GHCND climate archive observation: Datatype: {datatype}, Value: {val}.",
            "event_type": "climate_weather",
            "severity": "low",
            "city": None,
            "state": None,
            "latitude": None,
            "longitude": None,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "noaa_ncei",
            "source_url": "https://www.ncdc.noaa.gov/cdo-web/",
            "timestamp": item.get("date") or datetime.now(timezone.utc).isoformat(),
            "reported_at": item.get("date") or datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": "SOURCE_REPORTED",
            "metadata": {
                "station_id": station,
                "datatype": datatype,
                "value": val,
                "dataset_id": "GHCND",
                "is_noaa_climate_observation": True,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def fetch_climate_data(self) -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            if not self.is_enabled():
                self.health_state = "DISABLED"
            else:
                self.health_state = "AUTH_REQUIRED"
            return []

        api_key = getattr(settings, "NOAA_API_KEY", "")

        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        headers = {"token": api_key}
        params = {
            "datasetid": "GHCND",
            "startdate": start_date,
            "enddate": end_date,
            "limit": 50,
        }

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(NOAA_API_URL, headers=headers, params=params, timeout=15.0)
                if resp.status_code in (401, 403):
                    logger.warning("[NOAA_NCEI] Authentication token rejected.")
                    self.health_state = "AUTH_REQUIRED"
                    metrics_tracker.record_failure(self.source_id, "AUTH_REQUIRED")
                    return []
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                for item in results:
                    events.append(self.normalize_observation(item))

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(results), len(events), latency_ms=latency)
                else:
                    self.health_state = "NO_DATA"
        except Exception as e:
            logger.info(f"[NOAA_NCEI] API request note: {e}")
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

        events = await self.fetch_climate_data()
        results = {}
        for ev in events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return events, results


noaa_ncei_collector = NOAACollector()
