from datetime import datetime
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.weather_event import WeatherEvent, EventType, SeverityLevel, EventSource, VerificationStatus

router = APIRouter()


def format_story_response(event: WeatherEvent) -> Dict[str, Any]:
    """Format a WeatherEvent into a clean Weather Story object."""
    meta = event.metadata_ or {}
    if not isinstance(meta, dict):
        meta = {}

    src = event.source.value if hasattr(event.source, "value") else str(event.source or "web")
    source_display = meta.get("source_name") or src.upper()
    if src == "youtube":
        source_display = "YouTube"
    elif src == "mastodon":
        source_display = "Mastodon"
    elif src == "imd":
        source_display = "IMD Bulletin"
    elif src == "citizen_report":
        source_display = "Citizen Report"

    # Category determination
    cat = meta.get("category")
    if not cat:
        if event.source == EventSource.YOUTUBE:
            cat = "Videos"
        elif event.source == EventSource.IMD:
            cat = "IMD Updates"
        elif event.source == EventSource.CITIZEN_REPORT:
            cat = "Citizen Reports"
        elif event.event_type == EventType.RAINFALL:
            cat = "Rainfall"
        elif event.event_type == EventType.FLOODING:
            cat = "Flooding"
        elif event.event_type in (EventType.THUNDERSTORM, EventType.STRONG_WINDS, EventType.CYCLONE):
            cat = "Storms"
        elif event.event_type == EventType.HEATWAVE:
            cat = "Heatwave"
        elif event.event_type == EventType.FOG:
            cat = "Fog"
        elif event.event_type == EventType.DUST_STORM:
            cat = "Dust Storm"
        elif event.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL):
            cat = "Severe Weather"
        else:
            cat = "Severe Weather"

    loc_str = "India"
    if event.city and event.state:
        loc_str = f"{event.city}, {event.state}"
    elif event.city:
        loc_str = event.city

    img = meta.get("image_url") or event._primary_image_url()
    media_list = event._media_metadata()

    is_demo = bool(meta.get("is_demo", False))
    is_static = bool(meta.get("is_static", False))

    return {
        "id": event.source_id or str(event.id),
        "db_id": event.id,
        "title": event.title,
        "description": event.description,
        "source": source_display,
        "source_url": event.source_url,
        "image_url": img,
        "image_credit": meta.get("image_credit"),
        "image_credit_url": meta.get("image_credit_url"),
        "image_source": meta.get("image_source", "Unsplash"),
        "media": media_list,
        "category": cat,
        "tags": meta.get("tags", []),
        "location": {
            "city": event.city,
            "state": event.state,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "display": loc_str,
        },
        "published_at": event.reported_at.isoformat() if event.reported_at else (event.created_at.isoformat() if event.created_at else None),
        "reported_at": event.reported_at.isoformat() if event.reported_at else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "severity": event.severity.value if hasattr(event.severity, "value") else str(event.severity or "moderate"),
        "verification_status": event.verification_status.value if hasattr(event.verification_status, "value") else str(event.verification_status or "verified"),
        "confidence_score": meta.get("confidence_score", 0.95),
        "is_static": is_static,
        "is_demo": is_demo,
        "is_video": event.source == EventSource.YOUTUBE or cat == "Videos",
    }


def get_source_priority(event: WeatherEvent) -> int:
    """
    Source Priority:
    1. Real Live YouTube Weather Videos (not demo)
    2. Real Live Image Stories (not demo, has valid image_url)
    3. Curated Rich Image & Video Stories (has valid image_url or youtube)
    5. Other Live Events without image_url
    10. Pure fallback events
    """
    meta = event.metadata_ or {}
    if not isinstance(meta, dict):
        meta = {}

    src = str(event.source.value if hasattr(event.source, "value") else event.source or "").lower()
    src_url = str(event.source_url or "").lower()
    is_video = src == "youtube" or "youtube.com" in src_url or "youtu.be" in src_url or meta.get("category") == "Videos"
    
    img_url = meta.get("image_url") or event._primary_image_url()
    has_image = bool(img_url) and str(img_url).startswith("http")

    is_demo = bool(meta.get("is_demo", False)) or bool(meta.get("is_static", False))

    if is_video and not is_demo:
        return 1
    if has_image and not is_demo:
        return 2
    if has_image or is_video:
        return 3
    return 5


