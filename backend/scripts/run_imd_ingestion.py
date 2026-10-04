#!/usr/bin/env python
"""
IMD Live Ingestion Worker (PS-26069).

Fetches official weather observations, forecasts, district nowcasts, warnings, and rainfall reports
from India Meteorological Department (IMD) API & public RSS feeds and publishes normalized events
directly to Kafka `weather.raw` topic.

Usage:
  python scripts/run_imd_ingestion.py [--once] [--interval 15]
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
from app.collectors.imd_collector import imd_collector
from app.services.source_registry import metrics_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("imd_worker")

running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("[IMD] Received shutdown signal (%s). Stopping IMD ingestion worker...", signum)
    running = False


async def run_ingestion_cycle():
    logger.info("[IMD] Starting IMD ingestion cycle...")
    try:
        events, results = await imd_collector.fetch_and_publish_all()
        published_count = sum(1 for status in results.values() if status)
        failed_count = len(results) - published_count
        logger.info(
            "[IMD] Ingestion cycle complete: %d records collected, %d published to weather.raw, %d failed/skipped",
            len(events), published_count, failed_count
        )
        return events, results
    except Exception as e:
        logger.error("[IMD] Ingestion cycle error: %s", e, exc_info=True)
        metrics_tracker.record_failure("imd", str(e))
        return [], {}


async def main():
    parser = argparse.ArgumentParser(description="Run IMD Official Weather Ingestion Worker")
    parser.add_argument("--once", action="store_true", help="Run a single ingestion cycle and exit")
    parser.add_argument("--interval", type=float, default=15.0, help="Polling interval in minutes (default: 15)")
    args = parser.parse_args()

    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    except (ValueError, AttributeError):
        pass

    interval_seconds = int(args.interval * 60) if args.interval <= 60 else int(args.interval)
    env_interval = os.getenv("IMD_INTERVAL_SECONDS")
    if env_interval:
        try:
            interval_seconds = int(env_interval)
        except ValueError:
            pass

    if not getattr(settings, "IMD_ENABLED", True):
        logger.warning("[IMD] IMD_ENABLED is set to false in configuration. Exiting worker.")
        sys.exit(0)

    logger.info("[IMD] Worker initialized. Interval: %d seconds (%d mins)", interval_seconds, interval_seconds // 60)

    if args.once:
        await run_ingestion_cycle()
        return

    logger.info("[IMD] Entering continuous polling loop. Press Ctrl+C to exit.")
    while running:
        await run_ingestion_cycle()
        for _ in range(interval_seconds):
            if not running:
                break
            await asyncio.sleep(1)

    logger.info("[IMD] IMD Worker shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
