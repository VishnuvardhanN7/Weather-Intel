import asyncio
import httpx

urls = [
    "https://images.unsplash.com/photo-1519692933481-e162a57d6721?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1527482797697-8795b05a13fe?auto=format&fit=crop&w=1200&q=80",
    "https://images.indianexpress.com/2026/10/weather.jpg",
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1501999635878-71cb5379c2d4?auto=format&fit=crop&w=1200&q=80"
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

async def test():
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for u in urls:
            try:
                r = await client.get(u)
                print(f"{r.status_code} | {r.headers.get('content-type')} | {u}")
            except Exception as e:
                print(f"ERROR: {e} | {u}")

if __name__ == "__main__":
    asyncio.run(test())
