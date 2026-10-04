"""
Kafka Service Layer.

Provides a clean abstraction for publishing and consuming events across Kafka topics:
- weather.raw
- weather.clean
- weather.verified

Handles JSON serialization/deserialization, stable event identifier assignment,
and graceful fallback when Kafka is disabled or unreachable.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy singleton instances
_kafka_producer = None


def get_kafka_producer():
    """Lazy initialize KafkaProducer if KAFKA_ENABLED is True."""
    global _kafka_producer
    if not settings.KAFKA_ENABLED:
        return None

    if _kafka_producer is None:
        try:
            from kafka import KafkaProducer
            _kafka_producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=3,
                request_timeout_ms=5000,
            )
            logger.info("KafkaProducer initialized connecting to %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as exc:
            logger.warning("Failed to initialize KafkaProducer (%s). Kafka publishing will fallback gracefully.", exc)
            _kafka_producer = None

    return _kafka_producer


def create_kafka_consumer(topic: str, group_id: Optional[str] = None, auto_offset_reset: str = "earliest"):
    """Create a new confluent_kafka Consumer instance for the specified topic."""
    if not settings.KAFKA_ENABLED:
        logger.debug("Kafka is disabled. Skipping consumer creation for topic %s.", topic)
        return None

    try:
        from confluent_kafka import Consumer
        consumer_group = group_id or f"weather-group-{topic}-{uuid.uuid4().hex[:6]}"
        conf = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": consumer_group,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": False,
        }
        consumer = Consumer(conf)
        consumer.subscribe([topic])
        logger.info("confluent_kafka Consumer created and subscribed to topic '%s' (group: %s)", topic, consumer_group)
        return consumer
    except Exception as exc:
        logger.warning("Failed to create confluent_kafka Consumer for topic '%s': %s", topic, exc)
        return None



def ensure_event_id(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure every event dictionary has a stable event_id and timestamp."""
    event = dict(event_data)
    if not event.get("event_id"):
        raw_id = event.get("id") or event.get("source_id")
        if raw_id:
            event["event_id"] = f"weather_{raw_id}"
        else:
            event["event_id"] = f"weather_{uuid.uuid4().hex[:12]}"

    if not event.get("timestamp"):
        event["timestamp"] = datetime.now(timezone.utc).isoformat()

    return event


def format_verified_event(event_data: Dict[str, Any], jev_probability: float = 0.0, alertness_score: Optional[float] = None) -> Dict[str, Any]:
    """Format AI-Verified weather event payload strictly matching Phase 1 target schema."""
    event = ensure_event_id(event_data)
    event_id = event["event_id"]

    clean_text = event.get("clean_text") or event.get("raw_text")
    if not clean_text:
        title = event.get("title", "")
        desc = event.get("description", "")
        clean_text = f"{title} - {desc}".strip(" -")

    location = event.get("location")
    if not isinstance(location, dict):
        location = {
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
            "city": event.get("city") or "Unknown",
            "state": event.get("state") or "Unknown"
        }

    jev_prob = float(event.get("jev_probability", event.get("jev_score", jev_probability)))

    if alertness_score is not None:
        computed_alertness = float(alertness_score)
    elif "alertness_score" in event and event["alertness_score"] is not None:
        try:
            computed_alertness = float(event["alertness_score"])
        except (ValueError, TypeError):
            computed_alertness = 0.0
    else:
        sev = str(event.get("severity", "moderate")).lower()
        sev_factor = 1.0 if sev in ("critical", "high") else (0.85 if sev == "moderate" else 0.70)
        computed_alertness = round(jev_prob * sev_factor, 3)

    return {
        "event_id": event_id,
        "source": str(event.get("source", "unknown")),
        "timestamp": event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "clean_text": clean_text or "Verified Weather Event",
        "category": str(event.get("category", event.get("event_type", "other"))),
        "category_confidence": float(event.get("category_confidence", 0.90)),
        "severity": str(event.get("severity", "moderate")),
        "location": location,
        "media": event.get("media", []),
        "photos": event.get("photos", []),
        "videos": event.get("videos", []),
        "source_url": event.get("source_url"),
        "metadata": event.get("metadata", {}),
        "is_fake": bool(event.get("is_fake", False)),
        "is_duplicate": bool(event.get("is_duplicate", False)),
        "jev_probability": jev_prob,
        "verification_status": "AI_VERIFIED",
        "alertness_score": computed_alertness
    }


