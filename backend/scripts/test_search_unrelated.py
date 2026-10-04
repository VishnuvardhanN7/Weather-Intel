import asyncio
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import async_session_factory
from app.models.user import User
from app.models.weather_event import WeatherEvent
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        res = await db.execute(select(WeatherEvent))
        events = res.scalars().all()
        print(f"Total events in DB: {len(events)}")
        unrelated = []
        for e in events:
            title_lower = e.title.lower()
            meta = e.metadata_ or {}
            if any(k in title_lower for k in ['mars', 'hawaii', 'turtle', 'massachusetts', 'demo']):
                unrelated.append((e.id, e.source_id, e.title, meta.get("is_demo")))
        print(f"Found {len(unrelated)} matching items:")
        for u in unrelated:
            print(f"ID: {u[0]} | source_id: {u[1]} | is_demo: {u[3]} | Title: {u[2]}")

if __name__ == "__main__":
    asyncio.run(main())
