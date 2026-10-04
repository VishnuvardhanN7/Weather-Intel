"""
NASA POWER Meteorological Data Collector (PS-26069).
NASA Prediction Of Worldwide Energy Resources (POWER) global meteorological API.
Publishes normalized environmental observations directly to Kafka `weather.raw`.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

import httpx

from app.core.config import settings
from app.core.location_registry import get_all_locations
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)

NASA_POWER_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


class NasaPowerCollector:
    """Async collector for NASA POWER climatological and meteorological observations."""

    def __init__(self):
        self.source_id = "nasa_power"
        self.collector_name = "nasa_power_collector"
        self.authority = "NASA_POWER"
        self.health_state = "DISABLED" if not getattr(settings, "NASA_POWER_ENABLED", False) else "READY"
        self._cache: Dict[str, Tuple[datetime, List[Dict[str, Any]]]] = {}

    def is_enabled(self) -> bool:
        return getattr(settings, "NASA_POWER_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "NASA POWER collector is disabled in configuration (NASA_POWER_ENABLED=false)"
        return True, "Configuration valid"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "NASA Langley Research Center"
        meta["source_type"] = "climate_weather"
        return meta

    def generate_deterministic_event_id(self, city: str, date_str: str) -> str:
        clean_city = city.lower().replace(" ", "_")
        return f"weather_nasa_power_{clean_city}_{date_str}"

    def normalize_point_observation(self, data: Dict[str, Any], city_info: Dict[str, Any], dt_key: str = "20261002") -> Dict[str, Any]:
        city = city_info["city"]
        state = city_info.get("state", "")
        lat = city_info["latitude"]
        lon = city_info["longitude"]

        properties = data.get("properties", {})
        parameter_data = properties.get("parameter", {})

        t2m = parameter_data.get("T2M", {})
        rh2m = parameter_data.get("RH2M", {})
        precip = parameter_data.get("PRECTOTCORR", {})
        ws10m = parameter_data.get("WS10M", {})
        solar = parameter_data.get("ALLSKY_SFC_SW_DWN", {})

        temp = t2m.get(dt_key, 25.0) if isinstance(t2m, dict) else 25.0
        rh = rh2m.get(dt_key, 60.0) if isinstance(rh2m, dict) else 60.0
        pr = precip.get(dt_key, 0.0) if isinstance(precip, dict) else 0.0
        ws = ws10m.get(dt_key, 10.0) if isinstance(ws10m, dict) else 10.0
        sol = solar.get(dt_key, 5.0) if isinstance(solar, dict) else 5.0

        date_iso = f"{dt_key[:4]}-{dt_key[4:6]}-{dt_key[6:]}" if len(dt_key) >= 8 else "2026-10-02"
        ev_id = self.generate_deterministic_event_id(city, dt_key)

        return {
            "id": ev_id,
            "event_id": ev_id,
            "title": f"NASA POWER Environmental Weather Observation ({city})",
            "description": (
                f"NASA POWER satellite & model meteorology for {city}, {state}: "
                f"Temp: {temp}°C, Humidity: {rh}%, Precip: {pr}mm, "
                f"Wind: {ws}m/s, Solar: {sol}kWh/m²."
            ),
            "event_type": "environmental_weather_observation",
            "severity": "low",
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "nasa_power",
            "source_url": "https://power.larc.nasa.gov",
            "timestamp": f"{date_iso}T12:00:00Z",
            "reported_at": f"{date_iso}T12:00:00Z",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "weather": {
                "temperature": float(temp if temp is not None else 0),
                "humidity": float(rh if rh is not None else 0),
                "precipitation": float(pr if pr is not None else 0),
                "wind_speed": float(ws if ws is not None else 0),
                "solar_radiation": float(sol if sol is not None else 0),
            },
            "verification_status": "SOURCE_REPORTED",
            "metadata": {
                "community": "RE",
                "temp_c": float(temp if temp is not None else 0),
                "is_nasa_power_observation": True,
            },
            "pipeline": {"stage": "RAW"},
        }

    async def fetch_location_data(self, client: Any, loc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        evs = await self.fetch_point_meteorology(loc)
        return evs[0] if evs else None

    async def fetch_point_meteorology(self, loc: Dict[str, Any]) -> List[Dict[str, Any]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return []

        city = loc["city"]
        state = loc.get("state", "")
        lat = loc["latitude"]
        lon = loc["longitude"]

        end_dt = datetime.now(timezone.utc) - timedelta(days=2)
        start_dt = end_dt - timedelta(days=1)
        start_str = start_dt.strftime("%Y%m%d")
        end_str = end_dt.strftime("%Y%m%d")

        params = {
            "parameters": "T2M,RH2M,PRECTOTCORR,WS10M,ALLSKY_SFC_SW_DWN",
            "community": "RE",
            "longitude": lon,
            "latitude": lat,
            "start": start_str,
            "end": end_str,
            "format": "JSON",
        }

        start_time = datetime.now(timezone.utc)
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(NASA_POWER_API_URL, params=params, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()

                properties = data.get("properties", {})
                parameter_data = properties.get("parameter", {})
                t2m = parameter_data.get("T2M", {})

                if not isinstance(t2m, dict) or not t2m:
                    return []

                for dt_key in t2m.keys():
                    evt = self.normalize_point_observation(data, loc, dt_key)
                    events.append(evt)

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                if events:
                    self.health_state = "HEALTHY"
                    metrics_tracker.record_success(self.source_id, len(t2m), len(events), latency_ms=latency)
        except Exception as e:
            logger.info(f"[NASA_POWER] API request note for {city}: {e}")
            self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        return events

    async def fetch_and_publish_all(self, max_locations: int = 5) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            self.health_state = "DISABLED"
            return [], {}

        locations = get_all_locations()[:max_locations]
        all_events = []
        for loc in locations:
            evs = await self.fetch_point_meteorology(loc)
            all_events.extend(evs)

        results = {}
        for ev in all_events:
            ev_id = ev.get("id") or ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success

        return all_events, results


nasa_power_collector = NasaPowerCollector()
