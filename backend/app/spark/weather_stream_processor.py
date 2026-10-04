"""
Apache Spark Processing Layer — Weather Stream Processor.

Consumes raw events from weather.raw, normalizes and validates JSON payloads,
applies AI Engine 1 (Event Organization), Engine 2 (Fake News), Engine 3 (Deduplication),
and outputs clean, enriched events to weather.clean.

Uses PySpark Structured Streaming with graceful fallback when Spark is disabled.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# 1. Ensure valid JDK (17 or 21) is selected if default JAVA_HOME points to unsupported JDK 25
possible_jdks = [
    r"C:\Program Files\Android\Android Studio\jbr",
    r"C:\Users\nvvar\.vscode\extensions\redhat.java-1.56.0-win32-x64\jre\21.0.1",
]

for jdk_path in possible_jdks:
    if os.path.exists(os.path.join(jdk_path, "bin", "java.exe")):
        os.environ["JAVA_HOME"] = jdk_path
        os.environ["PATH"] = os.path.join(jdk_path, "bin") + os.path.pathsep + os.environ.get("PATH", "")
        break

# 2. Ensure HADOOP_HOME is set for Windows winutils compatibility
hadoop_home = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "hadoop_home"))
if os.path.exists(os.path.join(hadoop_home, "bin", "winutils.exe")):
    os.environ["HADOOP_HOME"] = hadoop_home
    os.environ["PATH"] = os.path.join(hadoop_home, "bin") + os.path.pathsep + os.environ.get("PATH", "")

from app.core.config import settings
from app.ai.event_organization import event_organization_engine
from app.ai.fake_news_engine import fake_news_engine
from app.ai.deduplication_engine import deduplication_engine
from app.services.kafka_service import kafka_service, ensure_event_id

logger = logging.getLogger(__name__)


def process_event_with_ai_engines(event: Dict[str, Any], existing_events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Process a single raw weather event payload through AI Engines 1, 2, and 3.

    Pipeline stages:
      1. Parse & validate required fields
      2. Engine 1: Event Organization (Category, Confidence, Normalized Text, Entities)
      3. Engine 2: Fake News Detection (is_fake, fake_score, reason)
      4. Engine 3: Deduplication (is_duplicate, duplicate_of_id)
      5. Output clean event schema
    """
    # 1. Normalize and validate payload
    event = ensure_event_id(event)
    raw_title = event.get("title") or ""
    raw_desc = event.get("description") or event.get("text") or ""
    combined_text = f"{raw_title} {raw_desc}".strip()

    if not combined_text:
        logger.warning("Event %s missing text content. Marking invalid.", event.get("event_id"))
        combined_text = "No content provided"

    # Location structure
    location = event.get("location") or {
        "latitude": event.get("latitude"),
        "longitude": event.get("longitude"),
        "city": event.get("city") or "Unknown",
        "state": event.get("state") or "Unknown",
    }

    # 2. AI Engine 1 — Event Organization
    org_result = event_organization_engine.organize_text(raw_desc, title=raw_title)

    # 3. AI Engine 2 — Fake News Detection
    fake_result = fake_news_engine.detect_fake_news(raw_title, raw_desc)

    # 4. AI Engine 3 — Deduplication
    dedup_result = deduplication_engine.check_duplicate_dict(event, existing_events=existing_events)

    # 5. Build Clean Event Schema (Preserving raw/source info and adding clean info)
    clean_event = {
        "event_id": event.get("event_id"),
        "source": event.get("source") or "unknown",
        "timestamp": event.get("timestamp"),
        "raw_text": combined_text,
        "clean_text": org_result.get("normalized_text", combined_text),
        "category": org_result.get("category", "other"),
        "category_confidence": org_result.get("confidence", 0.0),
        "severity": str(event.get("severity") or "moderate"),
        "language": org_result.get("language", "en"),
        "entities": org_result.get("entities", []),
        "is_fake": fake_result.get("is_fake", False),
        "fake_score": fake_result.get("fake_score", 0.0),
        "fake_reason": fake_result.get("reason", ""),
        "is_duplicate": dedup_result.get("is_duplicate", False),
        "duplicate_of_id": dedup_result.get("duplicate_of_id"),
        "location": location,
        "media": event.get("media", []),
        "photos": event.get("photos", []),
        "videos": event.get("videos", []),
        "source_url": event.get("source_url"),
        "metadata": event.get("metadata", {}),
        "processing_status": "CLEAN",
    }

    logger.info(
        "AI Processing Complete for event '%s': Category=%s (conf=%.2f), is_fake=%s (score=%.2f), is_duplicate=%s",
        clean_event["event_id"],
        clean_event["category"],
        clean_event["category_confidence"],
        clean_event["is_fake"],
        clean_event["fake_score"],
        clean_event["is_duplicate"],
    )

    return clean_event