class KafkaService:
    """Service abstraction for Kafka raw, clean, and verified topic operations."""

    def __init__(self):
        self.raw_topic = settings.KAFKA_RAW_TOPIC
        self.clean_topic = settings.KAFKA_CLEAN_TOPIC
        self.verified_topic = settings.KAFKA_VERIFIED_TOPIC

    def _publish(self, topic: str, event_data: Dict[str, Any], default_status: str) -> bool:
        """Publish payload to a specified Kafka topic."""
        event = ensure_event_id(event_data)
        if "processing_status" not in event:
            event["processing_status"] = default_status

        if not settings.KAFKA_ENABLED:
            logger.debug("Kafka disabled (KAFKA_ENABLED=false). Skipping publish to topic '%s' for event_id '%s'",
                         topic, event["event_id"])
            return False

        producer = get_kafka_producer()
        if not producer:
            logger.warning("KafkaProducer unavailable. Skipping message send to topic '%s'", topic)
            return False

        try:
            event_id = event["event_id"]
            future = producer.send(topic, key=event_id, value=event)
            # Flush or inspect asynchronously in production, flush synchronously for safety if needed
            producer.flush(timeout=3)
            logger.info("Successfully published event_id '%s' to Kafka topic '%s'", event_id, topic)
            return True
        except Exception as exc:
            logger.error("Error publishing event to Kafka topic '%s': %s", topic, exc)
            return False

    def publish_raw_event(self, event_data: Dict[str, Any]) -> bool:
        """Publish raw ingested weather event to weather.raw topic."""
        return self._publish(self.raw_topic, event_data, default_status="RAW")

    def publish_clean_event(self, event_data: Dict[str, Any]) -> bool:
        """Publish processed and normalized weather event to weather.clean topic."""
        return self._publish(self.clean_topic, event_data, default_status="CLEAN")

    def publish_verified_event(self, event_data: Dict[str, Any]) -> bool:
        """Publish admin/AI-approved verified event to weather.verified topic."""
        formatted = format_verified_event(
            event_data,
            jev_probability=event_data.get("jev_probability", event_data.get("jev_score", 0.0)),
            alertness_score=event_data.get("alertness_score")
        )
        return self._publish(self.verified_topic, formatted, default_status="VERIFIED")

    def consume_raw_events(self, max_records: int = 10, timeout_ms: int = 2000) -> List[Dict[str, Any]]:
        """Consume pending events from weather.raw topic."""
        return self._consume(self.raw_topic, max_records=max_records, timeout_ms=timeout_ms)

    def consume_clean_events(self, max_records: int = 10, timeout_ms: int = 2000) -> List[Dict[str, Any]]:
        """Consume pending events from weather.clean topic."""
        return self._consume(self.clean_topic, max_records=max_records, timeout_ms=timeout_ms)

    def consume_verified_events(self, max_records: int = 10, timeout_ms: int = 2000) -> List[Dict[str, Any]]:
        """Consume pending events from weather.verified topic."""
        return self._consume(self.verified_topic, max_records=max_records, timeout_ms=timeout_ms)

    def _consume(self, topic: str, max_records: int = 10, timeout_ms: int = 2000) -> List[Dict[str, Any]]:
        """Internal consumer helper using confluent_kafka."""
        if not settings.KAFKA_ENABLED:
            return []

        consumer = create_kafka_consumer(topic)
        if not consumer:
            return []

        events = []
        try:
            messages = consumer.consume(num_messages=max_records, timeout=timeout_ms / 1000.0)
            for msg in messages:
                if msg is None:
                    continue
                if msg.error():
                    logger.warning("Kafka message error on topic '%s': %s", topic, msg.error())
                    continue

                raw_val = msg.value()
                if not raw_val:
                    continue

                try:
                    if isinstance(raw_val, bytes):
                        raw_val = raw_val.decode("utf-8")
                    val_dict = json.loads(raw_val)
                    if isinstance(val_dict, dict):
                        events.append(val_dict)
                except Exception as parse_err:
                    logger.warning("Failed to deserialize Kafka JSON message on topic '%s': %s", topic, parse_err)

            logger.info("Consumed %d events from Kafka topic '%s'", len(events), topic)
        except Exception as exc:
            logger.warning("Error consuming events from Kafka topic '%s': %s", topic, exc)
        finally:
            try:
                consumer.close()
            except Exception:
                pass

        return events



# Shared global service instance
kafka_service = KafkaService()

