import httpx

try:
    resp = httpx.get("http://localhost:8000/api/stories?per_page=80", timeout=5.0)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    stories = data.get("data", [])
    print(f"Returned stories count: {len(stories)}")
    for i, s in enumerate(stories[:10], 1):
        print(f"[{i}] ID: {s.get('id')} | is_demo: {s.get('is_demo')} | Title: {s.get('title')[:40]} | ImgURL: {s.get('image_url')}")
except Exception as e:
    print(f"Error: {e}")
