import asyncio
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import async_session_factory
from app.models.user import User
from app.models.weather_event import WeatherEvent
from app.api.stories import get_source_priority
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        res = await db.execute(select(WeatherEvent))
        events = res.scalars().all()
        for e in events:
            if e.source_id and ('real_img_' in e.source_id or 'weather_youtube_' in e.source_id):
                print(f"source_id: {e.source_id:<35} | priority: {get_source_priority(e)} | source: {e.source}")

if __name__ == "__main__":
    asyncio.run(main())
