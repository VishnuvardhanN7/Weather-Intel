"""
OpenSearch / Elasticsearch Storage Service for PS-26069.

Provides document indexing and search functionality for sink-approved weather events.
Configured dynamically via settings.OPENSEARCH_ENABLED. Fails gracefully if OpenSearch is unavailable.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenSearchService:
    """Service abstraction for indexing sink-approved events into OpenSearch."""

    def __init__(self):
        self.enabled = settings.OPENSEARCH_ENABLED
        self.url = settings.OPENSEARCH_URL.rstrip("/")
        self.index_name = settings.OPENSEARCH_INDEX

    def index_event(self, event: Dict[str, Any]) -> bool:
        """
        Index a single sink-approved verified event into OpenSearch.
        Uses deterministic doc_id = event_id to prevent duplicate indexing.
        """
        if not settings.OPENSEARCH_ENABLED:
            logger.debug("OpenSearch indexing disabled (OPENSEARCH_ENABLED=False). Skipping event_id '%s'",
                         event.get("event_id"))
            return False

        event_id = event.get("event_id") or event.get("id")
        if not event_id:
            logger.warning("Cannot index event without valid event_id: %s", event)
            return False

        doc_url = f"{self.url}/{self.index_name}/_doc/{event_id}"

        doc_body = {
            "event_id": event_id,
            "source": event.get("source"),
            "timestamp": event.get("timestamp"),
            "clean_text": event.get("clean_text"),
            "category": event.get("category"),
            "category_confidence": event.get("category_confidence", 0.0),
            "severity": event.get("severity"),
            "location": event.get("location", {}),
            "media": event.get("media", []),
            "is_fake": event.get("is_fake", False),
            "is_duplicate": event.get("is_duplicate", False),
            "jev_probability": event.get("jev_probability", 0.0),
            "verification_status": event.get("verification_status", "AI_VERIFIED"),
            "alertness_score": event.get("alertness_score", 0.0),
        }

        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.put(doc_url, json=doc_body)
                if resp.status_code in (200, 201):
                    logger.info("[OPENSEARCH] Successfully indexed document '%s' into index '%s'", event_id, self.index_name)
                    return True
                else:
                    logger.warning("[OPENSEARCH] Indexing returned status %d: %s", resp.status_code, resp.text)
                    return False
        except Exception as exc:
            logger.warning("[OPENSEARCH] Failed to index document '%s' (OpenSearch unavailable): %s", event_id, exc)
            return False

    def search_events(self, query_text: str, size: int = 10) -> List[Dict[str, Any]]:
        """Search indexed weather events in OpenSearch."""
        if not settings.OPENSEARCH_ENABLED:
            return []

        search_url = f"{self.url}/{self.index_name}/_search"
        query_body = {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["clean_text^2", "category", "location.city", "location.state"]
                }
            },
            "size": size
        }

        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(search_url, json=query_body)
                if resp.status_code == 200:
                    hits = resp.json().get("hits", {}).get("hits", [])
                    return [h["_source"] for h in hits]
        except Exception as exc:
            logger.warning("[OPENSEARCH] Search failed (OpenSearch unavailable): %s", exc)
        return []


opensearch_service = OpenSearchService()
