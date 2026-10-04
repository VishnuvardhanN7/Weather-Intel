import logging
from typing import Optional, List, Dict
from datetime import datetime

from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.services.weather_service import weather_service
from app.services.media_service import read_and_validate_uploads, store_media
from app.models.weather_event import EventSource
from app.utils.geolocation import get_city_coordinates
from app.collectors.twitter_collector import INDIAN_STATES_AND_CITIES

logger = logging.getLogger(__name__)


class CitizenReportHandler:
    def __init__(self):
        self.upload_dir = None
        if settings.UPLOAD_DIR and settings.UPLOAD_DIR.strip():
            from pathlib import Path
            self.upload_dir = Path(settings.UPLOAD_DIR)
            self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def handle_report(
        self,
        db,
        title: str,
        description: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        reported_by_id: Optional[int] = None,
        reported_at: Optional[datetime] = None,
    ) -> dict:
        if city:
            city_lower = city.lower()
            if city_lower in INDIAN_STATES_AND_CITIES:
                resolved_city, resolved_state = INDIAN_STATES_AND_CITIES[city_lower]
                coords = get_city_coordinates(resolved_city)
                city = resolved_city
                state = state or resolved_state
                if not latitude:
                    latitude = coords.get("latitude")
                if not longitude:
                    longitude = coords.get("longitude")

        event = await weather_service.ingest_event(
            db=db,
            title=title,
            description=description,
            source=EventSource.CITIZEN_REPORT,
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude,
            reported_by_id=reported_by_id,
            reported_at=reported_at or datetime.utcnow(),
        )
        return event.to_dict()

    async def handle_report_with_files(
        self,
        db,
        title: str,
        description: str,
        files: List[UploadFile],
        city: Optional[str] = None,
        state: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        reported_by_id: Optional[int] = None,
    ) -> dict:
        # Validate every file before touching the database so a report is only
        # stored when the evidence passes the size/MIME checks.
        entries = await read_and_validate_uploads(files)

        event = await weather_service.ingest_event(
            db=db,
            title=title,
            description=description,
            source=EventSource.CITIZEN_REPORT,
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude,
            reported_by_id=reported_by_id,
        )

        photos: List[str] = []
        videos: List[str] = []
        if entries:
            photos, videos = await store_media(
                db=db,
                entries=entries,
                event_id=event.id,
                uploaded_by_id=reported_by_id,
            )
            event.photos = photos
            event.videos = videos
            await db.commit()
            await db.refresh(event)

        return event.to_dict()

    async def validate_location(self, city: Optional[str], state: Optional[str]) -> Dict:
        result = {"city": city, "state": state, "valid": True, "suggestions": []}

        if city:
            city_lower = city.lower()
            if city_lower in INDIAN_STATES_AND_CITIES:
                resolved_city, resolved_state = INDIAN_STATES_AND_CITIES[city_lower]
                coords = get_city_coordinates(resolved_city)
                result["city"] = resolved_city
                result["state"] = state or resolved_state
                result["latitude"] = coords.get("latitude")
                result["longitude"] = coords.get("longitude")
            else:
                result["valid"] = False
                suggestions = [
                    INDIAN_STATES_AND_CITIES[k]
                    for k in INDIAN_STATES_AND_CITIES
                    if city_lower in k or k in city_lower
                ][:5]
                result["suggestions"] = [{"city": s[0], "state": s[1]} for s in suggestions]

        return result

    def _mock_citizen_reports(self) -> List[dict]:
        import random
        reports = []
        mock_reports = [
            {
                "title": "Waterlogging near my house due to heavy rain",
                "description": "Heavy rain since morning has caused severe waterlogging in our area. Water level is about 2 feet on the main road. Several cars are stuck.",
            },
            {
                "title": "Tree fallen on road blocking traffic",
                "description": "Strong winds brought down a large tree on MG Road near the traffic signal. Both lanes are blocked. Emergency services notified.",
            },
            {
                "title": "Roof of my building damaged by storm",
                "description": "Last night's thunderstorm damaged the roof of our 3-story building. Rainwater entering apartments. Need immediate repair assistance.",
            },
            {
                "title": "Heatwave conditions - very hot day",
                "description": "It feels extremely hot today. I measured 47°C outside. Many people in our locality are suffering from heat-related issues. Request authorities to provide water and shade.",
            },
            {
                "title": "Flood water entering homes in colony",
                "description": "River overflow has caused flooding in our residential colony. About 50 houses are affected. Families have been evacuated to the nearby school.",
            },
            {
                "title": "Dust storm reducing visibility",
                "description": "Massive dust storm has engulfed the city. Visibility is very poor. Vehicles are moving with headlights on. Many trees and signboards damaged.",
            },
            {
                "title": "Heavy rainfall in our village, crops damaged",
                "description": "Unprecedented heavy rainfall has damaged standing crops in about 200 hectares. Farmers are in distress. Need government assistance.",
            },
            {
                "title": "Cyclone warning - securing our area",
                "description": " IMD has issued a cyclone warning for our coastal area. We are evacuating to higher ground. Wind speeds are already picking up.",
            },
        ]

        cities = list(INDIAN_STATES_AND_CITIES.keys())
        for _ in range(10):
            city_key = random.choice(cities)
            city, state = INDIAN_STATES_AND_CITIES[city_key]
            report = random.choice(mock_reports)
            coords = get_city_coordinates(city)
            reports.append({
                "title": report["title"],
                "description": report["description"],
                "city": city,
                "state": state,
                "latitude": coords.get("latitude"),
                "longitude": coords.get("longitude"),
                "metadata": {"citizen_report": True, "verified_citizen": random.choice([True, False])},
                "reported_at": datetime.utcnow().isoformat(),
            })
        return reports

    async def store_citizen_reports(self, db, reports: List[dict]):
        stored_count = 0
        for report in reports:
            try:
                await weather_service.ingest_event(
                    db=db,
                    title=report["title"],
                    description=report["description"],
                    source=EventSource.CITIZEN_REPORT,
                    city=report.get("city"),
                    state=report.get("state"),
                    latitude=report.get("latitude"),
                    longitude=report.get("longitude"),
                    metadata=report.get("metadata", {}),
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing citizen report: {e}")
        logger.info(f"Stored {stored_count} citizen reports")
        return stored_count


citizen_report_handler = CitizenReportHandler()
