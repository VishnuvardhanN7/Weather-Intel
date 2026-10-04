#!/usr/bin/env python
"""
Open-Meteo Live Ingestion Worker (PS-26069).

Fetches current weather observations for Indian locations from Open-Meteo API
and publishes normalized events to Kafka `weather.raw` topic.

Usage:
  python scripts/run_open_meteo_ingestion.py [--once] [--interval 15]
"""

import argparse
import asyncio
import logging
import os
import signal
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.collectors.open_meteo_collector import open_meteo_collector
from app.services.source_registry import metrics_tracker as source_metrics_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("open_meteo_worker")

running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("[OPEN_METEO] Received shutdown signal (%s). Stopping ingestion worker...", signum)
    running = False


async def run_ingestion_cycle():
    logger.info("[OPEN_METEO] Starting live ingestion cycle...")
    try:
        events, results = await open_meteo_collector.fetch_and_publish_live()
        published_count = sum(1 for status in results.values() if status)
        failed_count = len(results) - published_count
        logger.info(
            "[OPEN_METEO] Ingestion cycle complete: %d records fetched, %d published to weather.raw, %d failed",
            len(events), published_count, failed_count
        )
        return events, results
    except Exception as e:
        logger.error("[OPEN_METEO] Ingestion cycle error: %s", e, exc_info=True)
        source_metrics_tracker.record_failure("open_meteo", str(e))
        return [], {}


async def main():
    parser = argparse.ArgumentParser(description="Run Open-Meteo Live Ingestion Worker")
    parser.add_argument("--once", action="store_true", help="Run a single ingestion cycle and exit")
    parser.add_argument("--interval", type=float, default=15.0, help="Polling interval in minutes (default: 15)")
    args = parser.parse_args()

    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    except (ValueError, AttributeError):
        pass

    # If interval is passed in seconds (>60) or minutes (<=60)
    interval_seconds = int(args.interval * 60) if args.interval <= 60 else int(args.interval)

    # Check env var override
    env_interval = os.getenv("OPEN_METEO_INTERVAL_SECONDS")
    if env_interval:
        try:
            interval_seconds = int(env_interval)
        except ValueError:
            pass

    enabled_env = os.getenv("OPEN_METEO_ENABLED", "true").lower()
    if enabled_env in ("false", "0", "no"):
        logger.warning("[OPEN_METEO] OPEN_METEO_ENABLED is set to false. Exiting worker.")
        sys.exit(0)

    logger.info("[OPEN_METEO] Worker initialized. Interval: %d seconds (%d mins)", interval_seconds, interval_seconds // 60)

    if args.once:
        await run_ingestion_cycle()
        return

    logger.info("[OPEN_METEO] Entering continuous polling loop. Press Ctrl+C to exit.")
    while running:
        await run_ingestion_cycle()
        for _ in range(interval_seconds):
            if not running:
                break
            await asyncio.sleep(1)

    logger.info("[OPEN_METEO] Worker shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
