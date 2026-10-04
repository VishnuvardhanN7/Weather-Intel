"""
Stale Event / Incident Detection — determines lifecycle state.

Lifecycle: NEW → ACTIVE → VERIFIED → RESOLVED → STALE → REJECTED

Rules:
  - REJECTED: verification_status == rejected
  - VERIFIED: verification_status == verified
  - NEW: within first 30 minutes
  - ACTIVE: verified or recent (< 6h), or high severity
  - RESOLVED: verified + oldest report > 24h
  - STALE: last update > 12h and not verified, or > 5 days regardless
  
Only time-based. Never auto-resolve critical events.
"""

from typing import Optional
from datetime import datetime, timedelta

STALE_VERSION = "stale-detection-v1"

NEW_WINDOW_MINUTES = 30
ACTIVE_WINDOW_HOURS = 6
STALE_UNVERIFIED_HOURS = 12
RESOLVED_HOURS = 24
ABSOLUTE_STALE_DAYS = 5


def determine_lifecycle(
    verification_status: str,
    reported_at: Optional[datetime],
    updated_at: Optional[datetime] = None,
    severity: str = "LOW",
) -> dict:
    now = datetime.utcnow()

    if verification_status == "rejected":
        return {"lifecycle": "REJECTED", "reason": "Event rejected"}

    if verification_status == "verified":
        if reported_at and (now - reported_at).total_seconds() / 3600 > RESOLVED_HOURS:
            return {
                "lifecycle": "RESOLVED",
                "reason": f"Verified over {RESOLVED_HOURS}h ago",
            }
        return {"lifecycle": "VERIFIED", "reason": "Verified event"}

    if not reported_at:
        return {
            "lifecycle": "UNVERIFIED",
            "reason": "Insufficient timestamp data",
        }

    age_hours = (now - reported_at).total_seconds() / 3600
    last_hours = age_hours
    if updated_at:
        last_hours = (now - updated_at).total_seconds() / 3600

    if age_hours > ABSOLUTE_STALE_DAYS * 24:
        return {
            "lifecycle": "STALE",
            "reason": f"Older than {ABSOLUTE_STALE_DAYS} days",
        }

    if last_hours > STALE_UNVERIFIED_HOURS:
        return {
            "lifecycle": "STALE",
            "reason": f"No update in {STALE_UNVERIFIED_HOURS}h without verification",
        }

    if age_hours <= NEW_WINDOW_MINUTES / 60:
        return {
            "lifecycle": "NEW",
            "reason": f"Reported within last {NEW_WINDOW_MINUTES} minutes",
        }

    if severity in ("HIGH", "CRITICAL"):
        return {
            "lifecycle": "ACTIVE",
            "reason": "High severity — actively monitored",
        }

    if verification_status == "pending" and age_hours <= ACTIVE_WINDOW_HOURS:
        return {
            "lifecycle": "ACTIVE",
            "reason": f"Within active window ({ACTIVE_WINDOW_HOURS}h)",
        }

    if verification_status == "needs_review":
        return {
            "lifecycle": "ACTIVE" if age_hours < 24 else "STALE",
            "reason": "Needs review",
        }

    return {
        "lifecycle": "UNVERIFIED",
        "reason": "No verification or recent activity",
    }