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
            sid = str(e.source_id or e.id)
            if sid.startswith("real_img_story_") or sid.startswith("weather_youtube_"):
                p = get_source_priority(e)
                meta = e.metadata_ or {}
                img = meta.get("image_url") or e._primary_image_url()
                print(f"ID: {sid:<35} | Priority: {p} | Source: {e.source} | Img: {img}")

if __name__ == "__main__":
    asyncio.run(main())
