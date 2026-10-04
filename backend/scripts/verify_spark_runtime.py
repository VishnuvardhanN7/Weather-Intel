"""
Real Runtime End-to-End Verification Script for Kafka + Spark Architecture.

Flow:
1. Initialize PySpark Structured Streaming processor on weather.raw
2. Publish test event spark_runtime_test_001 to weather.raw
3. Allow Spark to consume, run AI Engines 1, 2, 3, and produce clean event to weather.clean
4. Consume from weather.clean and verify spark_runtime_test_001 output
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
settings.KAFKA_ENABLED = True
os.environ["KAFKA_ENABLED"] = "true"

from app.services.kafka_service import kafka_service
from app.spark.weather_stream_processor import weather_stream_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_spark_runtime")

def main():
    logger.info("==================================================")
    logger.info("REAL RUNTIME VERIFICATION: KAFKA -> SPARK -> KAFKA")
    logger.info("==================================================")

    # 1. Start REAL PySpark Structured Streaming Processor
    logger.info("Step 1: Starting PySpark Structured Streaming Processor...")
    query, spark = weather_stream_processor.start_pyspark_streaming()
    assert query is not None, "FAILED to start PySpark Structured Streaming query!"
    logger.info("[VERIFIED] Spark Structured Streaming Kafka processor active on topic '%s'.", settings.KAFKA_RAW_TOPIC)

    # Allow streaming query 2 seconds to initialize
    time.sleep(2)

    # 2. Publish Test Event to weather.raw
    test_event_id = f"spark_runtime_test_{uuid.uuid4().hex[:6]}"
    test_payload = {
        "event_id": test_event_id,
        "title": "Heavy rainfall in Bengaluru",
        "description": "Heavy rainfall reported near Silk Board Junction Bengaluru",
        "city": "Bengaluru",
        "state": "Karnataka",
        "event_type": "rainfall",
        "source": "spark_runtime_test",
        "processing_status": "RAW"
    }

    logger.info("Step 2: Publishing test event '%s' to topic '%s'...", test_event_id, settings.KAFKA_RAW_TOPIC)
    published = kafka_service.publish_raw_event(test_payload)
    assert published is True, f"FAILED to publish test event to {settings.KAFKA_RAW_TOPIC}"
    logger.info("[VERIFIED] Test event '%s' successfully published to topic '%s'", test_event_id, settings.KAFKA_RAW_TOPIC)

    # 3. Poll for clean event from weather.clean
    logger.info("Step 3 & 4: Waiting for PySpark Structured Streaming to process raw event and produce to '%s'...", settings.KAFKA_CLEAN_TOPIC)
    found_event = None
    start_time = time.time()
    
    while time.time() - start_time < 15:
        time.sleep(2)
        events = kafka_service.consume_clean_events(max_records=50, timeout_ms=3000)
        for evt in events:
            if isinstance(evt, dict) and evt.get("event_id") == test_event_id:
                found_event = evt
                break
        if found_event:
            break

    # Stop Spark streaming query cleanly
    logger.info("Cleaning up Spark streaming session...")
    try:
        query.stop()
        if spark:
            spark.stop()
    except Exception:
        pass

    # 5. Assertions
    assert found_event is not None, f"FAILED: Event '{test_event_id}' was NOT found in {settings.KAFKA_CLEAN_TOPIC} within 15s!"

    logger.info("==================================================")
    logger.info("SUCCESS: REAL SPARK STRUCTURED STREAMING RUNTIME TEST PASSED!")
    logger.info("Received Clean Event Schema:")
    logger.info(json.dumps(found_event, indent=2))
    logger.info("==================================================")
    print(f"REAL_SPARK_RUNTIME_SUCCESS: {found_event['event_id']}")

if __name__ == "__main__":
    main()
