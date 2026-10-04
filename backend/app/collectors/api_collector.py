import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import httpx

from app.core.config import settings
from app.services.weather_service import weather_service
from app.models.weather_event import EventSource
from app.utils.geolocation import get_city_coordinates

logger = logging.getLogger(__name__)

INDIAN_CITIES_COORDS = {
    "Delhi": {"latitude": 28.6139, "longitude": 77.2090},
    "Mumbai": {"latitude": 19.0760, "longitude": 72.8777},
    "Bengaluru": {"latitude": 12.9716, "longitude": 77.5946},
    "Chennai": {"latitude": 13.0827, "longitude": 80.2707},
    "Kolkata": {"latitude": 22.5726, "longitude": 88.3639},
    "Hyderabad": {"latitude": 17.3850, "longitude": 78.4867},
    "Pune": {"latitude": 18.5204, "longitude": 73.8567},
    "Ahmedabad": {"latitude": 23.0225, "longitude": 72.5714},
    "Jaipur": {"latitude": 26.9124, "longitude": 75.7873},
    "Lucknow": {"latitude": 26.8467, "longitude": 80.9462},
    "Bhopal": {"latitude": 23.2599, "longitude": 77.4126},
    "Patna": {"latitude": 25.6093, "longitude": 85.1376},
    "Guwahati": {"latitude": 26.1445, "longitude": 91.7362},
    "Kochi": {"latitude": 9.9312, "longitude": 76.2673},
    "Indore": {"latitude": 22.7196, "longitude": 75.8577},
    "Nagpur": {"latitude": 21.1458, "longitude": 79.0882},
    "Thiruvananthapuram": {"latitude": 8.5241, "longitude": 76.9366},
    "Visakhapatnam": {"latitude": 17.6868, "longitude": 83.2185},
    "Varanasi": {"latitude": 25.3176, "longitude": 82.9739},
    "Amritsar": {"latitude": 31.6340, "longitude": 74.8723},
}

WEATHER_EVENT_SEVERITY_MAP = {
    "Thunderstorm": "high",
    "Rain": "moderate",
    "Heavy Rain": "high",
    "Drizzle": "low",
    "Snow": "moderate",
    "Clear": "low",
    "Clouds": "low",
    "Mist": "low",
    "Fog": "moderate",
    "Haze": "moderate",
    "Dust": "high",
    "Tornado": "critical",
    "Squall": "high",
}


