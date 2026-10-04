import asyncio
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import async_session_factory
from app.models.user import User
from app.models.weather_event import WeatherEvent
from app.api.stories import format_story_response, get_source_priority
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        res = await db.execute(select(WeatherEvent).order_by(WeatherEvent.reported_at.desc()).limit(200))
        events = res.scalars().all()
        sorted_events = sorted(events, key=lambda e: (get_source_priority(e), - (e.reported_at.timestamp() if e.reported_at else 0)))
        formatted = [format_story_response(e) for e in sorted_events]
        print(f"Total formatted stories: {len(formatted)}")
        for i, s in enumerate(formatted[:20], 1):
            print(f"[{i}] ID: {s['id']} | is_demo: {s['is_demo']} | is_video: {s['is_video']} | Title: {s['title'][:50]} | ImgURL: {s['image_url']}")

if __name__ == "__main__":
    asyncio.run(main())