class WeatherStreamProcessor:
    """PySpark Structured Streaming & Modular Stream Processor Orchestrator."""

    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.raw_topic = settings.KAFKA_RAW_TOPIC
        self.clean_topic = settings.KAFKA_CLEAN_TOPIC

    def start_pyspark_streaming(self):
        """
        PySpark Structured Streaming pipeline setup.
        Consumes weather.raw Kafka stream via spark.readStream, applies AI transformation, writes to weather.clean.
        """
        try:
            from pyspark.sql import SparkSession

            logger.info("Initializing PySpark session for WeatherStreamProcessor...")
            spark = SparkSession.builder \
                .appName("NationalWeatherStreamProcessor") \
                .config("spark.streaming.stopGracefullyOnShutdown", "true") \
                .getOrCreate()

            spark.sparkContext.setLogLevel("WARN")

            # Structured Streaming dataframe reading from Kafka topic weather.raw
            raw_df = spark.readStream \
                .format("kafka") \
                .option("kafka.bootstrap.servers", self.bootstrap_servers) \
                .option("subscribe", self.raw_topic) \
                .option("startingOffsets", "earliest") \
                .load()

            def process_micro_batch(batch_df, batch_id):
                rows = batch_df.collect()
                if not rows:
                    return

                logger.info("[SPARK STREAM] Batch %s received %d raw events from topic '%s'", batch_id, len(rows), self.raw_topic)
                for row in rows:
                    raw_val = row.value
                    if isinstance(raw_val, bytes):
                        raw_val = raw_val.decode("utf-8")

                    try:
                        raw_dict = json.loads(raw_val)
                    except Exception:
                        raw_dict = {"title": str(raw_val), "event_id": f"spark_raw_{row.offset}"}

                    clean_event = process_event_with_ai_engines(raw_dict)
                    published = kafka_service.publish_clean_event(clean_event)
                    if published:
                        logger.info("[SPARK STREAM] Published clean event '%s' to topic '%s'", clean_event["event_id"], self.clean_topic)

            query = raw_df.writeStream \
                .foreachBatch(process_micro_batch) \
                .start()

            logger.info("Spark Structured Streaming Kafka processor active on topic '%s'.", self.raw_topic)
            return query, spark
        except Exception as exc:
            logger.warning("Spark Kafka connector unavailable — using fallback processor. Error: %s", exc)
            return None, None

    def process_raw_batch(self, max_records: int = 100) -> List[Dict[str, Any]]:
        """
        Fallback modular batch stream processor.
        Consumes events from weather.raw, passes through AI engines, and publishes to weather.clean.
        """
        raw_events = kafka_service.consume_raw_events(max_records=max_records)
        if not raw_events:
            logger.debug("No raw events to process in weather.raw.")
            return []

        clean_events = []
        for raw_evt in raw_events:
            clean_evt = process_event_with_ai_engines(raw_evt, existing_events=clean_events)
            published = kafka_service.publish_clean_event(clean_evt)
            if published:
                logger.info("Published clean event '%s' to topic '%s'", clean_evt["event_id"], self.clean_topic)
            clean_events.append(clean_evt)

        return clean_events


weather_stream_processor = WeatherStreamProcessor()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Weather Stream Processor in standalone mode...")
    os.environ["KAFKA_ENABLED"] = "true"
    settings.KAFKA_ENABLED = True
    processor = WeatherStreamProcessor()
    query, spark = processor.start_pyspark_streaming()
    if query:
        logger.info("Spark Structured Streaming query running. Awaiting termination...")
        try:
            query.awaitTermination()
        except KeyboardInterrupt:
            logger.info("Stopping Spark Structured Streaming query...")
            query.stop()
            if spark:
                spark.stop()
    else:
        logger.info("Running modular batch stream processor cycle...")
        processed = processor.process_raw_batch()
        logger.info("Processed %d events.", len(processed))
