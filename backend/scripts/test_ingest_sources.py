import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

RSS_FEEDS = [
    ("IMD District Nowcast", "https://mausam.imd.gov.in/responsive/rss_district_nowcast.php"),
    ("Google News Kerala Rain", "https://news.google.com/rss/search?q=Kerala+heavy+rain+IMD+warning&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News Odisha Weather", "https://news.google.com/rss/search?q=Odisha+thunderstorm+rainfall+IMD&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News Monsoon Withdrawal", "https://news.google.com/rss/search?q=monsoon+withdrawal+India+IMD+2026&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News Delhi Weather", "https://news.google.com/rss/search?q=Delhi+NCR+weather+temperature+fog+IMD&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News Maharashtra Rain", "https://news.google.com/rss/search?q=Maharashtra+rainfall+monsoon+IMD&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News Karnataka Weather", "https://news.google.com/rss/search?q=Bengaluru+Karnataka+heavy+rainfall+IMD&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News Tamil Nadu Monsoon", "https://news.google.com/rss/search?q=Tamil+Nadu+northeast+monsoon+rainfall+IMD&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News Northeast India Rain", "https://news.google.com/rss/search?q=Assam+Arunachal+rainfall+IMD+bulletin&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Times of India Weather", "https://timesofindia.indiatimes.com/rssfeeds/2647163.cms"),
    ("Indian Express India", "https://indianexpress.com/section/india/feed/"),
    ("Down To Earth Climate", "https://www.downtoearth.org.in/rss/climate-change"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

async def check_rss():
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
        for name, url in RSS_FEEDS:
            try:
                resp = await client.get(url)
                soup = BeautifulSoup(resp.content, "html.parser")
                items = soup.find_all("item")
                print(f"[{name}] {len(items)} items returned")
            except Exception as e:
                print(f"[{name}] ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(check_rss())
