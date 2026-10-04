"""
Verification script for KAFKA_ENABLED=false ingestion pipeline flow.
Verifies that collectors -> Spark/AI -> JEV -> Sink -> DB flow works correctly
without requiring Kafka infrastructure.
"""

import asyncio
import logging
from app.core.config import settings
from app.core.database import async_session_factory
from app.services.ingestion_service import run_ingestion
from app.services.streaming_pipeline import jev_stream_processor
from app.services.sink_consumer import sink_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_no_kafka")


async def main():
    logger.info("1. Setting KAFKA_ENABLED=False for verification...")
    settings.KAFKA_ENABLED = False

    logger.info("2. Test JEVStreamProcessor direct non-Kafka fallback for severe weather event...")
    clean_severe_event = {
        "event_id": "test_severe_monsoon_cloudburst_mumbai_99",
        "source": "api",
        "title": "Severe Flash Flood Cloudburst in Mumbai",
        "description": "Torrential downpour 150mm/hr causes severe cloudburst and flash flooding in Mumbai.",
        "severity": "critical",
        "is_fake": False,
        "fake_score": 0.0,
        "location": {"latitude": 19.0760, "longitude": 72.8777, "city": "Mumbai", "state": "Maharashtra"}
    }

    verified_evt = jev_stream_processor.process_clean_event(clean_severe_event)
    assert verified_evt is not None, "JEV process_clean_event returned None when Kafka disabled!"
    assert verified_evt["jev_probability"] >= 0.60, "JEV probability < 0.60"
    assert verified_evt["alertness_score"] > 0.90, f"Alertness score {verified_evt['alertness_score']} <= 0.90"
    logger.info("   -> JEV Accepted verified event with alertness_score = %.3f (> 0.90)", verified_evt["alertness_score"])

    async with async_session_factory() as db:
        logger.info("3. Test Sink Consumer persistence for severe verified event...")
        sink_res = await sink_consumer.process_verified_event_async(verified_evt, db_session=db)
        assert sink_res["accepted"] is True, f"Sink rejected severe event: {sink_res}"
        assert sink_res["status"] == "ACCEPTED", f"Sink status is not ACCEPTED: {sink_res}"
        logger.info("   -> Sink ACCEPTED severe event! DB action: %s, stored: %s", sink_res.get("db_action"), sink_res.get("postgres_stored"))

        logger.info("4. Test full run_ingestion pipeline for open_meteo...")
        res = await run_ingestion(db, sources=["open_meteo"], use_sample_data=False)

        logger.info("=== FULL INGESTION RESULTS SUMMARY ===")
        logger.info("Status: %s", res["status"])
        logger.info("Collected: %d", res["collected"])
        logger.info("Spark Processed: %d", res["spark_processed"])
        logger.info("AI Evaluated: %d", res["ai_evaluated"])
        logger.info("JEV Accepted: %d", res["jev_accepted"])
        logger.info("JEV Rejected: %d", res["jev_rejected"])
        logger.info("Processed by Sink (accepted alertness > 0.90): %d", res["processed_by_sink"])
        logger.info("New Inserts: %d", res["new_inserts"])
        logger.info("Already Existing: %d", res["already_existing"])
        logger.info("Filtered Routine (alertness <= 0.90): %d", res["filtered_routine"])
        logger.info("Total DB Records: %d", res["total_db_records"])

        assert res["collected"] > 0, "No records collected"
        assert res["spark_processed"] == res["collected"], "Spark processed count mismatch"
        assert res["jev_accepted"] == res["collected"], "JEV accepted count mismatch"
        assert res["filtered_routine"] == res["jev_accepted"], "Routine weather events were not filtered by alertness gate"
        logger.info("SUCCESS: All verification checks passed! Non-Kafka fallback mode works perfectly!")


if __name__ == "__main__":
    asyncio.run(main())
