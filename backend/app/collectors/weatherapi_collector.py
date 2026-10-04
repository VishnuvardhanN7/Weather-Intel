"""
WeatherAPI.com Ingestion Collector (PS-26069).

Collects real-time weather observations for Indian cities from WeatherAPI.com API,
normalizes them into common event format, updates source registry state,
and publishes to Kafka `weather.raw`.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.core.location_registry import get_all_locations
from app.models.weather_event import SeverityLevel, EventSource
from app.services.kafka_service import kafka_service
from app.services.source_registry import update_source_status, metrics_tracker

logger = logging.getLogger("weatherapi_collector")


class WeatherAPICollector:
    """Collector for WeatherAPI.com observations."""

    BASE_URL = "http://api.weatherapi.com/v1/current.json"

    def __init__(self):
        self.source_id = "weatherapi"
        self.health_state = "DISABLED"
        self.last_error = None

    def is_enabled(self) -> bool:
        return getattr(settings, "WEATHERAPI_ENABLED", False)

    def validate_config(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "WeatherAPI.com source is disabled in configuration (WEATHERAPI_ENABLED=false)"
        api_key = getattr(settings, "WEATHERAPI_API_KEY", "") or ""
        if not api_key.strip():
            return False, "WeatherAPI.com API key missing (WEATHERAPI_API_KEY)"
        return True, "Configuration valid"

    async def fetch_city_weather(self, client: httpx.AsyncClient, city_info: Dict) -> Optional[Dict]:
        api_key = getattr(settings, "WEATHERAPI_API_KEY", "")
        city_name = city_info["city"]
        state_name = city_info["state"]
        lat = city_info["latitude"]
        lon = city_info["longitude"]

        params = {
            "key": api_key,
            "q": f"{lat},{lon}",
            "aqi": "no"
        }

        try:
            resp = await client.get(self.BASE_URL, params=params, timeout=10.0)
            if resp.status_code == 401 or resp.status_code == 403:
                self.health_state = "AUTH_REQUIRED"
                self.last_error = f"Authentication failure (HTTP {resp.status_code}): Invalid API key"
                update_source_status(self.source_id, "AUTH_REQUIRED", error=self.last_error)
                return None
            elif resp.status_code == 429:
                self.health_state = "DEGRADED"
                self.last_error = "Rate limit exceeded (HTTP 429)"
                update_source_status(self.source_id, "DEGRADED", error=self.last_error)
                return None
            elif resp.status_code != 200:
                logger.warning("[WeatherAPI] Non-200 response for %s: HTTP %d", city_name, resp.status_code)
                return None

            data = resp.json()
            return self.normalize_observation(data, city_name, state_name)
        except Exception as e:
            logger.warning("[WeatherAPI] Request error for %s: %s", city_name, e)
            return None

    def normalize_observation(self, data: Dict, fallback_city: str, fallback_state: str) -> Dict:
        location = data.get("location", {})
        current = data.get("current", {})
        condition = current.get("condition", {})

        city = location.get("name") or fallback_city
        state = location.get("region") or fallback_state
        lat = location.get("lat")
        lon = location.get("lon")

        temp_c = current.get("temp_c")
        humidity = current.get("humidity")
        wind_kph = current.get("wind_kph")
        wind_dir = current.get("wind_dir")
        precip_mm = current.get("precip_mm")
        condition_text = condition.get("text", "Weather Observation")
        epoch = current.get("last_updated_epoch", int(datetime.now(timezone.utc).timestamp()))

        event_id = hashlib.md5(f"weatherapi_{city}_{epoch}".encode("utf-8")).hexdigest()

        title = f"WeatherAPI Observation: {city} ({temp_c}°C, {condition_text})"
        description = (
            f"Current weather in {city}, {state}: {condition_text}. "
            f"Temperature: {temp_c}°C, Humidity: {humidity}%, Wind: {wind_kph} kph ({wind_dir}), Precipitation: {precip_mm}mm."
        )

        # Map condition/wind/precip to severity
        severity = SeverityLevel.LOW.value
        if precip_mm and precip_mm > 50:
            severity = SeverityLevel.CRITICAL.value
        elif precip_mm and precip_mm > 20:
            severity = SeverityLevel.HIGH.value
        elif wind_kph and wind_kph > 60:
            severity = SeverityLevel.HIGH.value

        ts_str = datetime.now(timezone.utc).isoformat()

        return {
            "id": event_id,
            "title": title,
            "description": description,
            "event_type": "weather_observation",
            "severity": severity,
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon,
            "source": EventSource.WEATHERAPI.value,
            "source_type": "weather_api",
            "source_url": "https://www.weatherapi.com/",
            "timestamp": ts_str,
            "reported_at": ts_str,
            "created_at": ts_str,
            "verification_status": "SOURCE_REPORTED",
            "metadata": {
                "temp_c": temp_c,
                "humidity": humidity,
                "wind_kph": wind_kph,
                "wind_dir": wind_dir,
                "precip_mm": precip_mm,
                "condition": condition_text,
                "last_updated_epoch": epoch,
                "provider": "WeatherAPI.com"
            },
            "pipeline": {
                "stage": "RAW",
                "ingested_at": ts_str
            }
        }

    async def fetch_and_publish_all(self) -> Tuple[List[Dict], Dict[str, bool]]:
        valid, msg = self.validate_config()
        if not valid:
            if not self.is_enabled():
                self.health_state = "DISABLED"
                update_source_status(self.source_id, "DISABLED")
            else:
                self.health_state = "AUTH_REQUIRED"
                update_source_status(self.source_id, "AUTH_REQUIRED", error=msg)
            logger.info("[WeatherAPI] %s", msg)
            return [], {}

        locations = get_all_locations()[:10]  # Sample first 10 cities to respect rate limits
        events = []
        publish_results = {}

        async with httpx.AsyncClient() as client:
            for loc in locations:
                event = await self.fetch_city_weather(client, loc)
                if event:
                    events.append(event)

        if self.health_state == "AUTH_REQUIRED":
            return [], {}

        if not events:
            self.health_state = "NO_DATA"
            update_source_status(self.source_id, "NO_DATA")
            return [], {}

        for evt in events:
            ok = kafka_service.publish_raw_event(evt)
            publish_results[evt["id"]] = ok
            if ok:
                metrics_tracker.record_success(self.source_id, 1, 1)
            else:
                metrics_tracker.record_failure(self.source_id, "Kafka publish failed")

        published_count = sum(1 for v in publish_results.values() if v)
        if published_count > 0:
            self.health_state = "HEALTHY"
            update_source_status(self.source_id, "HEALTHY")
        else:
            self.health_state = "DEGRADED"
            update_source_status(self.source_id, "DEGRADED", error="Failed to publish events to Kafka")

        return events, publish_results


weatherapi_collector = WeatherAPICollector()
