import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User
from app.models.weather_event import WeatherEvent, SeverityLevel
from app.utils.geolocation import haversine_distance, is_within_radius

logger = logging.getLogger(__name__)

ALERT_SEVERITIES = {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
DEFAULT_RADIUS_KM = 25.0


async def notify_user(
    db: AsyncSession,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "system",
    event_id: Optional[int] = None,
    severity: Optional[str] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        event_id=event_id,
        severity=severity,
        is_read=False,
    )
    db.add(notification)
    await db.flush()
    return notification


async def notify_affected_citizens(db: AsyncSession, event: WeatherEvent) -> int:
    """Send location-based alerts to opted-in citizens near a severe event.

    Only ``high``/``critical`` severity events with usable coordinates trigger
    alerts. Citizens must explicitly enable ``notification_consent`` and
    provide a location; the per-user radius (default 25 km) controls reach.
    Ordinary observations (low/moderate) never generate alerts.
    """
    if not event.latitude or not event.longitude:
        return 0
    if event.severity not in ALERT_SEVERITIES:
        return 0

    result = await db.execute(
        select(User).where(
            User.notification_consent == True,  # noqa: E712
            User.notification_lat.isnot(None),
            User.notification_lng.isnot(None),
        )
    )
    recipients = result.scalars().all()

    created = 0
    for user in recipients:
        radius = user.notification_radius_km or DEFAULT_RADIUS_KM
        distance = haversine_distance(
            event.latitude,
            event.longitude,
            user.notification_lat,
            user.notification_lng,
        )
        if is_within_radius(
            event.latitude,
            event.longitude,
            user.notification_lat,
            user.notification_lng,
            radius,
        ):
            await notify_user(
                db=db,
                user_id=user.id,
                notification_type="alert",
                title="Severe weather alert near you",
                message=(
                    f"{event.title} (severity: {event.severity.value}). "
                    f"Reported about {distance:.1f} km from your saved location. "
                    f"Reported at {event.reported_at.isoformat()}."
                ),
                event_id=event.id,
                severity=event.severity.value,
            )
            created += 1

    if created:
        await db.commit()
        logger.info("Created %d location-based alerts for event %s", created, event.id)

    return created