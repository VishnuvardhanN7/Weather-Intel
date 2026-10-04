import asyncio
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import async_session_factory
from app.models.user import User
from app.models.weather_event import WeatherEvent
from app.api.stories import get_source_priority, format_story_response
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        res = await db.execute(select(WeatherEvent))
        events = res.scalars().all()
        sorted_events = sorted(events, key=lambda e: (get_source_priority(e), - (e.reported_at.timestamp() if e.reported_at else 0)))
        print(f"Total events: {len(events)}")
        for i, e in enumerate(sorted_events[:15], 1):
            s = format_story_response(e)
            print(f"[{i}] ID: {s['id']} | is_video: {s['is_video']} | Priority: {get_source_priority(e)} | Title: {s['title'][:40]}")

if __name__ == "__main__":
    asyncio.run(main())
