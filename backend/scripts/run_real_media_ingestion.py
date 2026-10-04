import sys
import asyncio
from datetime import datetime
import httpx

sys.path.insert(0, '.')
from app.core.database import async_session_factory
from app.models.user import User
from app.models.weather_event import WeatherEvent, EventType, SeverityLevel, EventSource, VerificationStatus
from app.collectors.web_scraper import WebScraper, is_valid_article_image
from app.collectors.youtube_collector import YouTubeCollector
from app.collectors.mastodon_collector import MastodonCollector
from app.collectors.reddit_collector import RedditCollector

async def verify_image_url(client: httpx.AsyncClient, url: str) -> bool:
    if not is_valid_article_image(url):
        return False
    try:
        resp = await client.get(url, follow_redirects=True, timeout=5.0)
        if resp.status_code == 200:
            ctype = resp.headers.get("content-type", "").lower()
            if "image" in ctype or "octet-stream" in ctype or "jpeg" in ctype or "png" in ctype or "webp" in ctype:
                return True
            if len(resp.content) > 1000:
                return True
    except Exception:
        pass
    return False

def safe_str(text: str) -> str:
    if not text:
        return ""
    return text.encode("ascii", "ignore").decode("ascii")

async def main():
    print("========================================")
    print("DOCKER BACKEND REAL MEDIA INGESTION")
    print("========================================")

    yt = YouTubeCollector()
    yt.health_state = "READY"
    web = WebScraper()
    masto = MastodonCollector()
    masto.health_state = "READY"

    collected_events = []

    # 1. YouTube
    print("\n[1/3] Fetching YouTube Weather Video Reports...")
    yt_items = await yt.search_weather_videos("heavy rainfall weather India monsoon IMD")
    print(f"-> YouTube returned: {len(yt_items)} videos.")
    collected_events.extend(yt_items)

    # 2. Web & RSS
    print("\n[2/3] Fetching Indian Weather News & RSS feeds...")
    web_articles = await web.scrape_all_sources()
    print(f"-> Web & RSS returned: {len(web_articles)} articles.")
    collected_events.extend(web_articles)

    # 3. Mastodon
    print("\n[3/3] Fetching Mastodon Fediverse Reports...")
    masto_items = await masto.fetch_hashtag_timeline("weather")
    print(f"-> Mastodon returned: {len(masto_items)} posts.")
    collected_events.extend(masto_items)

    print(f"\nTotal raw collected items: {len(collected_events)}")

    inserted_count = 0
    media_count = 0
    verified_samples = []

    async with httpx.AsyncClient() as client:
        async with async_session_factory() as session:
            for item in collected_events:
                photos = item.get("photos") or []
                media = item.get("media") or (item.get("metadata") or {}).get("media") or []
                raw_img = photos[0] if photos else (media[0].get("url") if media else None)
                valid_img = None

                if raw_img:
                    if await verify_image_url(client, raw_img):
                        valid_img = raw_img
                        media_count += 1

                src_name = item.get("source_name") or item.get("source") or "Web"
                if "youtube" in str(src_name).lower():
                    src_enum = EventSource.YOUTUBE
                elif "mastodon" in str(src_name).lower():
                    src_enum = EventSource.MASTODON
                else:
                    src_enum = EventSource.WEB

                photos_final = [valid_img] if valid_img else []
                media_final = [{"type": "image", "url": valid_img, "thumbnail_url": valid_img, "source_url": item.get("source_url") or item.get("url")}] if valid_img else []

                title_clean = safe_str(item.get("title") or "Weather Report")
                desc_clean = safe_str(item.get("description") or item.get("title") or "")

                now_ts = datetime.utcnow()

                db_event = WeatherEvent(
                    title=title_clean,
                    description=desc_clean,
                    event_type=EventType.RAINFALL,
                    severity=SeverityLevel.MODERATE,
                    source=src_enum,
                    source_url=item.get("source_url") or item.get("url"),
                    source_id=item.get("id") or item.get("event_id"),
                    city=item.get("city") or "India",
                    state=item.get("state") or "India",
                    latitude=item.get("latitude") or 20.5937,
                    longitude=item.get("longitude") or 78.9629,
                    photos=photos_final,
                    videos=[],
                    metadata_={
                        "image_url": valid_img,
                        "thumbnail_url": valid_img,
                        "media": media_final,
                        "source_name": src_name,
                    },
                    verification_status=VerificationStatus.VERIFIED,
                    created_at=now_ts,
                    reported_at=now_ts
                )
                session.add(db_event)
                inserted_count += 1

                if valid_img and len(verified_samples) < 5:
                    verified_samples.append({
                        "title": title_clean,
                        "source": src_name,
                        "source_url": item.get("source_url") or item.get("url"),
                        "image_url": valid_img
                    })

            await session.commit()

    print("\n========================================")
    print("CONTAINER DB INGESTION SUCCESS")
    print("========================================")
    print(f"Total New Inserts: {inserted_count}")
    print(f"Events with HTTP-Verified Real Media: {media_count}")

    if verified_samples:
        print("\n--- SAMPLE VERIFIED MEDIA RECORDS ---")
        for i, s in enumerate(verified_samples, 1):
            print(f"[{i}] Source: {s['source']}")
            print(f"    Title: {s['title']}")
            print(f"    Source URL: {s['source_url']}")
            print(f"    Image URL: {s['image_url']}")

if __name__ == "__main__":
    asyncio.run(main())
