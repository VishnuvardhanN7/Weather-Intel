#!/usr/bin/env python
"""
Open-Meteo Historical Backfill Worker (PS-26069).

Fetches historical hourly weather records from Open-Meteo Archive API,
normalizes events, and publishes them to Kafka `weather.raw` topic.

Usage:
  python scripts/backfill_open_meteo.py --start 2025-01-01 --end 2025-01-07 --cities Delhi,Mumbai
"""

import argparse
import asyncio
import logging
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.location_registry import get_locations_by_names, INDIAN_LOCATIONS
from app.collectors.open_meteo_collector import open_meteo_collector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("open_meteo_backfill")


async def main():
    parser = argparse.ArgumentParser(description="Open-Meteo Historical Weather Backfill")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--cities", help="Comma-separated list of city names or slugs (default: all registered Indian locations)")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of locations per API batch (default: 10)")
    args = parser.parse_args()

    if args.cities:
        city_names = [c.strip() for c in args.cities.split(",") if c.strip()]
        locations = get_locations_by_names(city_names)
        if not locations:
            logger.error("[OPEN_METEO_BACKFILL] No valid locations found for specified cities: %s", args.cities)
            sys.exit(1)
    else:
        locations = INDIAN_LOCATIONS

    logger.info("[OPEN_METEO_BACKFILL] %s → %s", args.start, args.end)
    logger.info("[OPEN_METEO_BACKFILL] Locations: %d", len(locations))

    events, results = await open_meteo_collector.fetch_and_publish_historical(
        locations=locations,
        start_date=args.start,
        end_date=args.end,
        batch_size=args.batch_size
    )

    published_count = sum(1 for status in results.values() if status)
    logger.info("[OPEN_METEO_BACKFILL] Hourly records: %d", len(events))
    logger.info("[OPEN_METEO_BACKFILL] Published: %d", published_count)


if __name__ == "__main__":
    asyncio.run(main())
