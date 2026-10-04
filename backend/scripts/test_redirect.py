import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

TEST_ARTICLES = [
    ("The Hindu", "https://news.google.com/rss/articles/CBMiwAFBVV95cUxQUnZLem9WOGpFSkVheFhON3lhZGF2UEx3bDEzcW52dEVwVXNwV1BtYXRzQy04TS15NUEzd0JCemRNMnhiRkhvc19uVlVqclU1ZFdTZWVpMFpGc3VRQ0pRYnRtd2VSbC00bEdpTmxodHhjS25iWW1mNS03eHhtMEhvSjRZMFVETTRaY2JDLW9QZU91S3M5UkhreklvdEVmRFlUbFVfZ0xfS2kyWmx1YVJ4TE1jMzdSTXB6LWI3NWN2dEbSAccBQVVfeXFMTS1VSVNTZUNaNGpCUGl4bTdNS05IbE03UkgtNW1CaGtPSkpfN21zQlRra3VxUk5ROXRtNlVSWW9ZbjhTbkNqWnJacGQwRlE5UncwcTV3dVdzMmlFd0hmM184VEFoamJaZkJ3VlhJbGFmNUlrNG5iR3FHU094dmlGUWhRMHdvSUZqUmhIRUJiOHhzRms2QldPZ09mZklCV0d1OWFER3h6NllaS19QVDZlNktDLW95dm1meWR4Q19uYldsNFVNNXl0QQ?oc=5"),
    ("Indian Express", "https://news.google.com/rss/articles/CBMiugFBVV95cUxQNjJSM2FCS3pFS0Q4WFNwZzUxeEQ0V1hmVlJHRTFITVI1U1I2LXVUNnRKUTBUY21vZDB2YjBiWWlvbUxnaHVhZjlJUGNJQXp1M3MwSUg2SEVnVHZZd3NlSTAyb0EwdkdSUVhfUU5NOUttcnpxdmlkWDdLdXJmeUFuZ1NVTllkaEcyZlhLVkpWYVVTUFVYNVdyeUxweDR4WlNWRlJRMDdLNXdjQUH0qgFAVV95cUxOcWUyU19hcFVsSjVpRlUzbm5KSmZmdldnUGFZUjh0Q1NMS3JPbms5R09GRlNob2x5TVpZM1FybWs5bkpSRXNyMFhZUXBFU2FtQ0thbjZjbnNnWjR2ZUExTHh2YVVhM2pneVNoaHliUjNYM1NYOHVvSW82MmQwM0hYRE5oaTNLS1RQOEF6NWhYRWk5MG9nOF9jUjNQaWZ4eW9NS0R3bzFLVFVTeDVEaXdIVi1ERnYxc1VRLXkwWGVWNFVF?oc=5")
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

async def test_redirect():
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
        for name, url in TEST_ARTICLES:
            try:
                resp = await client.get(url)
                print(f"[{name}] Final URL: {resp.url}")
                soup = BeautifulSoup(resp.content, "html.parser")
                og_img = None
                for meta in soup.find_all("meta"):
                    prop = (meta.get("property") or meta.get("name") or "").lower()
                    if prop in ("og:image", "twitter:image", "twitter:image:src"):
                        og_img = meta.get("content")
                        if og_img:
                            break
                print(f"[{name}] Extracted Image: {og_img}")
            except Exception as e:
                print(f"[{name}] Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_redirect())
