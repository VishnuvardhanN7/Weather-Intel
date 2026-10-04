#!/usr/bin/env python3
"""
Data Collection Runner for National Weather Platform.
Runs all collectors to gather weather event data from various sources.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("collect_data")


async def collect_from_all_sources():
    from app.core.database import async_session_factory
    from app.collectors.twitter_collector import twitter_collector
    from app.collectors.web_scraper import web_scraper
    from app.collectors.api_collector import api_collector
    from app.collectors.citizen_report import citizen_report_handler

    logger.info("=" * 60)
    logger.info("Starting data collection cycle")
    logger.info("=" * 60)

    async with async_session_factory() as db:
        total_stored = 0

        logger.info("1. Collecting tweets from Twitter/X...")
        try:
            tweets = await twitter_collector.collect_tweets(max_results=50)
            if tweets:
                count = await twitter_collector.store_collected_tweets(db, tweets)
                total_stored += count
                logger.info(f"   Stored {count} tweets")
            else:
                logger.info("   No tweets collected (using mock data)")
                mock_tweets = twitter_collector._mock_tweets()
                count = await twitter_collector.store_collected_tweets(db, mock_tweets)
                total_stored += count
                logger.info(f"   Stored {count} mock tweets")
        except Exception as e:
            logger.error(f"   Twitter collection failed: {e}")

        logger.info("2. Scraping weather news from Indian news sources...")
        try:
            articles = await web_scraper.scrape_all_sources()
            if articles:
                count = await web_scraper.store_scraped_articles(db, articles)
                total_stored += count
                logger.info(f"   Stored {count} articles")
            else:
                logger.info("   No articles scraped (using mock data)")
                mock_articles = web_scraper._mock_articles()
                count = await web_scraper.store_scraped_articles(db, mock_articles)
                total_stored += count
                logger.info(f"   Stored {count} mock articles")
        except Exception as e:
            logger.error(f"   Web scraping failed: {e}")

        logger.info("3. Fetching data from public APIs...")
        try:
            api_events = await api_collector.fetch_openweather_bulk()
            if api_events:
                count = await api_collector.store_api_events(db, api_events)
                total_stored += count
                logger.info(f"   Stored {count} API events")
            else:
                logger.info("   No API data (API key may not be configured)")
                from app.collectors.api_collector import INDIAN_CITIES_COORDS
                mock_events = [api_collector._mock_openweather(city) for city in list(INDIAN_CITIES_COORDS.keys())[:10]]
                count = await api_collector.store_api_events(db, mock_events)
                total_stored += count
                logger.info(f"   Stored {count} mock API events")
        except Exception as e:
            logger.error(f"   API collection failed: {e}")

        logger.info("4. Processing citizen reports...")
        try:
            mock_reports = citizen_report_handler._mock_citizen_reports()
            count = await citizen_report_handler.store_citizen_reports(db, mock_reports)
            total_stored += count
            logger.info(f"   Stored {count} citizen reports")
        except Exception as e:
            logger.error(f"   Citizen report processing failed: {e}")

        logger.info("=" * 60)
        logger.info(f"Collection cycle complete. Total events stored: {total_stored}")
        logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
        logger.info("=" * 60)

        return total_stored


if __name__ == "__main__":
    asyncio.run(collect_from_all_sources())