class APICollector:
    def __init__(self):
        self.openweather_key = settings.OPENWEATHER_API_KEY
        self.openweather_base = "https://api.openweathermap.org/data/2.5"
        self.imd_base = "https://api.data.gov.in/resource"

    async def fetch_openweather_current(self, city: str, use_sample_data: bool = False) -> Optional[dict]:
        key = self.openweather_key or settings.OPENWEATHER_API_KEY
        if not key:
            if use_sample_data:
                return self._mock_openweather(city)
            logger.warning(f"OPENWEATHER_API_KEY is not configured for city '{city}'. Skipping mock fallback.")
            return None

        url = f"{self.openweather_base}/weather"
        params = {"q": f"{city},IN", "appid": key, "units": "metric"}
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=30)
                resp.raise_for_status()
                return self._parse_openweather_response(resp.json())
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenWeather API error for {city}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error fetching OpenWeather for {city}: {e}")
                return None

    async def fetch_openweather_forecast(self, city: str, use_sample_data: bool = False) -> Optional[dict]:
        key = self.openweather_key or settings.OPENWEATHER_API_KEY
        if not key:
            if use_sample_data:
                return self._mock_openweather_forecast(city)
            logger.warning(f"OPENWEATHER_API_KEY is not configured for city '{city}'. Skipping forecast.")
            return None

        url = f"{self.openweather_base}/forecast"
        params = {"q": f"{city},IN", "appid": key, "units": "metric", "cnt": 24}
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                return self._parse_forecast_response(data)
            except Exception as e:
                logger.error(f"Error fetching forecast for {city}: {e}")
                return None

    async def fetch_openweather_bulk(self, cities: Optional[List[str]] = None, use_sample_data: bool = False) -> List[dict]:
        target_cities = cities or list(INDIAN_CITIES_COORDS.keys())[:10]
        results = []
        for city in target_cities:
            weather = await self.fetch_openweather_current(city, use_sample_data=use_sample_data)
            if weather:
                results.append(weather)
        return results

    async def publish_raw_weather_event(self, city: str, use_sample_data: bool = False) -> bool:
        """
        Fetch real OpenWeather observation for city and publish directly to Kafka weather.raw topic.
        Does NOT insert into PostgreSQL directly or bypass Spark/AI/JEV streaming pipeline.
        """
        weather = await self.fetch_openweather_current(city, use_sample_data=use_sample_data)
        if not weather:
            return False

        from app.services.kafka_service import kafka_service
        raw_payload = {
            "event_id": f"weather_openweather_{city.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}",
            "source": "api",
            "timestamp": weather.get("reported_at") or datetime.utcnow().isoformat(),
            "text": f"{weather['title']} - {weather['description']}",
            "title": weather["title"],
            "description": weather["description"],
            "location": {
                "latitude": weather.get("latitude"),
                "longitude": weather.get("longitude"),
                "city": weather.get("city") or city,
                "state": weather.get("state") or "",
            },
            "media": [],
            "metadata": weather.get("metadata", {}),
            "processing_status": "RAW",
        }
        return kafka_service.publish_raw_event(raw_payload)

    async def publish_raw_weather_bulk(self, cities: Optional[List[str]] = None, use_sample_data: bool = False) -> Dict[str, bool]:
        """
        Fetch real OpenWeather observations for specified (or default 20 Indian) cities
        and publish each raw observation directly to Kafka weather.raw topic.
        Does NOT insert records into PostgreSQL directly.
        """
        target_cities = cities or list(INDIAN_CITIES_COORDS.keys())
        results = {}
        for city in target_cities:
            success = await self.publish_raw_weather_event(city, use_sample_data=use_sample_data)
            results[city] = success
        return results

    async def fetch_imd_alerts(self) -> List[dict]:
        alerts = []
        imd_alert_cities = [
            "Delhi", "Mumbai", "Chennai", "Kolkata", "Bengaluru",
            "Hyderabad", "Ahmedabad", "Pune", "Jaipur", "Lucknow",
        ]
        for city in imd_alert_cities:
            weather = await self.fetch_openweather_current(city)
            if weather and weather.get("severity", "low") in ("high", "critical"):
                alerts.append(weather)
        return alerts

    def _parse_openweather_response(self, data: dict) -> Optional[dict]:
        try:
            weather_main = data.get("weather", [{}])[0]
            weather_condition = weather_main.get("main", "Unknown")
            description = weather_main.get("description", "")
            main = data.get("main", {})
            wind = data.get("wind", {})
            coord = data.get("coord", {})
            name = data.get("name", "")
            temp = main.get("temp", 0) or 0
            wind_speed = wind.get("speed", 0) or 0
            visibility = data.get("visibility", 10000) or 10000

            desc_lower = description.lower()
            cond_lower = weather_condition.lower()

            # Determine SIH event_type and severity strictly from actual weather data
            event_type = "other"
            severity = "low"

            if cond_lower in ("thunderstorm", "tornado") or "thunderstorm" in desc_lower or "lightning" in desc_lower:
                event_type = "thunderstorm"
                severity = "critical" if (cond_lower == "tornado" or "severe" in desc_lower) else "high"
            elif cond_lower in ("rain", "drizzle", "squall") or "rain" in desc_lower or "drizzle" in desc_lower:
                event_type = "rainfall"
                if "heavy" in desc_lower or "intense" in desc_lower or "extreme" in desc_lower:
                    severity = "high"
                elif "light" in desc_lower or "drizzle" in desc_lower or cond_lower == "drizzle":
                    severity = "low"
                else:
                    severity = "moderate"
            elif "flood" in desc_lower or "inundat" in desc_lower or "waterlog" in desc_lower:
                event_type = "flooding"
                severity = "high"
            elif temp >= 40.0 or "heatwave" in desc_lower or "extreme heat" in desc_lower:
                event_type = "heatwave"
                severity = "high" if temp >= 43.0 else "moderate"
            elif cond_lower in ("dust", "sand") or "dust" in desc_lower or "sandstorm" in desc_lower:
                event_type = "dust_storm"
                severity = "high" if wind_speed >= 15.0 else "moderate"
            elif wind_speed >= 15.0 or cond_lower == "squall" or "gale" in desc_lower or "strong wind" in desc_lower:
                event_type = "strong_winds"
                severity = "high" if wind_speed >= 20.0 else "moderate"
            elif cond_lower == "fog" or (cond_lower in ("mist", "haze") and visibility < 1000):
                event_type = "fog"
                severity = "moderate" if visibility < 500 else "low"
            else:
                # Normal weather observation (clear sky, clouds, mild mist/haze, normal temp/wind)
                event_type = "other"
                severity = "low"

            title = f"{weather_condition}: {description} in {name}, India"
            full_desc = (
                f"Current weather in {name}, India: {weather_condition} ({description}). "
                f"Temperature: {temp}°C, Humidity: {main.get('humidity', 'N/A')}%, "
                f"Wind: {wind_speed} m/s from {wind.get('deg', 'N/A')}°."
            )

            return {
                "title": title,
                "description": full_desc,
                "event_type": event_type,
                "severity": severity,
                "city": name,
                "state": "",
                "latitude": coord.get("lat"),
                "longitude": coord.get("lon"),
                "metadata": {
                    "source_api": "openweathermap",
                    "temperature": temp,
                    "humidity": main.get("humidity"),
                    "wind_speed": wind_speed,
                    "wind_deg": wind.get("deg"),
                    "pressure": main.get("pressure"),
                    "visibility": visibility,
                    "weather_condition": weather_condition,
                    "description": description,
                    "sunrise": data.get("sys", {}).get("sunrise"),
                    "sunset": data.get("sys", {}).get("sunset"),
                },
                "reported_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error parsing OpenWeather response: {e}")
            return None

    def _parse_forecast_response(self, data: dict) -> dict:
        forecasts = []
        for item in data.get("list", [])[:8]:
            weather = item.get("weather", [{}])[0]
            main = item.get("main", {})
            forecasts.append({
                "time": item.get("dt_txt"),
                "condition": weather.get("main"),
                "description": weather.get("description"),
                "temp": main.get("temp"),
                "humidity": main.get("humidity"),
            })
        return {
            "city": data.get("city", {}).get("name", ""),
            "country": data.get("city", {}).get("country", ""),
            "forecasts": forecasts,
        }

    async def store_api_events(self, db, events: List[dict]):
        stored_count = 0
        for event in events:
            try:
                await weather_service.ingest_event(
                    db=db,
                    title=event["title"],
                    description=event["description"],
                    source=EventSource.API,
                    city=event.get("city"),
                    state=event.get("state"),
                    latitude=event.get("latitude"),
                    longitude=event.get("longitude"),
                    metadata=event.get("metadata", {}),
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing API event: {e}")
        logger.info(f"Stored {stored_count} API events in database")
        return stored_count

    def _mock_openweather(self, city: str) -> dict:
        import random
        coords = INDIAN_CITIES_COORDS.get(city, {"latitude": 28.6139, "longitude": 77.2090})
        conditions = [
            ("Thunderstorm", "thunderstorm", "high"),
            ("Rain", "light rain", "moderate"),
            ("Heavy Rain", "heavy intensity rain", "high"),
            ("Clouds", "overcast clouds", "low"),
            ("Clear", "clear sky", "low"),
            ("Mist", "mist", "low"),
            ("Fog", "fog", "moderate"),
            ("Haze", "haze", "moderate"),
            ("Drizzle", "light drizzle", "low"),
        ]
        cond = random.choice(conditions)
        temp = random.uniform(15, 42)
        humidity = random.randint(40, 95)
        wind_speed = random.uniform(1, 25)

        return {
            "title": f"{cond[0]}: {cond[1]} in {city}, India",
            "description": (
                f"Current weather in {city}, India: {cond[0]} ({cond[1]}). "
                f"Temperature: {temp:.1f}°C, Humidity: {humidity}%, "
                f"Wind: {wind_speed:.1f} m/s."
            ),
            "event_type": cond[0].lower(),
            "severity": cond[2],
            "city": city,
            "state": "",
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "metadata": {
                "source_api": "openweathermap_mock",
                "temperature": round(temp, 1),
                "humidity": humidity,
                "wind_speed": round(wind_speed, 1),
                "weather_condition": cond[0],
                "description": cond[1],
            },
            "reported_at": datetime.utcnow().isoformat(),
        }

    def _mock_openweather_forecast(self, city: str) -> dict:
        import random
        forecasts = []
        base_time = datetime.utcnow()
        for i in range(8):
            t = base_time + timedelta(hours=i * 3)
            conditions = ["Clear", "Clouds", "Rain", "Thunderstorm", "Mist"]
            cond = random.choice(conditions)
            forecasts.append({
                "time": t.strftime("%Y-%m-%d %H:%M:%S"),
                "condition": cond,
                "description": cond.lower(),
                "temp": round(random.uniform(18, 38), 1),
                "humidity": random.randint(40, 95),
            })
        return {"city": city, "country": "IN", "forecasts": forecasts}


api_collector = APICollector()