"""
Open-Meteo Weather Data Collector (PS-26069).
Fetches live and historical meteorological observations from Open-Meteo API.
Publishes normalized events to Kafka `weather.raw` topic.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

import httpx

from app.core.location_registry import get_all_locations, get_location_by_city
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Open-Meteo WMO Weather Interpretation Codes Map
WMO_CODE_MAP = {
    0: ("Clear Sky", "other", "low"),
    1: ("Mainly Clear", "other", "low"),
    2: ("Partly Cloudy", "other", "low"),
    3: ("Overcast", "other", "low"),
    45: ("Fog", "fog", "moderate"),
    48: ("Depositing Rime Fog", "fog", "moderate"),
    51: ("Light Drizzle", "rainfall", "low"),
    53: ("Moderate Drizzle", "rainfall", "low"),
    55: ("Dense Drizzle", "rainfall", "moderate"),
    56: ("Freezing Drizzle", "rainfall", "moderate"),
    57: ("Dense Freezing Drizzle", "rainfall", "moderate"),
    61: ("Slight Rain", "rainfall", "low"),
    63: ("Moderate Rain", "rainfall", "moderate"),
    65: ("Heavy Rain", "rainfall", "high"),
    66: ("Freezing Rain", "rainfall", "moderate"),
    67: ("Heavy Freezing Rain", "rainfall", "high"),
    71: ("Slight Snow Fall", "other", "low"),
    73: ("Moderate Snow Fall", "other", "moderate"),
    75: ("Heavy Snow Fall", "other", "high"),
    80: ("Slight Rain Showers", "rainfall", "low"),
    81: ("Moderate Rain Showers", "rainfall", "moderate"),
    82: ("Violent Rain Showers", "rainfall", "high"),
    95: ("Thunderstorm", "thunderstorm", "high"),
    96: ("Thunderstorm with Hail", "thunderstorm", "high"),
    99: ("Heavy Thunderstorm", "thunderstorm", "critical"),
}


def slugify(text: str) -> str:
    return re.sub(r"[^\w]+", "_", text.strip().lower())


def generate_deterministic_event_id(city: str, dt_iso: str) -> str:
    """Generate a deterministic event ID based on city and observation hour timestamp."""
    try:
        dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
        # Round timestamp to nearest hour for deduplication
        hour_ts = int(dt.replace(minute=0, second=0, microsecond=0).timestamp())
    except Exception:
        hour_ts = int(datetime.now(timezone.utc).timestamp() // 3600 * 3600)
    city_slug = slugify(city)
    return f"weather_open_meteo_{city_slug}_{hour_ts}"


class OpenMeteoCollector:
    """Async collector for Open-Meteo live and historical weather endpoints."""

    def __init__(self):
        self.source_id = "open_meteo"
        self.collector_name = "open_meteo_collector"

    def parse_wmo_code(self, code: int, temp: float = 20.0, precipitation: float = 0.0) -> tuple:
        """Map WMO code and meteorological metrics to SIH event_type and severity."""
        wmo_info = WMO_CODE_MAP.get(code, ("Weather Observation", "other", "low"))
        label, event_type, severity = wmo_info

        if temp >= 42.0:
            return "Extreme Heatwave", "heatwave", "critical"
        elif temp >= 40.0:
            return "Heatwave Warning", "heatwave", "high"
        elif precipitation >= 50.0:
            return "Extreme Rainfall", "rainfall", "critical"
        elif precipitation >= 20.0:
            return "Heavy Rainfall", "rainfall", "high"

        # Routine weather observation
        if event_type == "other":
            return label, "weather_observation", "low"

        return label, event_type, severity

    async def fetch_current_batch(
        self,
        locations: List[Dict[str, Any]],
        timeout: float = 15.0,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Fetch current weather for a batch of locations in a single multi-coordinate HTTP request.
        Open-Meteo accepts comma-separated lists: latitude=28.61,19.07&longitude=77.20,72.87
        """
        if not locations:
            return []

        lats = ",".join(str(loc["latitude"]) for loc in locations)
        lons = ",".join(str(loc["longitude"]) for loc in locations)

        params = {
            "latitude": lats,
            "longitude": lons,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,rain,showers,weather_code,cloud_cover,"
                "visibility,wind_speed_10m,wind_direction_10m,wind_gusts_10m,surface_pressure"
            ),
            "timezone": "Asia/Kolkata",
        }

        start_time = datetime.now(timezone.utc)
        response_data = None

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(OPEN_METEO_FORECAST_URL, params=params, timeout=timeout)
                    resp.raise_for_status()
                    response_data = resp.json()
                    break
            except Exception as e:
                logger.warning(
                    f"[OPEN_METEO] Request attempt {attempt}/{max_retries} failed: {e}"
                )
                if attempt == max_retries:
                    latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    metrics_tracker.record_failure(self.source_id, str(e))
                    return []
                await asyncio.sleep(2 ** (attempt - 1))

        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        # Open-Meteo returns a single object if 1 location requested, or a list if multiple
        if isinstance(response_data, dict):
            raw_list = [response_data]
        elif isinstance(response_data, list):
            raw_list = response_data
        else:
            raw_list = []

        normalized_events = []
        for idx, item in enumerate(raw_list):
            loc = locations[idx] if idx < len(locations) else locations[0]
            event = self.normalize_current_observation(loc, item)
            if event:
                normalized_events.append(event)

        metrics_tracker.record_success(
            self.source_id,
            records_received=len(raw_list),
            records_published=len(normalized_events),
            latency_ms=latency_ms,
        )

        logger.info(
            f"[OPEN_METEO] Successfully fetched and normalized {len(normalized_events)} location observations in {latency_ms:.1f}ms"
        )
        return normalized_events

    def normalize_current_observation(self, loc: Dict[str, Any], raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize raw Open-Meteo API current block into ATMOS event schema."""
        current = raw.get("current", {})
        if not current:
            return None

        city = loc["city"]
        state = loc.get("state", "")
        lat = loc["latitude"]
        lon = loc["longitude"]

        obs_time = current.get("time") or datetime.now(timezone.utc).isoformat()
        wmo_code = int(current.get("weather_code", 0) or 0)
        temp = float(current.get("temperature_2m", 0) or 0)
        precip = float(current.get("precipitation", 0) or 0)

        condition_label, event_type, severity = self.parse_wmo_code(wmo_code, temp=temp, precipitation=precip)
        event_id = generate_deterministic_event_id(city, obs_time)

        humidity = current.get("relative_humidity_2m")
        wind_speed = current.get("wind_speed_10m")
        wind_deg = current.get("wind_direction_10m")
        pressure = current.get("surface_pressure")
        cloud_cover = current.get("cloud_cover")
        visibility = current.get("visibility")

        title = f"{condition_label} in {city}, {state}" if state else f"{condition_label} in {city}"
        description = (
            f"Open-Meteo observation for {city}, {state}: {condition_label}. "
            f"Temperature: {temp:.1f}°C, Humidity: {humidity}%, "
            f"Wind: {wind_speed} km/h from {wind_deg}°, Cloud Cover: {cloud_cover}%."
        )

        source_meta = get_source_metadata(self.source_id, collector=self.collector_name)

        return {
            "event_id": event_id,
            "source": self.source_id,
            "source_metadata": source_meta,
            "source_type": "open_meteo",
            "timestamp": obs_time,
            "reported_at": obs_time,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "description": description,
            "event_type": event_type,
            "severity": severity,
            "location": {
                "city": city,
                "state": state,
                "latitude": lat,
                "longitude": lon,
            },
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon,
            "weather": {
                "temperature": temp,
                "humidity": humidity,
                "apparent_temperature": current.get("apparent_temperature"),
                "precipitation": precip,
                "rain": current.get("rain"),
                "showers": current.get("showers"),
                "cloud_cover": cloud_cover,
                "visibility": visibility,
                "wind_speed": wind_speed,
                "wind_direction": wind_deg,
                "wind_gust": current.get("wind_gusts_10m"),
                "pressure": pressure,
                "weather_code": wmo_code,
            },
            "metadata": {
                "provider": "Open-Meteo",
                "source_api": "open_meteo",
                "weather_code": wmo_code,
                "condition": condition_label,
            },
            "pipeline": {
                "stage": "RAW",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def publish_live_events(self, batch_size: int = 50) -> Dict[str, Any]:
        """Fetch current live events for all configured Indian locations and publish to Kafka `weather.raw`."""
        all_locations = get_all_locations()
        published_count = 0
        failed_count = 0

        for i in range(0, len(all_locations), batch_size):
            batch = all_locations[i : i + batch_size]
            events = await self.fetch_current_batch(batch)

            for event in events:
                success = kafka_service.publish_raw_event(event)
                if success:
                    published_count += 1
                else:
                    failed_count += 1

        return {
            "total_locations": len(all_locations),
            "published": published_count,
            "failed": failed_count,
        }

    async def fetch_historical_archive(
        self,
        city: str,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical hourly weather data for a city using Open-Meteo Historical Weather API.
        URL: https://archive-api.open-meteo.com/v1/archive
        """
        loc = get_location_by_city(city)
        if not loc:
            logger.error(f"[OPEN_METEO_BACKFILL] Location '{city}' not found in registry.")
            return []

        params = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m",
            "timezone": "Asia/Kolkata",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=30.0)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"[OPEN_METEO_BACKFILL] Archive API request failed for {city}: {e}")
            return []

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        hums = hourly.get("relative_humidity_2m", [])
        precips = hourly.get("precipitation", [])
        codes = hourly.get("weather_code", [])
        winds = hourly.get("wind_speed_10m", [])

        normalized_events = []
        for idx, t in enumerate(times):
            wmo_code = int(codes[idx]) if idx < len(codes) and codes[idx] is not None else 0
            temp = float(temps[idx]) if idx < len(temps) and temps[idx] is not None else 20.0
            precip = float(precips[idx]) if idx < len(precips) and precips[idx] is not None else 0.0

            label, event_type, severity = self.parse_wmo_code(wmo_code, temp=temp, precipitation=precip)
            event_id = generate_deterministic_event_id(loc["city"], t)

            normalized_events.append({
                "event_id": event_id,
                "source": self.source_id,
                "source_metadata": get_source_metadata(self.source_id, collector="open_meteo_backfill"),
                "source_type": "open_meteo",
                "timestamp": t,
                "reported_at": t,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "title": f"[Historical Archive] {label} in {loc['city']}",
                "description": f"Historical hourly weather archive for {loc['city']}: {label}, Temp: {temp}°C, Precip: {precip}mm",
                "event_type": event_type,
                "severity": severity,
                "location": loc,
                "city": loc["city"],
                "state": loc.get("state", ""),
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "weather": {
                    "temperature": temp,
                    "humidity": hums[idx] if idx < len(hums) else None,
                    "precipitation": precip,
                    "wind_speed": winds[idx] if idx < len(winds) else None,
                    "weather_code": wmo_code,
                },
                "metadata": {
                    "provider": "Open-Meteo Archive",
                    "is_historical_backfill": True,
                },
                "pipeline": {
                    "stage": "RAW",
                    "backfilled_at": datetime.now(timezone.utc).isoformat(),
                },
            })

        logger.info(
            f"[OPEN_METEO_BACKFILL] Extracted {len(normalized_events)} hourly archive records for {city} ({start_date} to {end_date})"
        )
        return normalized_events

    async def fetch_and_publish_live(self, locations: Optional[List[Dict[str, Any]]] = None) -> tuple:
        """Fetch live weather for given or all locations and publish events to Kafka weather.raw."""
        if locations is None:
            locations = get_all_locations()
        events = await self.fetch_current_batch(locations)
        results = {}
        for ev in events:
            ev_id = ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            results[ev_id] = success
        return events, results

    async def fetch_and_publish_historical(
        self,
        locations: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        batch_size: int = 10,
    ) -> tuple:
        """Fetch historical archive events for multiple locations and publish to Kafka weather.raw."""
        all_events = []
        results = {}
        for loc in locations:
            city_name = loc["city"]
            events = await self.fetch_historical_archive(city_name, start_date, end_date)
            all_events.extend(events)
            for ev in events:
                ev_id = ev.get("event_id")
                success = kafka_service.publish_raw_event(ev)
                results[ev_id] = success
        return all_events, results


open_meteo_collector = OpenMeteoCollector()
