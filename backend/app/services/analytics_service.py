from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy import select, func, extract, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weather_event import WeatherEvent, EventType, SeverityLevel, VerificationStatus


class AnalyticsService:
    async def get_event_trends(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day",
    ) -> List[dict]:
        query = select(
            WeatherEvent.reported_at,
            WeatherEvent.event_type,
            WeatherEvent.severity,
        )
        if start_date:
            query = query.where(WeatherEvent.reported_at >= start_date)
        if end_date:
            query = query.where(WeatherEvent.reported_at <= end_date)
        query = query.order_by(WeatherEvent.reported_at)
        result = await db.execute(query)
        rows = result.all()

        if granularity == "day":
            buckets: Dict[str, dict] = {}
            for r in rows:
                key = r.reported_at.strftime("%Y-%m-%d")
                if key not in buckets:
                    buckets[key] = {"date": key, "total": 0, "types": {}}
                buckets[key]["total"] += 1
                etype = r.event_type.value
                buckets[key]["types"][etype] = buckets[key]["types"].get(etype, 0) + 1
            return list(buckets.values())
        elif granularity == "month":
            buckets: Dict[str, dict] = {}
            for r in rows:
                key = r.reported_at.strftime("%Y-%m")
                if key not in buckets:
                    buckets[key] = {"date": key, "total": 0, "types": {}}
                buckets[key]["total"] += 1
                etype = r.event_type.value
                buckets[key]["types"][etype] = buckets[key]["types"].get(etype, 0) + 1
            return list(buckets.values())

        return [{"date": r.reported_at.isoformat(), "event_type": r.event_type.value, "severity": r.severity.value} for r in rows]

    async def get_geographic_heatmap(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[dict]:
        query = select(
            WeatherEvent.city,
            WeatherEvent.state,
            WeatherEvent.latitude,
            WeatherEvent.longitude,
            func.count(WeatherEvent.id).label("event_count"),
            func.avg(
                case(
                    (WeatherEvent.severity == SeverityLevel.CRITICAL, 4),
                    (WeatherEvent.severity == SeverityLevel.HIGH, 3),
                    (WeatherEvent.severity == SeverityLevel.MODERATE, 2),
                    (WeatherEvent.severity == SeverityLevel.LOW, 1),
                    else_=0,
                )
            ).label("avg_severity"),
        ).where(WeatherEvent.latitude.isnot(None))

        if start_date:
            query = query.where(WeatherEvent.reported_at >= start_date)
        if end_date:
            query = query.where(WeatherEvent.reported_at <= end_date)

        query = query.group_by(
            WeatherEvent.city, WeatherEvent.state,
            WeatherEvent.latitude, WeatherEvent.longitude
        )
        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "city": r.city,
                "state": r.state,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "event_count": r.event_count,
                "avg_severity": float(r.avg_severity) if r.avg_severity else 0,
            }
            for r in rows
        ]

    async def get_verification_pipeline(self, db: AsyncSession) -> dict:
        statuses = await db.execute(
            select(WeatherEvent.verification_status, func.count(WeatherEvent.id))
            .group_by(WeatherEvent.verification_status)
        )
        status_counts = {r[0].value: r[1] for r in statuses.all()}

        avg_fake_conf = (await db.execute(
            select(func.avg(WeatherEvent.fake_confidence))
            .where(WeatherEvent.is_fake == True)
        )).scalar() or 0

        avg_category_conf = (await db.execute(
            select(func.avg(WeatherEvent.category_confidence))
        )).scalar() or 0

        return {
            "verification_status_counts": status_counts,
            "avg_fake_confidence": float(avg_fake_conf),
            "avg_category_confidence": float(avg_category_conf),
        }

    async def get_state_summary(self, db: AsyncSession) -> List[dict]:
        result = await db.execute(
            select(
                WeatherEvent.state,
                func.count(WeatherEvent.id).label("total"),
                func.count(case((WeatherEvent.severity == SeverityLevel.CRITICAL, 1))).label("critical"),
                func.count(case((WeatherEvent.severity == SeverityLevel.HIGH, 1))).label("high"),
                func.count(case((WeatherEvent.verification_status == VerificationStatus.VERIFIED, 1))).label("verified"),
            ).where(WeatherEvent.state.isnot(None))
            .group_by(WeatherEvent.state)
            .order_by(func.count(WeatherEvent.id).desc())
        )
        rows = result.all()
        return [
            {
                "state": r.state,
                "total_events": r.total,
                "critical_events": r.critical,
                "high_events": r.high,
                "verified": r.verified,
            }
            for r in rows
        ]


analytics_service = AnalyticsService()