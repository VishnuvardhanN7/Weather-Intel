from datetime import datetime, timedelta
from typing import Optional, List
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.weather_event import WeatherEvent, EventType, SeverityLevel, EventSource, VerificationStatus
from app.models.user import User
from app.api.auth import get_current_user, get_current_admin
from app.ml.categorizer import Categorizer
from app.ml.fake_detector import FakeDetector
from app.ml.deduplicator import Deduplicator
from app.collectors.citizen_report import citizen_report_handler
from pydantic import BaseModel, Field

router = APIRouter()

WEATHER_CODE_MAP = {
    0: ("Clear Sky", "sun"),
    1: ("Mainly Clear", "sun"),
    2: ("Partly Cloudy", "cloud-sun"),
    3: ("Overcast", "cloud"),
    45: ("Fog", "fog"),
    48: ("Depositing Rime Fog", "fog"),
    51: ("Light Drizzle", "rain"),
    53: ("Moderate Drizzle", "rain"),
    55: ("Dense Drizzle", "rain"),
    61: ("Slight Rain", "rain"),
    63: ("Moderate Rain", "rain"),
    65: ("Heavy Rain", "rain"),
    80: ("Rain Showers", "rain"),
    81: ("Moderate Rain Showers", "rain"),
    82: ("Violent Rain Showers", "rain"),
    95: ("Thunderstorm", "thunderstorm"),
    96: ("Thunderstorm with Hail", "thunderstorm"),
    99: ("Heavy Thunderstorm", "thunderstorm"),
}


@router.get("/forecast", response_model=dict)
async def get_weather_forecast(
    city: str = Query("Delhi"),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
):
    """
    Get 10-day real weather forecast for an Indian city using Open-Meteo weather provider.
    """
    from app.utils.geolocation import get_city_coordinates
    from app.collectors.api_collector import INDIAN_CITIES_COORDS

    lat = latitude
    lon = longitude

    if lat is None or lon is None:
        c_coords = INDIAN_CITIES_COORDS.get(city) or get_city_coordinates(city)
        lat = c_coords.get("latitude", 28.6139)
        lon = c_coords.get("longitude", 77.2090)

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&timezone=Asia%2FKolkata&forecast_days=10"
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            daily = data.get("daily", {})
            times = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            codes = daily.get("weather_code", [])
            precip = daily.get("precipitation_probability_max", [])

            forecasts = []
            for i in range(len(times)):
                dt_str = times[i]
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d")
                    day_str = dt.strftime("%a").upper()
                    day_full = dt.strftime("%a, %b %d")
                except Exception:
                    day_str = "DAY"
                    day_full = dt_str

                code = codes[i] if i < len(codes) else 0
                cond, icon = WEATHER_CODE_MAP.get(code, ("Partly Cloudy", "cloud-sun"))
                t_max = round(max_temps[i]) if i < len(max_temps) and max_temps[i] is not None else 30
                t_min = round(min_temps[i]) if i < len(min_temps) and min_temps[i] is not None else 22
                p_prob = precip[i] if i < len(precip) and precip[i] is not None else 0

                forecasts.append({
                    "date": dt_str,
                    "day": day_str,
                    "day_full": day_full,
                    "condition": cond,
                    "temp_max": t_max,
                    "temp_min": t_min,
                    "precipitation_probability": p_prob,
                    "weather_code": code,
                    "icon": icon,
                })

            return {
                "city": city,
                "latitude": lat,
                "longitude": lon,
                "forecast": forecasts,
            }
    except Exception as e:
        base_dt = datetime.utcnow()
        forecasts = []
        for i in range(10):
            dt = base_dt + timedelta(days=i)
            forecasts.append({
                "date": dt.strftime("%Y-%m-%d"),
                "day": dt.strftime("%a").upper(),
                "day_full": dt.strftime("%a, %b %d"),
                "condition": "Partly Cloudy",
                "temp_max": 32 - (i % 3),
                "temp_min": 24 - (i % 2),
                "precipitation_probability": 10 * (i % 4),
                "weather_code": 2,
                "icon": "cloud-sun",
            })
        return {
            "city": city,
            "latitude": lat,
            "longitude": lon,
            "forecast": forecasts,
            "error": str(e),
        }



class EventCreate(BaseModel):
    title: str
    description: str
    event_type: EventType
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photos: List[str] = []
    videos: List[str] = []
    metadata: dict = {}


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    severity: Optional[SeverityLevel] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    metadata: Optional[dict] = None
    verification_status: Optional[VerificationStatus] = None
    verified_by_id: Optional[int] = None


class VerifyRequest(BaseModel):
    verification_status: VerificationStatus


