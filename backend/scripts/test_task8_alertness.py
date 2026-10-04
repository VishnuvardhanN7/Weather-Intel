"""
Test script for Task 8:
- alertness_score = 0.90 -> MUST be filtered
- alertness_score = 0.91 -> MUST be accepted into PostgreSQL
"""
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.kafka_service import kafka_service
from app.services.sink_consumer import sink_consumer
from app.core.database import async_session_factory
from app.models.weather_event import WeatherEvent
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Task8Test")

async def run_task8_test():
    timestamp = int(time.time())
    filtered_id = f"test_task8_filtered_{timestamp}"
    accepted_id = f"test_task8_accepted_{timestamp}"

    filtered_event = {
        "event_id": filtered_id,
        "title": "Task 8 Negative Test - Moderate Rain in Delhi",
        "description": "Rain in Delhi area, alertness score exactly 0.90",
        "event_type": "rainfall",
        "severity": "moderate",
        "city": "Delhi",
        "state": "Delhi",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "source": "api",
        "jev_probability": 0.90,
        "alertness_score": 0.90,
        "processing_status": "VERIFIED",
    }

    accepted_event = {
        "event_id": accepted_id,
        "title": "Task 8 Positive Test - Severe Cloudburst in Shimla",
        "description": "Flash flooding and high alertness event in Shimla, alertness score 0.91",
        "event_type": "flash_flood",
        "severity": "high",
        "city": "Shimla",
        "state": "Himachal Pradesh",
        "latitude": 31.1048,
        "longitude": 77.1734,
        "source": "api",
        "jev_probability": 0.95,
        "alertness_score": 0.91,
        "processing_status": "VERIFIED",
    }

    logger.info("--- Testing SinkConsumer directly ---")
    res_filtered = sink_consumer.process_verified_event(filtered_event)
    logger.info("Result for alertness_score 0.90: %s", res_filtered)
    assert res_filtered["accepted"] is False, "Event with alertness_score 0.90 must be FILTERED!"
    assert res_filtered["status"] == "FILTERED", "Status must be FILTERED!"

    res_accepted = sink_consumer.process_verified_event(accepted_event)
    logger.info("Result for alertness_score 0.91: %s", res_accepted)
    assert res_accepted["accepted"] is True, "Event with alertness_score 0.91 must be ACCEPTED!"
    assert res_accepted["status"] == "ACCEPTED", "Status must be ACCEPTED!"

    # Verify PostgreSQL DB state
    async with async_session_factory() as db:
        q_filt = await db.execute(select(WeatherEvent).where(WeatherEvent.source_id == filtered_id))
        db_filt = q_filt.scalar_one_or_none()
        assert db_filt is None, "Filtered event MUST NOT exist in PostgreSQL database!"

        q_acc = await db.execute(select(WeatherEvent).where(WeatherEvent.source_id == accepted_id))
        db_acc = q_acc.scalar_one_or_none()
        assert db_acc is not None, "Accepted event MUST exist in PostgreSQL database!"
        logger.info("Found accepted event in DB: id=%s, title='%s'", db_acc.id, db_acc.title)

        # Cleanup test accepted record
        await db.delete(db_acc)
        await db.commit()

    print("\n=======================================================")
    print("TASK 8 TEST PASSED PERFECTLY!")
    print("alertness_score = 0.90 -> FILTERED (Not in PostgreSQL)")
    print("alertness_score = 0.91 -> ACCEPTED (Stored in PostgreSQL)")
    print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_task8_test())
