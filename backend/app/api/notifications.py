import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class PreferencesUpdate(BaseModel):
    notification_consent: bool
    notification_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    notification_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)
    notification_radius_km: Optional[float] = Field(None, ge=1.0, le=100.0)


@router.get("/preferences", response_model=dict)
async def get_preferences(current_user: User = Depends(get_current_user)):
    return {
        "notification_consent": current_user.notification_consent,
        "notification_lat": current_user.notification_lat,
        "notification_lng": current_user.notification_lng,
        "notification_radius_km": current_user.notification_radius_km,
    }


@router.put("/preferences", response_model=dict)
async def update_preferences(
    prefs: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if prefs.notification_consent:
        if prefs.notification_lat is None or prefs.notification_lng is None:
            raise HTTPException(
                status_code=400,
                detail="Location is required to enable weather alert notifications.",
            )
    current_user.notification_consent = prefs.notification_consent
    if prefs.notification_lat is not None:
        current_user.notification_lat = prefs.notification_lat
    if prefs.notification_lng is not None:
        current_user.notification_lng = prefs.notification_lng
    if prefs.notification_radius_km is not None:
        current_user.notification_radius_km = prefs.notification_radius_km
    await db.commit()
    await db.refresh(current_user)
    return current_user.to_dict()


@router.get("/unread-count", response_model=dict)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = (
        await db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == current_user.id,
                Notification.is_read == False,  # noqa: E712
            )
        )
    ).scalar() or 0
    return {"unread_count": count}


@router.get("", response_model=dict)
async def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read == False)  # noqa: E712
    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar() or 0
    query = (
        query
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    return {
        "data": [n.to_dict() for n in result.scalars().all()],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    }


@router.post("/{notification_id}/read", response_model=dict)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    await db.commit()
    return {"status": "ok"}


@router.post("/read-all", response_model=dict)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}