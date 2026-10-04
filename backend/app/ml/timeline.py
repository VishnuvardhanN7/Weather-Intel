"""
Timeline Reconstruction — reconstructs the real-time processing history
of an incident for transparency.

Timeline steps:
  09:12 → Report received
  09:16 → Social media detection
  09:21 → Weather API confirmation
  09:27 → Reports clustered
  09:28 → Verification score computed
  09:29 → Marked VERIFIED
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

TIMELINE_VERSION = "timeline-v1"


def _normalize_to_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            return None
    return None


def build_timeline(event: Dict[str, Any], related_reports=None) -> List[dict]:
    """Build a processing timeline for an event."""
    related_reports = related_reports or []
    events = []

    def push(time_value, label, detail, kind):
        dt = _normalize_to_dt(time_value)
        if dt is not None:
            events.append({
                "_dt": dt,
                "time": dt.isoformat(),
                "label": label,
                "detail": detail,
                "kind": kind,
            })

    push(
        event.get('reported_at'),
        "Report received",
        "Raw report ingested from source",
        "ingestion",
    )

    created_at = event.get('created_at')
    reported_at = event.get('reported_at')
    if created_at and created_at != reported_at:
        push(
            created_at,
            "Event created",
            "Processed and stored",
            "ingestion",
        )

    push(
        event.get('category_processed_at') or created_at or reported_at,
        f"Classified as {event['event_type']}",
        f"Classification confidence: {event.get('category_confidence', 0):.0%}"
        if isinstance(event.get('category_confidence', 0), (int, float)) else "Classification confidence: n/a",
        "classification",
    )

    if related_reports:
        latest_similar = max(
            (_normalize_to_dt(r['reported_at']) for r in related_reports if r.get('reported_at')),
            default=_normalize_to_dt(created_at) or _normalize_to_dt(reported_at),
        )
        push(
            latest_similar,
            f"Incident clustered ({len(related_reports)} related reports)",
            "Reports grouped by proximity, time, category, and semantics",
            "clustering",
        )

    verification_scores = [r.get('similarity') for r in related_reports if r.get('similarity')]
    if verification_scores:
        push(
            event.get('verification_processed_at') or created_at or reported_at,
            "Verification computed",
            f"Cross-source corroboration from {len(related_reports)} reports",
            "verification",
        )

    status = event.get('verification_status')
    if status:
        push(
            event.get('verified_at') or event.get('updated_at') or datetime.utcnow().isoformat(),
            f"Marked {str(status).upper().replace('_', ' ')}",
            "Verification criteria evaluated",
            "verification",
        )

    events.sort(key=lambda e: e['_dt'])

    for entry in events:
        entry.pop('_dt', None)

    return events