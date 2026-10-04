import sys
import asyncio
import os
import httpx
from datetime import datetime

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import async_session_factory
from app.models.user import User
from app.models.weather_event import WeatherEvent, EventSource
from sqlalchemy import select, func, or_

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

async def verify_image_url_http(client: httpx.AsyncClient, url: str) -> bool:
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return False
    try:
        resp = await client.head(url, follow_redirects=True, timeout=8.0)
        if resp.status_code == 200:
            ctype = resp.headers.get("content-type", "").lower()
            if "image" in ctype or "jpeg" in ctype or "png" in ctype or "webp" in ctype:
                return True
        resp_get = await client.get(url, follow_redirects=True, timeout=8.0)
        if resp_get.status_code == 200:
            ctype = resp_get.headers.get("content-type", "").lower()
            if "image" in ctype or "jpeg" in ctype or "png" in ctype or "webp" in ctype or len(resp_get.content) > 1000:
                return True
    except Exception:
        pass
    return False

async def main():
    print("==================================================")
    print("REAL IMAGE STORIES VERIFICATION")
    print("==================================================")

    async with async_session_factory() as session:
        # Fetch 50 real image stories by source_id prefix real_img_story_
        stmt = select(WeatherEvent).where(WeatherEvent.source_id.like("real_img_story_%"))
        res = await session.execute(stmt)
        real_stories = res.scalars().all()

        total = len(real_stories)
        with_image_url = 0
        with_source_url = 0
        with_source = 0
        with_title = 0
        with_description = 0
        source_ids = set()
        titles = set()
        broken_images = 0
        duplicate_count = 0

        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            for s in real_stories:
                img_url = s._primary_image_url()
                meta = s.metadata_ or {}
                if not img_url:
                    img_url = meta.get("image_url")

                if img_url:
                    with_image_url += 1
                    is_valid = await verify_image_url_http(client, img_url)
                    if not is_valid:
                        broken_images += 1
                else:
                    broken_images += 1

                if s.source_url:
                    with_source_url += 1
                
                src_val = meta.get("source_name") or (s.source.value if hasattr(s.source, "value") else str(s.source))
                if src_val:
                    with_source += 1

                if s.title:
                    with_title += 1
                    if s.title in titles:
                        duplicate_count += 1
                    titles.add(s.title)

                if s.description and len(s.description.strip()) > 20:
                    with_description += 1

                if s.source_id:
                    source_ids.add(s.source_id)

        # Check Youtube videos retained
        yt_stmt = select(func.count(WeatherEvent.id)).where(WeatherEvent.source == EventSource.YOUTUBE)
        yt_res = await session.execute(yt_stmt)
        yt_count = yt_res.scalar() or 0

        print(f"\nREAL IMAGE STORIES")
        print(f"------------------")
        print(f"Total: {total}")
        print(f"With image_url: {with_image_url}")
        print(f"With source_url: {with_source_url}")
        print(f"With source: {with_source}")
        print(f"With title: {with_title}")
        print(f"With description: {with_description}")
        print(f"Unique source IDs: {len(source_ids)}")
        print(f"\nBroken image URLs: {broken_images}")
        print(f"Duplicate stories: {duplicate_count}")
        print(f"Retained YouTube Video Stories: {yt_count}")

        if (
            total == 50
            and with_image_url == 50
            and with_source_url == 50
            and with_source == 50
            and with_title == 50
            and with_description == 50
            and len(source_ids) == 50
            and broken_images == 0
            and duplicate_count == 0
            and yt_count > 0
        ):
            print("\nSTATUS: PASS")
        else:
            print("\nSTATUS: FAIL")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
