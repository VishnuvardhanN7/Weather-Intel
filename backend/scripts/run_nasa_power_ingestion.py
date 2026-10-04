#!/usr/bin/env python
"""
NASA POWER Meteorological Data Ingestion Worker (PS-26069).

Fetches solar and meteorological data from NASA POWER API,
normalizes events, and publishes to Kafka `weather.raw`.

Usage:
  python scripts/run_nasa_power_ingestion.py [--once] [--interval 60]
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
from app.collectors.nasa_power_collector import nasa_power_collector
from app.services.source_registry import metrics_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nasa_power_worker")

running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("[NASA_POWER] Received shutdown signal (%s). Stopping NASA POWER worker...", signum)
    running = False


async def run_ingestion_cycle():
    logger.info("[NASA_POWER] Starting NASA POWER ingestion cycle...")
    try:
        events, results = await nasa_power_collector.fetch_and_publish_all()
        published_count = sum(1 for status in results.values() if status)
        failed_count = len(results) - published_count
        logger.info(
            "[NASA_POWER] Ingestion cycle complete: %d records collected, %d published to weather.raw, %d failed. Health: %s",
            len(events), published_count, failed_count, nasa_power_collector.health_state
        )
        return events, results
    except Exception as e:
        logger.error("[NASA_POWER] Ingestion cycle error: %s", e, exc_info=True)
        metrics_tracker.record_failure("nasa_power", str(e))
        return [], {}


async def main():
    parser = argparse.ArgumentParser(description="Run NASA POWER Ingestion Worker")
    parser.add_argument("--once", action="store_true", help="Run a single ingestion cycle and exit")
    parser.add_argument("--interval", type=float, default=60.0, help="Polling interval in minutes (default: 60)")
    args = parser.parse_args()

    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    except (ValueError, AttributeError):
        pass

    interval_seconds = int(args.interval * 60) if args.interval <= 60 else int(args.interval)
    env_interval = os.getenv("NASA_POWER_INTERVAL_SECONDS")
    if env_interval:
        try:
            interval_seconds = int(env_interval)
        except ValueError:
            pass

    if not getattr(settings, "NASA_POWER_ENABLED", False):
        logger.warning("[NASA_POWER] NASA_POWER_ENABLED is set to false in configuration. Worker standing by (DISABLED state).")
        if args.once:
            sys.exit(0)

    logger.info("[NASA_POWER] Worker initialized. Interval: %d seconds (%d mins)", interval_seconds, interval_seconds // 60)

    if args.once:
        await run_ingestion_cycle()
        return

    logger.info("[NASA_POWER] Entering continuous polling loop. Press Ctrl+C to exit.")
    while running:
        await run_ingestion_cycle()
        for _ in range(interval_seconds):
            if not running:
                break
            await asyncio.sleep(1)

    logger.info("[NASA_POWER] NASA POWER Worker shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
