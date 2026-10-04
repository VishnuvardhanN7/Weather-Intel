"""
USGS Water Services Hydrology Collector (PS-26069).
US Geological Survey (USGS) Instantaneous Water Services streamflow & gauge height monitoring.
Publishes normalized hydrological observations directly to Kafka `weather.raw`.
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

USGS_WATER_API_URL = "https://waterservices.usgs.gov/nwis/iv/"


class USGSWaterCollector:
    """Async collector for USGS Water Services streamflow and gauge height monitoring."""

    def __init__(self):
        self.source_id = "usgs_water"
        self.collector_name = "usgs_water_collector"
        self.authority = "USGS_Water"
        self.health_state = "DISABLED" if not getattr(settings, "USGS_WATER_ENABLED", False) else "READY"

    def is_enabled(self) -> bool:
        return getattr(settings, "USGS_WATER_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "USGS Water collector is disabled in configuration (USGS_WATER_ENABLED=false)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "US Geological Survey"
        meta["source_type"] = "hydrology"
        return meta

    def generate_deterministic_event_id(self, site_id: str, ts_str: str) -> str:
        clean_site = site_id.lower().replace(" ", "_")
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ts_sec = int(dt.timestamp())
        except Exception:
            ts_sec = int(datetime.now(timezone.utc).timestamp() // 3600 * 3600)
        return f"weather_usgs_water_{clean_site}_{ts_sec}"

    def normalize_time_series(self, ts_item: Dict[str, Any]) -> Dict[str, Any]:
        source_info = ts_item.get("sourceInfo", {})
        site_name = source_info.get("siteName", "USGS Monitoring Site")
        site_code = source_info.get("siteCode", [{}])[0].get("value", "00000000")
        geo = source_info.get("geoLocation", {}).get("geogLocation", {})
        lat = geo.get("latitude")
        lon = geo.get("longitude")

        variable = ts_item.get("variable", {})
        var_name = variable.get("variableName", "Streamflow")
        unit = variable.get("unit", {}).get("unitCode", "cfs")

        values_list = ts_item.get("values", [{}])[0].get("value", [])
        latest_val = values_list[-1] if values_list else {}
        val = str(latest_val.get("value", 0) or 0)
        ts = latest_val.get("dateTime") or datetime.now(timezone.utc).isoformat()

        ev_id = self.generate_deterministic_event_id(site_code, ts)

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"USGS Hydrology Observation: {site_name}",
            "description": f"USGS Water Services instantaneous hydrology reading for {site_name}. Metric: {var_name} = {val} {unit}.",
            "event_type": "hydrology_observation",
            "severity": "low",
            "city": None,
            "state": None,
            "latitude": lat,
            "longitude": lon,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "usgs_water",
            "source_url": f"https://waterdata.usgs.gov/nwis/uv?site_no={site_code}",
            "timestamp": ts,
            "reported_at": ts,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "weather": {
                "value": val,
                "unit": unit,
            },
            "verification_status": "SOURCE_REPORTED",
            "metadata": {
                "site_code": site_code,
                "variable_name": var_name,
                "value": val,
                "unit": unit,
                "is_hydrology_observation": True,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def fetch_instantaneous_values(self, format_type: str = "json") -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return []

        params = {
            "format": "json",
            "sites": "01646500",  # Example reference site
            "parameterCd": "00060,00065",  # Streamflow (cfs) & Gauge height (ft)
            "siteStatus": "all",
        }

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(USGS_WATER_API_URL, params=params, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()

                time_series = data.get("value", {}).get("timeSeries", [])
                for ts_item in time_series:
                    events.append(self.normalize_time_series(ts_item))

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(time_series), len(events), latency_ms=latency)
                else:
                    self.health_state = "NO_DATA"
        except Exception as e:
            logger.info(f"[USGS_WATER] API request note: {e}")
            self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        return events

    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return [], {}

        events = await self.fetch_instantaneous_values()
        results = {}
        for ev in events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return events, results


usgs_water_collector = USGSWaterCollector()