class EventResponse(BaseModel):
    id: int
    title: str
    description: str
    event_type: str
    severity: str
    source: str
    source_url: str
    source_id: str
    city: str
    state: str
    latitude: float
    longitude: float
    photos: List[str]
    videos: List[str]
    metadata: dict
    verification_status: str
    is_fake: bool
    fake_confidence: float
    category_confidence: float
    duplicate_of_id: Optional[int]
    reported_by_id: Optional[int]
    verified_by_id: Optional[int]
    created_at: str
    updated_at: str
    reported_at: str


@router.post("/citizen-report", response_model=dict, status_code=status.HTTP_201_CREATED)
async def submit_citizen_report(
    title: str = Form(..., min_length=5, max_length=500),
    description: str = Form(..., min_length=10),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a citizen observation, optionally with image/video evidence."""
    return await citizen_report_handler.handle_report_with_files(
        db=db,
        title=title,
        description=description,
        files=files,
        city=city,
        state=state,
        latitude=latitude,
        longitude=longitude,
        reported_by_id=current_user.id,
    )


@router.get("", response_model=dict)
async def list_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    event_type: Optional[EventType] = None,
    severity: Optional[SeverityLevel] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    verification_status: Optional[VerificationStatus] = None,
    source: Optional[EventSource] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    is_fake: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WeatherEvent).options(
        selectinload(WeatherEvent.reported_by),
        selectinload(WeatherEvent.verified_by),
    )

    if event_type:
        query = query.where(WeatherEvent.event_type == event_type)
    if severity:
        query = query.where(WeatherEvent.severity == severity)
    if state:
        query = query.where(WeatherEvent.state.ilike(f"%{state}%"))
    if city:
        query = query.where(WeatherEvent.city.ilike(f"%{city}%"))
    if verification_status:
        query = query.where(WeatherEvent.verification_status == verification_status)
    if source:
        query = query.where(WeatherEvent.source == source)
    if start_date:
        query = query.where(WeatherEvent.reported_at >= start_date)
    if end_date:
        query = query.where(WeatherEvent.reported_at <= end_date)
    if is_fake is not None:
        query = query.where(WeatherEvent.is_fake == is_fake)
    if search:
        query = query.where(
            or_(
                WeatherEvent.title.ilike(f"%{search}%"),
                WeatherEvent.description.ilike(f"%{search}%"),
                WeatherEvent.city.ilike(f"%{search}%"),
                WeatherEvent.state.ilike(f"%{search}%"),
            )
        )

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    total = total or 0

    query = query.order_by(WeatherEvent.reported_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "data": [
            e.to_dict(
                reported_by_name=(
                    (e.reported_by.full_name or e.reported_by.username)
                    if e.reported_by
                    else None
                ),
                verified_by_name=(
                    (e.verified_by.full_name or e.verified_by.username)
                    if e.verified_by
                    else None
                ),
            )
            for e in events
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_event = WeatherEvent(
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        source=EventSource.CITIZEN_REPORT,
        city=event.city,
        state=event.state,
        latitude=event.latitude,
        longitude=event.longitude,
        photos=event.photos,
        videos=event.videos,
        metadata_=event.metadata,
        reported_by_id=current_user.id,
        verification_status=VerificationStatus.PENDING,
    )

    from app.services.processing_service import ingestion_buffer
    await ingestion_buffer.push_to_processing(db, new_event)

    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    return new_event.to_dict(
        reported_by_name=current_user.full_name or current_user.username
    )


@router.get("/stats/general", response_model=dict)
async def event_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    total = (await db.execute(select(func.count()).select_from(WeatherEvent))).scalar() or 0
    verified = (await db.execute(
        select(func.count()).select_from(WeatherEvent).where(WeatherEvent.verification_status == VerificationStatus.VERIFIED))
    ).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(WeatherEvent).where(WeatherEvent.verification_status == VerificationStatus.PENDING))
    ).scalar() or 0
    needs_review = (await db.execute(
        select(func.count()).select_from(WeatherEvent).where(WeatherEvent.verification_status == VerificationStatus.NEEDS_REVIEW))
    ).scalar() or 0
    rejected = (await db.execute(
        select(func.count()).select_from(WeatherEvent).where(WeatherEvent.verification_status == VerificationStatus.REJECTED))
    ).scalar() or 0
    today_events = (await db.execute(
        select(func.count()).select_from(WeatherEvent).where(WeatherEvent.reported_at >= today_start))
    ).scalar() or 0
    detected_fake = (await db.execute(
        select(func.count()).select_from(WeatherEvent).where(WeatherEvent.is_fake == True))
    ).scalar() or 0

    verification_rate = (verified / total * 100) if total else 0

    return {
        "total_events": total,
        "today_events": today_events,
        "pending_review": pending,
        "needs_review": needs_review,
        "verified_events": verified,
        "rejected_events": rejected,
        "detected_fake": detected_fake,
        "verification_rate": verification_rate,
    }


@router.get("/{event_id}", response_model=dict)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WeatherEvent)
        .options(
            selectinload(WeatherEvent.reported_by),
            selectinload(WeatherEvent.verified_by),
        )
        .where(WeatherEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Weather event not found")
    return event.to_dict(
        reported_by_name=(
            (event.reported_by.full_name or event.reported_by.username)
            if event.reported_by
            else None
        ),
        verified_by_name=(
            (event.verified_by.full_name or event.verified_by.username)
            if event.verified_by
            else None
        ),
    )


@router.put("/{event_id}", response_model=dict)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WeatherEvent).where(WeatherEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Weather event not found")

    update_data = event_data.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")

    for field, value in update_data.items():
        setattr(event, field, value)

    if not update_data.get("verified_by_id"):
        event.verified_by_id = current_user.id

    await db.commit()
    await db.refresh(event)
    return event.to_dict()


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WeatherEvent).where(WeatherEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Weather event not found")
    await db.delete(event)
    await db.commit()
    return None


@router.post("/{event_id}/verify", response_model=dict)
async def verify_event(
    event_id: int,
    verify_req: VerifyRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WeatherEvent).where(WeatherEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Weather event not found")

    event.verification_status = verify_req.verification_status
async def _apply_verification_pipeline(event, new_status: VerificationStatus, db: AsyncSession):
    from sqlalchemy.orm.attributes import flag_modified
    event.verification_status = new_status
    metadata = getattr(event, 'metadata_', None) or {}
    if isinstance(metadata, str):
        try:
            import json
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}

    from app.services.rag_service import evaluate_jev, purify_weather_data, index_approved_event_embedding
    if new_status == VerificationStatus.REJECTED:
        event.is_fake = True
        event.fake_confidence = 1.0
        metadata['pipeline_status'] = "admin_rejected"
        setattr(event, 'metadata_', metadata)
        try:
            flag_modified(event, 'metadata_')
        except Exception:
            pass
    elif new_status == VerificationStatus.VERIFIED:
        from app.core.config import settings
        jev_info = await evaluate_jev(event, db=db)
        if jev_info.get("probability", 0.0) >= settings.JEV_THRESHOLD:
            await purify_weather_data(event)
            await index_approved_event_embedding(db, event)
        curr_meta = getattr(event, 'metadata_', None) or {}
        if isinstance(curr_meta, dict):
            curr_meta['pipeline_status'] = "rag_indexed"
            setattr(event, 'metadata_', curr_meta)
            try:
                flag_modified(event, 'metadata_')
            except Exception:
                pass

        if settings.KAFKA_ENABLED:
            try:
                from app.services.kafka_service import kafka_service
                kafka_service.publish_verified_event({
                    "event_id": f"weather_{getattr(event, 'id', 'new')}",
                    "verification_status": "VERIFIED",
                    "jev_score": jev_info.get("probability", 1.0) if 'jev_info' in locals() else 1.0,
                    "is_fake": bool(getattr(event, "is_fake", False)),
                    "is_duplicate": bool(getattr(event, "duplicate_of_id", None)),
                    "category": str(getattr(event, "event_type", "other")),
                    "location": {
                        "latitude": getattr(event, "latitude", None),
                        "longitude": getattr(event, "longitude", None),
                        "city": getattr(event, "city", None),
                        "state": getattr(event, "state", None),
                    },
                    "clean_text": f"{getattr(event, 'title', '')} - {getattr(event, 'description', '')}".strip(),
                    "approved_by": str(getattr(event, "verified_by_id", "admin")),
                    "approved_at": datetime.utcnow().isoformat(),
                    "processing_status": "VERIFIED",
                })
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("Failed to publish verified event to Kafka: %s", exc)


@router.post("/{event_id}/verify", response_model=dict)
async def verify_event(
    event_id: int,
    verify_req: VerifyRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WeatherEvent).where(WeatherEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Weather event not found")

    event.verified_by_id = current_user.id
    await _apply_verification_pipeline(event, verify_req.verification_status, db)

    await db.commit()
    await db.refresh(event)

    from app.services.notification_service import notify_user
    if event.reported_by_id and event.reported_by_id != current_user.id:
        await notify_user(
            db=db,
            user_id=event.reported_by_id,
            notification_type="verification",
            title="Your weather report has been reviewed",
            message=(
                f"Your report \u201c{event.title}\u201d was marked "
                f"'{verify_req.verification_status.value}' "
                f"by an administrator."
            ),
            event_id=event.id,
        )

    return event.to_dict()
