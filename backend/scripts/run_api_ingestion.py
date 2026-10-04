#!/usr/bin/env python
"""
Standalone Real OpenWeather API Ingestion Worker (PS-26069).

Fetches live weather observations for configured Indian cities from OpenWeather API
and publishes raw events directly to Kafka `weather.raw` topic without direct DB insertion.

Usage (Windows):
  .\\venv\\Scripts\\python.exe scripts\\run_api_ingestion.py [--once] [--interval 300] [--sample]
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
from app.collectors.api_collector import api_collector, INDIAN_CITIES_COORDS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("api_ingestion_worker")

running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("Received shutdown signal (%s). Stopping API ingestion worker...", signum)
    running = False


async def run_ingestion_cycle(use_sample_data: bool = False):
    logger.info("Starting OpenWeather ingestion cycle for %d Indian cities...", len(INDIAN_CITIES_COORDS))
    cities = list(INDIAN_CITIES_COORDS.keys())
    results = await api_collector.publish_raw_weather_bulk(cities=cities, use_sample_data=use_sample_data)
    
    success_count = sum(1 for s in results.values() if s)
    failed_count = len(cities) - success_count
    
    logger.info(
        "Ingestion cycle completed: %d/%d cities processed successfully (%d failed/skipped)",
        success_count, len(cities), failed_count
    )
    for city, ok in results.items():
        status_str = "SUCCESS" if ok else "FAILED/SKIPPED"
        logger.debug("City '%s': %s", city, status_str)
        
    return results


async def main():
    parser = argparse.ArgumentParser(description="Run OpenWeather Real API Ingestion Worker")
    parser.add_argument("--once", action="store_true", help="Run a single ingestion cycle and exit")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds (default: 300s)")
    parser.add_argument("--sample", action="store_true", help="Allow sample data fallback if API key is missing")
    args = parser.parse_args()

    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    except (ValueError, AttributeError):
        pass

    if not settings.KAFKA_ENABLED:
        logger.warning("KAFKA_ENABLED is False in configuration. Raw event publishing to Kafka will be skipped/mocked.")

    if not settings.OPENWEATHER_API_KEY:
        if not args.sample:
            logger.error("OPENWEATHER_API_KEY is not configured in .env. Exiting.")
            sys.exit(1)
        else:
            logger.warning("OPENWEATHER_API_KEY is missing. Running in --sample fallback mode.")
    else:
        logger.info("OPENWEATHER_API_KEY verified. Live OpenWeather API ingestion active.")

    if args.once:
        await run_ingestion_cycle(use_sample_data=args.sample)
        return

    logger.info("Entering continuous polling loop (interval: %ds)... Press Ctrl+C to exit.", args.interval)
    while running:
        await run_ingestion_cycle(use_sample_data=args.sample)
        for _ in range(args.interval):
            if not running:
                break
            await asyncio.sleep(1)

    logger.info("API ingestion worker shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
