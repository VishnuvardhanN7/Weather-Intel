import asyncio
import httpx
from bs4 import BeautifulSoup

DIRECT_FEEDS = [
    ("Indian Express India", "https://indianexpress.com/section/india/feed/"),
    ("Indian Express Cities", "https://indianexpress.com/section/cities/mumbai/feed/"),
    ("Times of India Weather", "https://timesofindia.indiatimes.com/rssfeeds/2647163.cms"),
    ("Times of India Environment", "https://timesofindia.indiatimes.com/rssfeeds/2647163.cms"),
    ("NDTV News", "https://feeds.feedburner.com/ndtvnews-top-stories"),
    ("Down To Earth", "https://www.downtoearth.org.in/rss/climate-change"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

async def test_direct_feeds():
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
        for name, url in DIRECT_FEEDS:
            try:
                resp = await client.get(url)
                soup = BeautifulSoup(resp.content, "html.parser")
                items = soup.find_all("item")
                print(f"=== {name} ({len(items)} items) ===")
                for item in items[:3]:
                    title = item.find("title").get_text(strip=True) if item.find("title") else ""
                    link = item.find("link").get_text(strip=True) if item.find("link") else ""
                    
                    # Look for media:content, media:thumbnail, enclosure, or og:image by fetching link
                    img_url = None
                    media = item.find("media:content") or item.find("media:thumbnail")
                    if media and media.get("url"):
                        img_url = media.get("url")
                    
                    if not img_url:
                        enc = item.find("enclosure")
                        if enc and enc.get("url"):
                            img_url = enc.get("url")

                    if not img_url and link and link.startswith("http"):
                        try:
                            art_resp = await client.get(link, timeout=4.0)
                            art_soup = BeautifulSoup(art_resp.content, "html.parser")
                            for meta in art_soup.find_all("meta"):
                                prop = (meta.get("property") or meta.get("name") or "").lower()
                                if prop in ("og:image", "twitter:image", "twitter:image:src"):
                                    cand = meta.get("content")
                                    if cand and cand.startswith("http") and "placeholder" not in cand and "default" not in cand:
                                        img_url = cand
                                        break
                        except Exception:
                            pass

                    print(f"Title: {title[:70]}")
                    print(f"Link:  {link}")
                    print(f"Image: {img_url}")
                    print("-" * 40)
            except Exception as e:
                print(f"[{name}] Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_feeds())
