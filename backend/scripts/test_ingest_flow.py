import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_factory
from app.services.ingestion_service import run_ingestion
from app.models.weather_event import WeatherEvent
from sqlalchemy import select, func

import pytest

@pytest.mark.asyncio
async def test_ingest():
    async with async_session_factory() as db:
        print("--- Running Ingestion ---")
        res = await run_ingestion(db, ["public_api"], use_sample_data=False)
        print("Ingestion Result:", res)

    print("--- Waiting 3 seconds for streaming worker cycle ---")
    await asyncio.sleep(3)

    async with async_session_factory() as db:
        count_res = await db.execute(select(func.count(WeatherEvent.id)))
        total_count = count_res.scalar()
        print("Total PostgreSQL Events after streaming pipeline:", total_count)

        events_res = await db.execute(select(WeatherEvent).order_by(WeatherEvent.id.desc()).limit(10))
        events = events_res.scalars().all()
        print(f"Latest {len(events)} events in PostgreSQL DB:")
        for e in events:
            print(f"  [{e.id}] {e.title} | City: {e.city} | Status: {e.verification_status} | Alertness: {e.metadata_.get('alertness_score') if e.metadata_ else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(test_ingest())
