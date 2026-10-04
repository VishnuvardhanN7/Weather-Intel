import httpx

r_list = httpx.get("http://localhost:8000/api/stories?per_page=80")
print("=== API STORIES LIST VERIFICATION ===")
print("Status:", r_list.status_code)
stories = r_list.json().get("data", [])
print("Total stories returned:", len(stories))
real_img_count = sum(1 for s in stories if str(s.get("id", "")).startswith("real_img_story_"))
print("Real image stories count in returned feed:", real_img_count)
print("Top 5 stories in feed:")
for i, s in enumerate(stories[:5], 1):
    print(f"  {i}. [{s.get('id')}] {s.get('title')[:50]}... | Img: {s.get('image_url')}")

r_detail = httpx.get("http://localhost:8000/api/stories/real_img_story_01")
print("\n=== API STORY DETAIL VERIFICATION ===")
print("Status:", r_detail.status_code)
detail = r_detail.json().get("story", {})
print("Detail Title:", detail.get("title"))
print("Detail Image URL:", detail.get("image_url"))
print("Detail Source:", detail.get("source"))
print("Detail Source URL:", detail.get("source_url"))
print("Detail Image Credit:", detail.get("image_credit"))