@router.get("", response_model=dict)
async def list_stories(
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_video: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(WeatherEvent)

    # Apply category filter
    if category and category.upper() != "ALL":
        cat_lower = category.lower().strip()
        cat_str = f"%{cat_lower}%"

        if cat_lower in ("videos", "video"):
            query = query.where(
                or_(
                    WeatherEvent.source == EventSource.YOUTUBE,
                    cast(WeatherEvent.metadata_, String).ilike("%video%"),
                )
            )
        elif cat_lower in ("imd updates", "imd"):
            query = query.where(
                or_(
                    WeatherEvent.source == EventSource.IMD,
                    cast(WeatherEvent.metadata_, String).ilike("%imd%"),
                )
            )
        elif cat_lower in ("citizen reports", "citizen report", "citizen"):
            query = query.where(
                or_(
                    WeatherEvent.source == EventSource.CITIZEN_REPORT,
                    cast(WeatherEvent.metadata_, String).ilike("%citizen%"),
                )
            )
        elif cat_lower == "fog":
            query = query.where(
                or_(
                    WeatherEvent.event_type == EventType.FOG,
                    cast(WeatherEvent.metadata_, String).ilike("%fog%"),
                )
            )
        elif cat_lower in ("dust storm", "duststorm"):
            query = query.where(
                or_(
                    WeatherEvent.event_type == EventType.DUST_STORM,
                    cast(WeatherEvent.metadata_, String).ilike("%dust%"),
                )
            )
        elif cat_lower in ("storm", "storms"):
            query = query.where(
                or_(
                    WeatherEvent.event_type.in_([EventType.THUNDERSTORM, EventType.STRONG_WINDS, EventType.CYCLONE]),
                    cast(WeatherEvent.metadata_, String).ilike("%storm%"),
                )
            )
        elif cat_lower == "severe weather":
            query = query.where(
                or_(
                    WeatherEvent.severity.in_([SeverityLevel.HIGH, SeverityLevel.CRITICAL]),
                    cast(WeatherEvent.metadata_, String).ilike("%severe%"),
                )
            )
        elif cat_lower == "rainfall":
            query = query.where(
                or_(
                    WeatherEvent.event_type == EventType.RAINFALL,
                    cast(WeatherEvent.metadata_, String).ilike("%rainfall%"),
                )
            )
        elif cat_lower == "flooding":
            query = query.where(
                or_(
                    WeatherEvent.event_type == EventType.FLOODING,
                    cast(WeatherEvent.metadata_, String).ilike("%flooding%"),
                )
            )
        elif cat_lower == "heatwave":
            query = query.where(
                or_(
                    WeatherEvent.event_type == EventType.HEATWAVE,
                    cast(WeatherEvent.metadata_, String).ilike("%heatwave%"),
                )
            )
        else:
            query = query.where(
                or_(
                    cast(WeatherEvent.metadata_, String).ilike(cat_str),
                    cast(WeatherEvent.event_type, String).ilike(cat_str),
                )
            )

    if source:
        src_lower = source.lower()
        if src_lower == "youtube":
            query = query.where(WeatherEvent.source == EventSource.YOUTUBE)
        elif src_lower == "web":
            query = query.where(WeatherEvent.source == EventSource.WEB)
        elif src_lower == "mastodon":
            query = query.where(WeatherEvent.source == EventSource.MASTODON)
        elif src_lower == "imd":
            query = query.where(WeatherEvent.source == EventSource.IMD)
        elif src_lower == "citizen":
            query = query.where(WeatherEvent.source == EventSource.CITIZEN_REPORT)

    if is_video is True:
        query = query.where(WeatherEvent.source == EventSource.YOUTUBE)

    if search:
        s_term = f"%{search}%"
        query = query.where(
            or_(
                WeatherEvent.title.ilike(s_term),
                WeatherEvent.description.ilike(s_term),
                WeatherEvent.city.ilike(s_term),
                WeatherEvent.state.ilike(s_term),
                cast(WeatherEvent.metadata_, String).ilike(s_term),
            )
        )

    result = await db.execute(query)
    events = result.scalars().all()

    # Sort: Live events first (priority 1..6), Demo events second (priority 10), then by reported_at desc
    sorted_events = sorted(
        events,
        key=lambda e: (
            get_source_priority(e),
            - (e.reported_at.timestamp() if e.reported_at else 0)
        )
    )

    formatted_stories = [format_story_response(e) for e in sorted_events]

    live_count = sum(1 for s in formatted_stories if not s["is_demo"])
    demo_count = sum(1 for s in formatted_stories if s["is_demo"])

    total = len(formatted_stories)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_items = formatted_stories[start_idx:end_idx]

    return {
        "data": paginated_items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
            "live_count": live_count,
            "demo_count": demo_count,
        },
    }


@router.get("/{story_id}", response_model=dict)
async def get_story_detail(
    story_id: str,
    db: AsyncSession = Depends(get_db),
):
    event = None
    
    # Try finding by source_id first
    stmt = select(WeatherEvent).where(WeatherEvent.source_id == story_id)
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()

    # If not found by source_id, try numeric primary key ID
    if not event and story_id.isdigit():
        stmt_id = select(WeatherEvent).where(WeatherEvent.id == int(story_id))
        res_id = await db.execute(stmt_id)
        event = res_id.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Weather story not found")

    story_obj = format_story_response(event)

    # Fetch 4 related stories
    rel_stmt = (
        select(WeatherEvent)
        .where(WeatherEvent.id != event.id)
        .order_by(WeatherEvent.reported_at.desc())
        .limit(4)
    )
    rel_res = await db.execute(rel_stmt)
    rel_events = rel_res.scalars().all()
    related = [format_story_response(e) for e in rel_events]

    return {
        "story": story_obj,
        "related_stories": related,
    }
