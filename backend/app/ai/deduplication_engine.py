"""
AI Engine 3: Deduplication Service.

Wraps existing backend/app/ml/deduplicator.py behind BaseDeduplicationEngine interface.
Identifies exact duplicates, near duplicates, and repeated reports referring to the same event.
"""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.deduplicator import deduplicator

logger = logging.getLogger(__name__)


class BaseDeduplicationEngine:
    """Base interface for Deduplication AI Engine."""

    async def check_duplicate(self, db: AsyncSession, event: Any) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement check_duplicate()")

    def check_duplicate_dict(self, event_data: Dict[str, Any], existing_events: Optional[list] = None) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement check_duplicate_dict()")


class DeduplicationEngine(BaseDeduplicationEngine):
    """
    Deduplication Engine wrapping existing ML deduplicator implementation.
    """

    def __init__(self, dedup_impl=None):
        self.deduplicator = dedup_impl or deduplicator

    async def check_duplicate(self, db: AsyncSession, event: Any) -> Dict[str, Any]:
        """Check database for existing duplicate of event."""
        try:
            duplicate = await self.deduplicator.find_duplicate(db, event)
            if duplicate:
                dup_id = getattr(duplicate, "id", None)
                return {
                    "is_duplicate": True,
                    "duplicate_of_id": dup_id,
                    "match_type": "database_near_duplicate",
                    "confidence": 0.90,
                }
            return {
                "is_duplicate": False,
                "duplicate_of_id": None,
                "match_type": "none",
                "confidence": 0.0,
            }
        except Exception as exc:
            logger.error("Error running DeduplicationEngine.check_duplicate: %s", exc)
            return {
                "is_duplicate": False,
                "duplicate_of_id": None,
                "match_type": "error_fallback",
                "confidence": 0.0,
            }

    def check_duplicate_dict(self, event_data: Dict[str, Any], existing_events: Optional[list] = None) -> Dict[str, Any]:
        """In-memory dictionary duplicate check helper for stream processing."""
        if not existing_events:
            return {"is_duplicate": False, "duplicate_of_id": None, "match_type": "none"}

        text = str(event_data.get("text") or event_data.get("title") or "").strip().lower()
        event_city = str(event_data.get("location", {}).get("city") or "").strip().lower()

        for item in existing_events:
            item_text = str(item.get("text") or item.get("title") or "").strip().lower()
            item_city = str(item.get("location", {}).get("city") or "").strip().lower()

            if text and text == item_text:
                return {
                    "is_duplicate": True,
                    "duplicate_of_id": item.get("event_id"),
                    "match_type": "exact_text_match",
                }

            if text and item_text and event_city and event_city == item_city and (text in item_text or item_text in text):
                return {
                    "is_duplicate": True,
                    "duplicate_of_id": item.get("event_id"),
                    "match_type": "near_text_city_match",
                }

        return {"is_duplicate": False, "duplicate_of_id": None, "match_type": "none"}


# Shared default instance
deduplication_engine = DeduplicationEngine()
