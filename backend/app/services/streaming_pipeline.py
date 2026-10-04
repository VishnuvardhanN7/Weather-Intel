"""
Streaming Pipeline Orchestrator for PS-26069 National Weather Platform.

Source of Truth Flow:
OpenWeather API -> Kafka (weather.raw)
 -> Spark Stream Processor (AI Engine 1: Org, Engine 2: Fake, Engine 3: Dedup) -> Kafka (weather.clean)
 -> JEV Verification Processor (JEV probability >= 0.60) -> Kafka (weather.verified)
 -> Sink Consumer (alertness_score > 0.90 gate) -> PostgreSQL/PostGIS & WebSockets broadcast
"""

import logging
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.services.kafka_service import kafka_service, format_verified_event
from app.spark.weather_stream_processor import weather_stream_processor
from app.services.sink_consumer import sink_consumer

logger = logging.getLogger(__name__)


class JEVStreamProcessor:
    """Consumes clean events from weather.clean, evaluates JEV (>= 0.60), and publishes to weather.verified."""

    def process_clean_event(self, clean_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate JEV gate (probability >= 0.60) and alertness score for a single clean event.
        If accepted by JEV, publish to weather.verified.
        """
        event_id = clean_event.get("event_id") or "unknown"
        source = str(clean_event.get("source", "api")).lower()
        title = clean_event.get("title") or clean_event.get("clean_text") or ""
        desc = clean_event.get("description") or clean_event.get("raw_text") or ""

        # 1. Fake risk signal
        is_fake = clean_event.get("is_fake", False)
        fake_score = float(clean_event.get("fake_score", 0.0))

        # 2. Derive JEV probability (0.0 - 1.0)
        if "api" in source or source in ("eventsource.api", "api"):
            jev_probability = max(0.95 if not is_fake else 0.85, 1.0 - (fake_score * 0.4))
        else:
            trust_penalty = fake_score * 0.4
            base_ver = 0.75 if not is_fake else 0.40
            jev_probability = max(0.0, min(1.0, base_ver * (1.0 - trust_penalty)))

        jev_probability = round(jev_probability, 3)

        # 3. JEV Gate: probability >= 0.60
        if jev_probability < 0.60:
            logger.info("[JEV STREAM] REJECTED event '%s': JEV probability %.3f < 0.60", event_id, jev_probability)
            return None

        # 4. Compute alertness_score
        severity = str(clean_event.get("severity", "moderate")).lower()
        if severity in ("critical", "high"):
            sev_factor = 1.0
        elif severity == "moderate":
            sev_factor = 0.95
        else:
            sev_factor = 0.70

        computed_alertness = round(jev_probability * sev_factor, 3)

        # 5. Format verified event matching Phase 1 schema
        verified_event = format_verified_event(
            clean_event,
            jev_probability=jev_probability,
            alertness_score=computed_alertness
        )

        # 6. Publish to weather.verified topic
        published = kafka_service.publish_verified_event(verified_event)
        if published:
            logger.info("[JEV STREAM] Published verified event '%s' to topic 'weather.verified' (JEV: %.3f, alertness: %.3f)",
                        event_id, jev_probability, computed_alertness)
            return verified_event
        else:
            logger.warning("[JEV STREAM] Failed to publish verified event '%s' to topic 'weather.verified'", event_id)
            return None

    def process_clean_batch(self, max_records: int = 10, timeout_ms: int = 2000) -> List[Dict[str, Any]]:
        clean_events = kafka_service.consume_clean_events(max_records=max_records, timeout_ms=timeout_ms)
        verified_results = []
        for evt in clean_events:
            res = self.process_clean_event(evt)
            if res:
                verified_results.append(res)
        return verified_results


jev_stream_processor = JEVStreamProcessor()


class PipelineOrchestrator:
    """
    Unified end-to-end streaming pipeline orchestrator.
    Executes raw -> Spark/AI -> clean -> JEV -> verified -> Sink Consumer (>0.90 gate) -> DB/WebSockets.
    """

    def run_pipeline_cycle(self) -> Dict[str, Any]:
        if not settings.KAFKA_ENABLED:
            return {"status": "DISABLED"}

        # Step 1: Spark / AI Processing (weather.raw -> weather.clean)
        clean_events = weather_stream_processor.process_raw_batch(max_records=20)

        # Step 2: JEV Verification Processing (weather.clean -> weather.verified)
        verified_events = jev_stream_processor.process_clean_batch(max_records=20)

        # Step 3: Sink Consumer (weather.verified -> alertness > 0.90 gate -> PostgreSQL & WebSockets)
        sink_results = sink_consumer.consume_loop(max_records=20)

        return {
            "status": "SUCCESS",
            "clean_processed": len(clean_events),
            "verified_processed": len(verified_events),
            "sink_processed": len(sink_results),
            "sink_accepted": sum(1 for r in sink_results if r.get("accepted")),
            "sink_filtered": sum(1 for r in sink_results if r.get("status") == "FILTERED"),
        }

    def run_worker(self, poll_interval: float = 2.0):
        """Continuous background worker loop for the end-to-end streaming pipeline."""
        import signal
        import time

        if not settings.KAFKA_ENABLED:
            logger.info("[PIPELINE WORKER] KAFKA_ENABLED is False. Worker exiting.")
            return

        logger.info("[PIPELINE WORKER] Starting continuous streaming pipeline worker...")
        self._running = True

        def _handle_shutdown(signum, frame):
            logger.info("[PIPELINE WORKER] Shutdown signal received. Exiting...")
            self._running = False

        try:
            signal.signal(signal.SIGINT, _handle_shutdown)
            signal.signal(signal.SIGTERM, _handle_shutdown)
        except (ValueError, AttributeError):
            pass

        while getattr(self, "_running", True):
            try:
                res = self.run_pipeline_cycle()
                if res.get("clean_processed") or res.get("verified_processed") or res.get("sink_processed"):
                    logger.info("[PIPELINE WORKER] Cycle complete: clean=%d, verified=%d, sink_accepted=%d, sink_filtered=%d",
                                res.get("clean_processed", 0), res.get("verified_processed", 0),
                                res.get("sink_accepted", 0), res.get("sink_filtered", 0))
                time.sleep(poll_interval)
            except Exception as exc:
                logger.error("[PIPELINE WORKER] Unexpected error: %s", exc)
                time.sleep(poll_interval)


pipeline_orchestrator = PipelineOrchestrator()
