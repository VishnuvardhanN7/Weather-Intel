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
        res = await db.execute(select(WeatherEvent).where(WeatherEvent.source_id == 'weather_youtube_bK8qng6aMJM'))
        e = res.scalar_one_or_none()
        if e:
            meta = e.metadata_ or {}
            print(f"e.source: {repr(e.source)} ({type(e.source)})")
            print(f"EventSource.YOUTUBE: {repr(EventSource.YOUTUBE)} ({type(EventSource.YOUTUBE)})")
            print(f"e.source == EventSource.YOUTUBE: {e.source == EventSource.YOUTUBE}")
            print(f"meta.get('category'): {meta.get('category')}")

if __name__ == "__main__":
    asyncio.run(main())
