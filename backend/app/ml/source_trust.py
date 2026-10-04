"""
Source Trust Service — tracks and computes reliability scores for data sources.

Every source has:
  source_type: social/web/api/citizen_report
  source_name: specific identifier (e.g., "twitter:@imd_sh", "ndtv")
  trust_score: 0-100
  total_reports: count of reports from this source
  confirmed_reports: count confirmed
  incorrect_reports: count incorrect/rejected
  last_seen: most recent report timestamp
  reliability_reason: human-readable explanation
  has_sufficient_data: whether sample size is large enough for stats

Trust scoring derivation:
  Base trust by source type (official API=90, news=75, social=55, citizen=50, unknown=30)
  + adjustment from known credible sources
  + historical confirmation rate adjustment (only if >= 10 samples)
"""

from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from datetime import datetime

SOURCE_TRUST_VERSION = "source-trust-v1"

SOURCE_TYPE_DEFAULTS = {
    "api": 90,
    "web": 65,
    "twitter": 55,
    "citizen_report": 50,
    "other": 40,
}

KNOWN_CREDIBLE_SOURCES = {
    "imd": 95, "openweather": 90, "ndma": 95, "ndrf": 92,
    "ndtv": 80, "the_hindu": 78, "india_today": 75,
    "times_of_india": 73, "hindustan_times": 72,
    "weather_channel": 85, "accuweather": 82,
}

MIN_SAMPLES_FOR_STATISTICAL_TRUST = 10


def get_source_info(event) -> Tuple[str, str]:
    """Extract source_type and source_name from an event-like object."""
    src = getattr(event, 'source', '') or ''
    metadata = getattr(event, 'metadata_', None) or {}
    source_url = getattr(event, 'source_url', '') or ''
    source_details = metadata.get('source_details', {}) if isinstance(metadata, dict) else {}

    src_type = str(src).lower()

    if source_url and 'twitter.com' in source_url and 'x.com' in source_url:
        src_type = 'twitter'

    name = src_type
    if src_type == 'twitter':
        handle = source_details.get('handle') or (source_url.split('/')[-2] if 'twitter.com' in source_url else '')
        if handle:
            name = f"twitter:@{handle}"
    elif src_type == 'web':
        if source_url:
            from urllib.parse import urlparse
            netloc = urlparse(source_url).netloc
            name = netloc.replace('www.', '').split('.')[0]
    elif src_type == 'api':
        name = 'openweather' if 'openweather' in source_url.lower() else (source_details.get('provider') or 'weather-api')
    elif src_type == 'citizen_report':
        name = 'citizen-report'

    return src_type, name


def compute_base_trust(source_type: str, source_name: str) -> float:
    """Base trust score from source type + known credible source bumps."""
    name_lower = source_name.lower().strip()
    for credible, score in KNOWN_CREDIBLE_SOURCES.items():
        if credible in name_lower:
            return score
    return SOURCE_TYPE_DEFAULTS.get(source_type, 40)


def compute_trust_score(
    source_type: str,
    source_name: str,
    total_reports: int,
    confirmed_reports: int,
) -> Tuple[float, str, bool]:
    """Compute final trust score with historical adjustment where data permits."""
    base = compute_base_trust(source_type, source_name)
    has_sufficient = total_reports >= MIN_SAMPLES_FOR_STATISTICAL_TRUST
    adjustment = 0.0
    reason = ""

    if has_sufficient and total_reports > 0:
        rate = confirmed_reports / total_reports
        adjustment = (rate - 0.5) * 30
        adjustment = max(-20, min(20, adjustment))
        reason = f"{rate*100:.0f}% historical confirmation across {total_reports} reports"
    else:
        if total_reports > 0:
            reason = f"Insufficient history ({total_reports} reports; need {MIN_SAMPLES_FOR_STATISTICAL_TRUST})"
        else:
            reason = "No historical data yet"

    if source_name and any(k in source_name.lower() for k in KNOWN_CREDIBLE_SOURCES):
        reason = "Known credible source"

    score = max(5, min(100, base + adjustment))
    return score, reason, has_sufficient


async def compute_trust_record(db, source_type: str, source_name: str) -> dict:
    """Compute a trust record for a source based on actual database history."""
    from sqlalchemy import select, func, or_
    from app.models.weather_event import WeatherEvent

    source_filter = WeatherEvent.source == source_type
    if source_name and source_name != source_type:
        source_filter = or_(source_filter, WeatherEvent.metadata_['source_name'].as_string() == source_name)

    total_result = await db.execute(
        select(func.count(WeatherEvent.id)).where(source_filter)
    )
    total = total_result.scalar() or 0

    has_media_filter = or_(
        func.json_array_length(WeatherEvent.photos) > 0,
        func.json_array_length(WeatherEvent.videos) > 0,
    )

    verified_result = await db.execute(
        select(func.count(WeatherEvent.id)).where(
            source_filter,
            WeatherEvent.verification_status == 'verified',
        )
    )
    verified = verified_result.scalar() or 0

    rejected_result = await db.execute(
        select(func.count(WeatherEvent.id)).where(
            source_filter,
            or_(WeatherEvent.verification_status == 'rejected', WeatherEvent.is_fake == True),
        )
    )
    rejected = rejected_result.scalar() or 0

    last_seen_result = await db.execute(
        select(func.max(WeatherEvent.reported_at)).where(source_filter)
    )
    last_seen = last_seen_result.scalar()

    score, reason, has_sufficient = compute_trust_score(
        source_type, source_name, total, verified
    )

    return {
        "source_type": source_type,
        "source_name": source_name,
        "trust_score": round(score, 1),
        "total_reports": total,
        "confirmed_reports": verified,
        "incorrect_reports": rejected,
        "confirmation_rate": round(verified / total * 100, 1) if total > 0 else None,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "reliability_reason": reason,
        "has_sufficient_data": has_sufficient,
        "min_samples_for_statistics": MIN_SAMPLES_FOR_STATISTICAL_TRUST,
        "version": SOURCE_TRUST_VERSION,
    }


async def get_all_source_trusts(db) -> List[dict]:
    """Compute trust records for all sources seen in the database."""
    from sqlalchemy import select, func
    from app.models.weather_event import WeatherEvent

    result = await db.execute(
        select(WeatherEvent.source, func.count(WeatherEvent.id))
        .group_by(WeatherEvent.source)
    )
    rows = result.all()

    records = []
    for source_type, _ in rows:
        record = await compute_trust_record(db, source_type, str(source_type))
        if record["total_reports"] > 0:
            records.append(record)
    records.sort(key=lambda r: r["trust_score"], reverse=True)
    return records