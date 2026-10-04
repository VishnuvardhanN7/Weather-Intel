import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

TEST_URLS = [
    "https://news.google.com/rss/search?q=Kerala+heavy+rain+IMD+warning&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Odisha+thunderstorm+rainfall+IMD&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=monsoon+withdrawal+India+IMD+2026&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Delhi+NCR+weather+temperature+fog+IMD&hl=en-IN&gl=IN&ceid=IN:en",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

async def test_extract():
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
        for rss_url in TEST_URLS:
            resp = await client.get(rss_url)
            soup = BeautifulSoup(resp.content, "html.parser")
            items = soup.find_all("item")
            count = 0
            for item in items[:5]:
                title = item.find("title").get_text(strip=True) if item.find("title") else ""
                link = item.find("link").next_sibling if item.find("link") else None
                if not link:
                    link_el = item.find("link")
                    link = link_el.get_text(strip=True) if link_el else ""
                
                print(f"Title: {title}")
                print(f"Link: {link}")
                
                # Fetch actual page if link
                if link and str(link).startswith("http"):
                    try:
                        art_resp = await client.get(str(link), timeout=5.0)
                        art_soup = BeautifulSoup(art_resp.content, "html.parser")
                        og_img = None
                        for meta in art_soup.find_all("meta"):
                            prop = (meta.get("property") or meta.get("name") or "").lower()
                            if prop in ("og:image", "twitter:image", "twitter:image:src", "og:image:secure_url"):
                                content = meta.get("content")
                                if content and content.startswith("http"):
                                    og_img = content
                                    break
                        print(f"-> Extracted og:image: {og_img}")
                        if og_img:
                            # Verify image accessibility
                            img_resp = await client.head(og_img, timeout=5.0)
                            print(f"   Image HTTP Status: {img_resp.status_code}, ctype: {img_resp.headers.get('content-type')}")
                    except Exception as e:
                        print(f"-> Failed to fetch article: {e}")
                print("-" * 50)
                count += 1
                if count >= 2:
                    break

if __name__ == "__main__":
    asyncio.run(test_extract())
