"""
India Meteorological Department (IMD) Collector (PS-26069).
Official Government Weather Data Collector fetching current observations, forecasts,
district nowcasts, rainfall data, RSS feeds, and severe weather warnings.
Publishes normalized events to Kafka `weather.raw`.
"""

import asyncio
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

import httpx

from app.core.config import settings
from app.core.location_registry import get_all_locations, get_location_by_city
from app.core.imd_locations import resolve_imd_location
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    return re.sub(r"[^\w]+", "_", text.strip().lower())


class IMDCollector:
    """Async collector for official IMD weather API endpoints and public RSS feeds."""

    def __init__(self):
        self.source_id = "imd"
        self.collector_name = "imd_collector"
        self.authority = "official_government_source"
        self._cache: Dict[str, Tuple[datetime, List[Dict[str, Any]]]] = {}

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        if cache_key in self._cache:
            cached_at, data = self._cache[cache_key]
            cache_ttl = getattr(settings, "IMD_CACHE_SECONDS", 300)
            if (datetime.now(timezone.utc) - cached_at).total_seconds() < cache_ttl:
                logger.debug(f"[IMD] Serving cached response for '{cache_key}'")
                return data
        return None

    def _set_cache(self, cache_key: str, data: List[Dict[str, Any]]):
        self._cache[cache_key] = (datetime.now(timezone.utc), data)

    def generate_deterministic_event_id(self, category: str, location_slug: str, ts_str: str) -> str:
        """Generate deterministic event ID for IMD records."""
        clean_loc = slugify(location_slug)
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            hour_ts = int(dt.replace(minute=0, second=0, microsecond=0).timestamp())
        except Exception:
            hour_ts = int(datetime.now(timezone.utc).timestamp() // 3600 * 3600)
        return f"weather_imd_{category}_{clean_loc}_{hour_ts}"

    def get_source_header(self) -> Dict[str, str]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "India Meteorological Department"
        meta["source_type"] = "government_weather"
        return meta

    def parse_warning_severity_and_category(self, warning_text: str) -> Tuple[str, str, str]:
        """Map IMD warning description to category, event_type, and severity level."""
        text_lower = warning_text.lower()
        
        category = "heavy_rainfall"
        event_type = "weather_warning"
        severity = "moderate"

        if "heavy rain" in text_lower or "extremely heavy" in text_lower or "downpour" in text_lower:
            category = "heavy_rainfall"
            severity = "critical" if "extremely heavy" in text_lower else "high"
        elif "thunderstorm" in text_lower or "lightning" in text_lower or "squall" in text_lower:
            category = "thunderstorm"
            severity = "high"
        elif "heat wave" in text_lower or "severe heat" in text_lower:
            category = "heatwave"
            severity = "critical" if "severe" in text_lower else "high"
        elif "cyclone" in text_lower or "depression" in text_lower or "gale" in text_lower:
            category = "cyclone"
            severity = "critical"
        elif "fog" in text_lower:
            category = "fog"
            severity = "moderate"
        elif "dust storm" in text_lower:
            category = "dust_storm"
            severity = "high"

        return category, event_type, severity

    # ==========================================
    # 1. CURRENT WEATHER ADAPTER
    # ==========================================
    async def fetch_current_weather(self, locations: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Fetch IMD current weather observations across Indian cities."""
        if not getattr(settings, "IMD_ENABLED", True):
            return []

        cache_key = "current_weather"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if locations is None:
            locations = get_all_locations()

        api_url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/public/api/current"
        headers = {}
        if getattr(settings, "IMD_API_KEY", ""):
            headers["X-API-KEY"] = settings.IMD_API_KEY

        start_time = datetime.now(timezone.utc)
        events = []

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, headers=headers, timeout=10.0)
                if resp.status_code in (401, 403):
                    logger.warning("[IMD] Authentication required — source waiting for credentials")
                    metrics_tracker.record_failure(self.source_id, "AUTH_REQUIRED")
                    return []
                resp.raise_for_status()
                data = resp.json()

                # Process payload array if returned from live IMD endpoint
                records = data if isinstance(data, list) else data.get("data", [])
                for item in records:
                    city_name = item.get("station") or item.get("city") or "Delhi"
                    loc = resolve_imd_location(city_name, item.get("state"))
                    ts = item.get("timestamp") or datetime.now(timezone.utc).isoformat()
                    
                    ev = {
                        "event_id": self.generate_deterministic_event_id("current", loc["city"], ts),
                        "source": self.source_id,
                        "source_metadata": self.get_source_header(),
                        "source_type": "imd",
                        "timestamp": ts,
                        "reported_at": ts,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "title": f"IMD Current Weather in {loc['city']}, {loc['state']}",
                        "description": f"Official IMD observation for {loc['city']}: Temp {item.get('temperature')}°C, Humidity {item.get('humidity')}%.",
                        "event_type": "weather_observation",
                        "severity": "low",
                        "location": loc,
                        "city": loc["city"],
                        "state": loc["state"],
                        "latitude": loc["latitude"],
                        "longitude": loc["longitude"],
                        "weather": {
                            "temperature": float(item.get("temperature", 0) or 0),
                            "humidity": int(item.get("humidity", 0) or 0),
                            "rainfall": float(item.get("rainfall", 0) or 0),
                            "wind_speed": float(item.get("wind_speed", 0) or 0),
                            "wind_direction": item.get("wind_direction"),
                            "pressure": item.get("pressure"),
                            "visibility": item.get("visibility"),
                        },
                        "verification_status": "SOURCE_REPORTED",
                        "pipeline": {"stage": "RAW"},
                    }
                    events.append(ev)

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                metrics_tracker.record_success(self.source_id, len(records), len(events), latency_ms=latency)
        except Exception as e:
            logger.info(f"[IMD] Public API current endpoint unreachable or auth required: {e}")
            metrics_tracker.record_failure(self.source_id, str(e))

        self._set_cache(cache_key, events)
        return events

    # ==========================================
    # 2. CITY FORECAST ADAPTER
    # ==========================================
    async def fetch_city_forecast(self, locations: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Fetch IMD 7-day city weather forecast."""
        cache_key = "city_forecast"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        api_url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/public/api/forecast"
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, timeout=10.0)
                if resp.status_code in (401, 403):
                    logger.warning("[IMD] Authentication required for city forecast endpoint")
                    return []
                resp.raise_for_status()
                data = resp.json()
                records = data if isinstance(data, list) else data.get("data", [])

                for item in records:
                    city_name = item.get("city") or "Delhi"
                    loc = resolve_imd_location(city_name)
                    forecast_date = item.get("forecast_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    ev_id = f"weather_imd_forecast_{slugify(loc['city'])}_{forecast_date}"
                    
                    events.append({
                        "event_id": ev_id,
                        "source": self.source_id,
                        "source_metadata": self.get_source_header(),
                        "source_type": "imd",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "reported_at": datetime.now(timezone.utc).isoformat(),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "title": f"IMD City Forecast for {loc['city']} ({forecast_date})",
                        "description": f"Official IMD 7-day forecast for {loc['city']}: {item.get('weather_condition', 'Forecast Available')}.",
                        "event_type": "weather_forecast",
                        "severity": "low",
                        "location": loc,
                        "city": loc["city"],
                        "state": loc["state"],
                        "latitude": loc["latitude"],
                        "longitude": loc["longitude"],
                        "weather": {
                            "temp_max": item.get("temp_max"),
                            "temp_min": item.get("temp_min"),
                            "condition": item.get("weather_condition"),
                        },
                        "verification_status": "SOURCE_REPORTED",
                        "pipeline": {"stage": "RAW"},
                    })
        except Exception as e:
            logger.info(f"[IMD] City forecast API request note: {e}")

        self._set_cache(cache_key, events)
        return events

    # ==========================================
    # 3. DISTRICT NOWCAST ADAPTER
    # ==========================================
    async def fetch_district_nowcast(self, districts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch IMD district-wise 3-hour nowcast warnings."""
        cache_key = "district_nowcast"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        api_url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/public/api/nowcast"
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, timeout=10.0)
                if resp.status_code in (401, 403):
                    logger.warning("[IMD] Authentication required for district nowcast")
                    return []
                resp.raise_for_status()
                records = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])

                for item in records:
                    dist_name = item.get("district") or "Delhi"
                    loc = resolve_imd_location(dist_name, item.get("state"))
                    ts = item.get("issued_at") or datetime.now(timezone.utc).isoformat()
                    ev_id = self.generate_deterministic_event_id("nowcast", loc["city"], ts)

                    events.append({
                        "event_id": ev_id,
                        "source": self.source_id,
                        "source_metadata": self.get_source_header(),
                        "source_type": "imd",
                        "timestamp": ts,
                        "reported_at": ts,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "title": f"IMD District Nowcast: {dist_name}",
                        "description": item.get("nowcast_text", f"IMD 3-hour nowcast bulletin for {dist_name}."),
                        "event_type": "weather_nowcast",
                        "severity": "moderate",
                        "location": loc,
                        "city": loc["city"],
                        "state": loc["state"],
                        "latitude": loc["latitude"],
                        "longitude": loc["longitude"],
                        "verification_status": "SOURCE_REPORTED",
                        "pipeline": {"stage": "RAW"},
                    })
        except Exception as e:
            logger.info(f"[IMD] District nowcast API note: {e}")

        self._set_cache(cache_key, events)
        return events

    # ==========================================
    # 4. DISTRICT WARNING ADAPTER
    # ==========================================
    async def fetch_district_warnings(self, districts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch IMD district severe weather warnings."""
        cache_key = "district_warnings"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        api_url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/public/api/warnings"
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, timeout=10.0)
                if resp.status_code in (401, 403):
                    logger.warning("[IMD] Authentication required for district warnings")
                    return []
                resp.raise_for_status()
                records = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])

                for item in records:
                    dist_name = item.get("district") or "Delhi"
                    loc = resolve_imd_location(dist_name, item.get("state"))
                    warn_text = item.get("warning_text") or item.get("warning") or "Heavy Rainfall Warning"
                    category, event_type, severity = self.parse_warning_severity_and_category(warn_text)
                    warn_id = item.get("warning_id") or hashlib.md5(f"{dist_name}_{warn_text}".encode()).hexdigest()[:10]
                    ev_id = f"weather_imd_warning_{warn_id}"

                    events.append({
                        "event_id": ev_id,
                        "source": self.source_id,
                        "source_metadata": self.get_source_header(),
                        "source_type": "imd",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "reported_at": datetime.now(timezone.utc).isoformat(),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "title": f"OFFICIAL IMD WARNING: {warn_text.title()} ({dist_name})",
                        "description": f"Official IMD Severe Weather Warning for {dist_name}, {loc['state']}: {warn_text}. Valid until {item.get('valid_until', '18:00 IST')}.",
                        "event_type": event_type,
                        "category": category,
                        "severity": severity,
                        "location": loc,
                        "city": loc["city"],
                        "state": loc["state"],
                        "latitude": loc["latitude"],
                        "longitude": loc["longitude"],
                        "verification_status": "SOURCE_REPORTED",
                        "pipeline": {"stage": "RAW"},
                    })
        except Exception as e:
            logger.info(f"[IMD] District warning API note: {e}")

        self._set_cache(cache_key, events)
        return events

    # ==========================================
    # 5. DISTRICT & STATE RAINFALL ADAPTERS
    # ==========================================
    async def fetch_district_rainfall(self, districts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch IMD district-wise rainfall observations."""
        cache_key = "district_rainfall"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        api_url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/public/api/rainfall/district"
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, timeout=10.0)
                if resp.status_code in (401, 403):
                    return []
                resp.raise_for_status()
                records = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])

                for item in records:
                    dist = item.get("district") or "Delhi"
                    loc = resolve_imd_location(dist, item.get("state"))
                    date_str = item.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    ev_id = f"weather_imd_rainfall_{slugify(dist)}_{date_str}"

                    events.append({
                        "event_id": ev_id,
                        "source": self.source_id,
                        "source_metadata": self.get_source_header(),
                        "source_type": "imd",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "reported_at": datetime.now(timezone.utc).isoformat(),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "title": f"IMD District Rainfall: {dist} ({date_str})",
                        "description": f"Official IMD rainfall observation for {dist}: {item.get('rainfall_mm', 0)} mm.",
                        "event_type": "rainfall_observation",
                        "severity": "low",
                        "location": loc,
                        "city": loc["city"],
                        "state": loc["state"],
                        "latitude": loc["latitude"],
                        "longitude": loc["longitude"],
                        "weather": {"rainfall": float(item.get("rainfall_mm", 0) or 0)},
                        "verification_status": "SOURCE_REPORTED",
                        "pipeline": {"stage": "RAW"},
                    })
        except Exception as e:
            logger.info(f"[IMD] District rainfall API note: {e}")

        self._set_cache(cache_key, events)
        return events

    async def fetch_state_rainfall(self, states: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch IMD state-wise cumulative rainfall summary."""
        cache_key = "state_rainfall"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        api_url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/public/api/rainfall/state"
        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, timeout=10.0)
                if resp.status_code in (401, 403):
                    return []
                resp.raise_for_status()
                records = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])

                for item in records:
                    st_name = item.get("state") or "Maharashtra"
                    loc = resolve_imd_location(st_name, st_name)
                    date_str = item.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    ev_id = f"weather_imd_state_rainfall_{slugify(st_name)}_{date_str}"

                    events.append({
                        "event_id": ev_id,
                        "source": self.source_id,
                        "source_metadata": self.get_source_header(),
                        "source_type": "imd",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "reported_at": datetime.now(timezone.utc).isoformat(),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "title": f"IMD State Rainfall Summary: {st_name}",
                        "description": f"Official IMD cumulative rainfall report for {st_name}: {item.get('actual_rainfall_mm', 0)} mm.",
                        "event_type": "rainfall_observation",
                        "severity": "low",
                        "location": loc,
                        "city": loc["city"],
                        "state": loc["state"],
                        "latitude": loc["latitude"],
                        "longitude": loc["longitude"],
                        "weather": {"rainfall": float(item.get("actual_rainfall_mm", 0) or 0)},
                        "verification_status": "SOURCE_REPORTED",
                        "pipeline": {"stage": "RAW"},
                    })
        except Exception as e:
            logger.info(f"[IMD] State rainfall API note: {e}")

        self._set_cache(cache_key, events)
        return events

    async def fetch_aws_observations(self) -> List[Dict[str, Any]]:
        """Fetch AWS/ARG automatic weather station observations where accessible."""
        api_url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/public/api/aws"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, timeout=10.0)
                if resp.status_code in (401, 403):
                    return []
                resp.raise_for_status()
                return resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])
        except Exception:
            return []

    # ==========================================
    # 6. PUBLIC IMD RSS FEED ADAPTER (SECONDARY INGESTION)
    # ==========================================
    async def fetch_imd_rss(self) -> List[Dict[str, Any]]:
        """
        Fetch official public IMD RSS bulletins / district nowcasts as a secondary public ingestion mechanism.
        Public RSS URL: https://mausam.imd.gov.in/responsive/rss_district_nowcast.php
        """
        cache_key = "imd_rss"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        rss_urls = [
            "https://mausam.imd.gov.in/responsive/rss_district_nowcast.php",
            "https://mausam.imd.gov.in/rss.php",
        ]

        events = []
        for url in rss_urls:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=10.0, follow_redirects=True)
                    if resp.status_code == 200 and resp.text:
                        root = ET.fromstring(resp.text)
                        channel = root.find("channel")
                        if channel is not None:
                            for item in channel.findall("item"):
                                title_elem = item.find("title")
                                desc_elem = item.find("description")
                                pub_date_elem = item.find("pubDate")

                                title_text = title_elem.text if title_elem is not None and title_elem.text else "IMD Weather Warning"
                                desc_text = desc_elem.text if desc_elem is not None and desc_elem.text else title_text

                                # Extract district/state if present in title/desc
                                dist_match = re.search(r"district\s*:\s*([\w\s]+)", desc_text, re.IGNORECASE)
                                dist_name = dist_match.group(1).strip() if dist_match else "Delhi"

                                loc = resolve_imd_location(dist_name)
                                category, event_type, severity = self.parse_warning_severity_and_category(f"{title_text} {desc_text}")
                                
                                item_hash = hashlib.md5(f"{title_text}_{desc_text}".encode()).hexdigest()[:10]
                                ev_id = f"weather_imd_rss_{item_hash}"

                                events.append({
                                    "event_id": ev_id,
                                    "source": self.source_id,
                                    "source_metadata": self.get_source_header(),
                                    "source_type": "imd",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "reported_at": datetime.now(timezone.utc).isoformat(),
                                    "created_at": datetime.now(timezone.utc).isoformat(),
                                    "title": f"OFFICIAL IMD RSS: {title_text}",
                                    "description": f"Official IMD Bulletin: {desc_text}",
                                    "event_type": event_type,
                                    "category": category,
                                    "severity": severity,
                                    "location": loc,
                                    "city": loc["city"],
                                    "state": loc["state"],
                                    "latitude": loc["latitude"],
                                    "longitude": loc["longitude"],
                                    "verification_status": "SOURCE_REPORTED",
                                    "pipeline": {"stage": "RAW"},
                                })
                        break
            except Exception as e:
                logger.debug(f"[IMD] RSS endpoint {url} note: {e}")

        self._set_cache(cache_key, events)
        return events

    # ==========================================
    # 7. MAIN COLLECT & PUBLISH ALL ADAPTER
    # ==========================================
    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        """
        Execute all available IMD data adapters (current, forecast, nowcast, warnings, rainfall, RSS),
        normalize records into ATMOS event format, and publish to Kafka topic `weather.raw`.
        """
        if not getattr(settings, "IMD_ENABLED", True):
            logger.info("[IMD] IMD collector disabled in settings.")
            return [], {}

        logger.info("[IMD] Fetching official weather data from IMD endpoints & RSS feeds...")
        
        # Execute adapters concurrently
        results_list = await asyncio.gather(
            self.fetch_current_weather(),
            self.fetch_city_forecast(),
            self.fetch_district_nowcast(),
            self.fetch_district_warnings(),
            self.fetch_district_rainfall(),
            self.fetch_state_rainfall(),
            self.fetch_imd_rss(),
            return_exceptions=True
        )

        all_events: List[Dict[str, Any]] = []
        for res in results_list:
            if isinstance(res, list):
                all_events.extend(res)

        publish_results: Dict[str, bool] = {}
        for ev in all_events:
            ev_id = ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            publish_results[ev_id] = success

        published_count = sum(1 for status in publish_results.values() if status)
        logger.info(
            f"[IMD] Cycle completed: {len(all_events)} records collected across adapters, {published_count} published to weather.raw"
        )
        return all_events, publish_results


imd_collector = IMDCollector()
