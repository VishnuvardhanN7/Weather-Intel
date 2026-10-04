import asyncio
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import async_session_factory
from app.models.user import User
from app.models.weather_event import WeatherEvent, EventSource
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        res = await db.execute(select(WeatherEvent).where(WeatherEvent.source == EventSource.YOUTUBE))
        events = res.scalars().all()
        print(f"Total EventSource.YOUTUBE events: {len(events)}")
        for e in events[:5]:
            meta = e.metadata_ or {}
            print(f"ID: {e.id} | source_id: {e.source_id} | source: {repr(e.source)} | meta_category: {meta.get('category')}")

if __name__ == "__main__":
    asyncio.run(main())
