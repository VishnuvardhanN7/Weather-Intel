"""
Sink Consumer Service for PS-26069 National Weather Analytics Platform.

Architecture Flow:
Kafka (weather.verified) -> Sink Consumer -> Alertness Score Filter (> 0.90) -> Downstream:
- PostgreSQL + PostGIS (Idempotent spatial/weather storage)
- OpenSearch / Elasticsearch (Full-text index)
- WebSockets (/ws/weather broadcast)
"""

import json
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from app.core.config import settings
from app.services.opensearch_service import opensearch_service
from app.services.websocket_manager import manager as websocket_manager
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)


class SinkConsumer:
    """Intelligent Kafka Sink Consumer enforcing alertness_score > 0.90 gate."""

    def __init__(self):
        self.topic = settings.KAFKA_VERIFIED_TOPIC
        self.alertness_threshold = 0.90

    def process_verified_event(self, event: Dict[str, Any], db_session=None) -> Dict[str, Any]:
        """
        Process a single deserialized verified event from weather.verified synchronously.
        Evaluates alertness_score > 0.90 gate and dispatches downstream.
        """
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                task = loop.create_task(self.process_verified_event_async(event, db_session=db_session))
                return {"event_id": str(event.get("event_id")), "status": "PENDING", "accepted": True}
            else:
                return asyncio.run(self.process_verified_event_async(event, db_session=db_session))
        except Exception as exc:
            logger.error("[SINK] Error in process_verified_event: %s", exc)
            return {"event_id": str(event.get("event_id")), "status": "ERROR", "accepted": False, "reason": str(exc)}


    async def process_verified_event_async(self, event: Dict[str, Any], db_session=None) -> Dict[str, Any]:
        """
        Async implementation of verified event processing.
        Evaluates alertness_score:
          - If <= 0.90 => FILTERED
          - If > 0.90  => ACCEPTED -> PostgreSQL/PostGIS, OpenSearch, WebSockets
        """
        event_id = str(event.get("event_id") or event.get("id") or "unknown_event")
        logger.info("[SINK] Received verified event '%s'", event_id)

        # 1. Safely extract alertness_score
        raw_score = event.get("alertness_score")
        if raw_score is None:
            logger.warning("[SINK] Invalid alertness score for event '%s': missing or None", event_id)
            return {
                "event_id": event_id,
                "alertness_score": None,
                "status": "REJECTED",
                "accepted": False,
                "reason": "missing alertness_score"
            }

        try:
            alertness_score = float(raw_score)
        except (ValueError, TypeError) as exc:
            logger.warning("[SINK] Invalid alertness score for event '%s': %s", event_id, exc)
            return {
                "event_id": event_id,
                "alertness_score": raw_score,
                "status": "REJECTED",
                "accepted": False,
                "reason": f"invalid alertness_score: {raw_score}"
            }

        logger.info("[SINK] Alertness score: %.4f", alertness_score)

        # 2. Strict threshold filter: alertness_score > 0.90 (STRICTLY greater than, NOT >=)
        if alertness_score <= self.alertness_threshold:
            logger.info("[SINK] FILTERED: alertness <= 0.90")
            return {
                "event_id": event_id,
                "alertness_score": alertness_score,
                "status": "FILTERED",
                "accepted": False,
                "reason": "alertness_score <= 0.90"
            }

        logger.info("[SINK] ACCEPTED: alertness > 0.90")

        results = {
            "event_id": event_id,
            "alertness_score": alertness_score,
            "status": "ACCEPTED",
            "accepted": True,
            "postgres_stored": False,
            "opensearch_indexed": False,
            "websocket_broadcast": False
        }

        # 3. Downstream Dispatch A: PostgreSQL / PostGIS
        try:
            db_res = await self._async_store_in_postgres(event, db_session=db_session)
            if isinstance(db_res, dict):
                results["postgres_stored"] = db_res.get("stored", False)
                results["is_new_record"] = db_res.get("is_new", False)
                results["db_action"] = db_res.get("action", "UPDATED")
            else:
                results["postgres_stored"] = bool(db_res)
                results["is_new_record"] = False
                results["db_action"] = "UPDATED"

            if results["postgres_stored"]:
                logger.info("[SINK] PostgreSQL/PostGIS stored event '%s' (Action: %s)", event_id, results["db_action"])
        except Exception as exc:
            logger.error("[SINK] Error storing event in PostgreSQL/PostGIS: %s", exc)

        # 3. Downstream Dispatch B: OpenSearch
        try:
            indexed = opensearch_service.index_event(event)
            results["opensearch_indexed"] = indexed
            if indexed:
                logger.info("[SINK] OpenSearch indexed event '%s'", event_id)
        except Exception as exc:
            logger.error("[SINK] Error indexing event in OpenSearch: %s", exc)

        # 3. Downstream Dispatch C: WebSockets
        try:
            await websocket_manager.broadcast(event)
            results["websocket_broadcast"] = True
            logger.info("[SINK] WebSocket broadcast event '%s'", event_id)
        except Exception as exc:
            logger.error("[SINK] Error broadcasting event to WebSockets: %s", exc)

        return results

    async def _async_store_in_postgres(self, event: Dict[str, Any], db_session=None) -> dict:
        """Async implementation of DB storage using existing async_session_factory or provided AsyncSession."""
        if db_session is not None:
            return await self._async_db_storage(event, db_session)

        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            return await self._async_db_storage(event, session)


    async def _async_db_storage(self, event: Dict[str, Any], async_session) -> dict:
        from app.models.user import User
        from app.models.weather_event import WeatherEvent, VerificationStatus, EventType, SeverityLevel, EventSource
        from sqlalchemy import select


        source_id = str(event.get("event_id") or event.get("id"))
        clean_text = str(event.get("clean_text") or "Verified Weather Event")

        stmt = select(WeatherEvent).where(
            (WeatherEvent.source_id == source_id) | (WeatherEvent.title == clean_text[:500])
        )
        res = await async_session.execute(stmt)
        existing = res.scalar_one_or_none()

        loc = event.get("location") or {}
        cat = str(event.get("category", "other")).lower()
        sev = str(event.get("severity", "moderate")).lower()
        src = str(event.get("source", "api")).lower()

        event_type_val = EventType.RAINFALL if "rain" in cat else (EventType.FLOODING if "flood" in cat else EventType.OTHER)
        severity_val = SeverityLevel.HIGH if "high" in sev else (SeverityLevel.CRITICAL if "crit" in sev else SeverityLevel.MODERATE)
        source_val = EventSource.API if "api" in src else EventSource.CITIZEN_REPORT

        photos = event.get("photos") or ([m["url"] for m in event.get("media", []) if isinstance(m, dict) and m.get("url")] if isinstance(event.get("media"), list) else [])
        videos = event.get("videos") or []
        source_url = event.get("source_url")

        if existing:
            existing.verification_status = VerificationStatus.VERIFIED
            existing.is_fake = False
            existing.priority_score = float(event.get("alertness_score", 0.95)) * 100.0
            existing.verification_score = float(event.get("jev_probability", 0.95)) * 100.0
            if photos and not existing.photos:
                existing.photos = photos
            if videos and not existing.videos:
                existing.videos = videos
            if source_url and not existing.source_url:
                existing.source_url = source_url
            if event.get("media"):
                existing.metadata_ = {**(existing.metadata_ or {}), "media": event.get("media")}
            await async_session.commit()
            return {"stored": True, "is_new": False, "action": "UPDATED"}

        new_event = WeatherEvent(
            title=clean_text[:500],
            description=clean_text,
            event_type=event_type_val,
            severity=severity_val,
            source=source_val,
            source_id=source_id,
            source_url=source_url,
            city=loc.get("city", "Unknown"),
            state=loc.get("state", "Unknown"),
            latitude=loc.get("latitude"),
            longitude=loc.get("longitude"),
            photos=photos,
            videos=videos,
            verification_status=VerificationStatus.VERIFIED,
            is_fake=False,
            fake_confidence=0.0,
            category_confidence=float(event.get("category_confidence", 0.9)),
            verification_score=float(event.get("jev_probability", 0.9)) * 100.0,
            priority_score=float(event.get("alertness_score", 0.95)) * 100.0,
            metadata_={
                "sink_consumed": True,
                "alertness_score": event.get("alertness_score"),
                "jev_probability": event.get("jev_probability"),
                "media": event.get("media", []),
                **(event.get("metadata") or {})
            }
        )
        async_session.add(new_event)
        await async_session.commit()
        return {"stored": True, "is_new": True, "action": "INSERTED"}


    async def consume_loop_async(self, max_records: int = 10, timeout_ms: int = 2000, db_session=None) -> List[Dict[str, Any]]:
        """Async version of consume loop for FastAPI / async pipeline tasks."""
        raw_events = kafka_service.consume_verified_events(max_records=max_records, timeout_ms=timeout_ms)
        results = []
        for evt in raw_events:
            res = await self.process_verified_event_async(evt, db_session=db_session)
            results.append(res)
        return results

    def consume_loop(self, max_records: int = 10, timeout_ms: int = 2000, db_session=None) -> List[Dict[str, Any]]:
        """Consume pending verified events from weather.verified topic and process through Sink Consumer gate."""
        raw_events = kafka_service.consume_verified_events(max_records=max_records, timeout_ms=timeout_ms)
        results = []
        for evt in raw_events:
            res = self.process_verified_event(evt, db_session=db_session)
            results.append(res)
        return results

    def run_worker(
        self,
        max_records_per_poll: int = 10,
        timeout_ms: int = 1000,
        poll_interval: float = 0.5,
        max_batches: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run continuous Sink Consumer background worker process.
        Consumes events from weather.verified topic, enforces alertness_score > 0.90 gate,
        and dispatches accepted events downstream to PostgreSQL, OpenSearch, and WebSockets.
        Handles SIGINT (Ctrl+C) and SIGTERM gracefully.
        """
        import signal
        import time

        if not settings.KAFKA_ENABLED:
            logger.info("[SINK WORKER] KAFKA_ENABLED is False. Worker exiting.")
            return {"processed": 0, "accepted": 0, "filtered": 0, "status": "DISABLED"}

        logger.info("[SINK WORKER] Starting Sink Consumer background worker for topic '%s'...", self.topic)
        self._worker_running = True

        def _handle_shutdown(signum, frame):
            logger.info("[SINK WORKER] Received shutdown signal (%s). Stopping worker...", signum)
            self._worker_running = False

        try:
            signal.signal(signal.SIGINT, _handle_shutdown)
            signal.signal(signal.SIGTERM, _handle_shutdown)
        except (ValueError, AttributeError):
            pass

        processed_count = 0
        accepted_count = 0
        filtered_count = 0
        batch_count = 0

        try:
            while getattr(self, "_worker_running", True):
                if max_batches is not None and batch_count >= max_batches:
                    break

                try:
                    results = self.consume_loop(max_records=max_records_per_poll, timeout_ms=timeout_ms)
                    batch_count += 1
                    if results:
                        for res in results:
                            processed_count += 1
                            status = res.get("status")
                            if status == "ACCEPTED":
                                accepted_count += 1
                                logger.info("[SINK WORKER] Event '%s' ACCEPTED downstream", res.get("event_id"))
                            elif status == "FILTERED":
                                filtered_count += 1
                                logger.info("[SINK WORKER] Event '%s' FILTERED (alertness <= 0.90)", res.get("event_id"))
                    else:
                        time.sleep(poll_interval)
                except Exception as exc:
                    logger.error("[SINK WORKER] Unexpected error during consume loop: %s", exc)
                    time.sleep(1.0)
                    batch_count += 1
        finally:
            logger.info(
                "[SINK WORKER] Worker stopped gracefully. Summary: processed=%d, accepted=%d, filtered=%d",
                processed_count, accepted_count, filtered_count
            )

        return {
            "processed": processed_count,
            "accepted": accepted_count,
            "filtered": filtered_count,
            "status": "STOPPED"
        }


sink_consumer = SinkConsumer()
