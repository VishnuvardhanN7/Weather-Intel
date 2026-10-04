import sys
import asyncio
from collections import Counter
from sqlalchemy import select

sys.path.insert(0, '.')
from app.core.database import async_session_factory
from app.models.user import User
from app.models.weather_event import WeatherEvent

EXPECTED_COUNTS = {
    "Severe Weather": 15,
    "Rainfall": 15,
    "Flooding": 12,
    "Storms": 12,
    "Heatwave": 12,
    "IMD Updates": 10,
    "Videos": 10,
    "Citizen Reports": 8,
    "Fog": 3,
    "Dust Storm": 3,
}

async def verify_demo_dataset():
    print("==================================================")
    print("ATMOS DEMO STORY DATASET AUDIT")
    print("==================================================")

    async with async_session_factory() as session:
        stmt = select(WeatherEvent).where(WeatherEvent.source_id.like("demo-story-%"))
        result = await session.execute(stmt)
        events = result.scalars().all()

    total_count = len(events)
    source_ids = [e.source_id for e in events]
    unique_ids = set(source_ids)
    duplicate_count = len(source_ids) - len(unique_ids)

    with_title = sum(1 for e in events if e.title and e.title.strip())
    with_desc = sum(1 for e in events if e.description and len(e.description.strip()) > 20)
    with_img = sum(1 for e in events if (e._primary_image_url() or (e.metadata_ or {}).get("image_url")))
    is_demo_count = sum(1 for e in events if (e.metadata_ or {}).get("is_demo") is True)
    is_static_count = sum(1 for e in events if (e.metadata_ or {}).get("is_static") is True)

    category_counts = Counter()
    for e in events:
        cat = (e.metadata_ or {}).get("category", "Uncategorized")
        category_counts[cat] += 1

    print(f"Total demo stories:      {total_count}")
    print(f"Stories with images:    {with_img}")
    print(f"Stories with desc:      {with_desc}")
    print(f"Unique IDs:             {len(unique_ids)}")
    print(f"Duplicate IDs:          {duplicate_count}")
    print(f"is_demo=true count:     {is_demo_count}")
    print(f"is_static=true count:   {is_static_count}")

    print("\nCategory Distribution:")
    all_categories_pass = True
    for cat, expected in EXPECTED_COUNTS.items():
        actual = category_counts.get(cat, 0)
        match = "OK" if actual == expected else f"FAIL (expected {expected})"
        if actual != expected:
            all_categories_pass = False
        print(f"  {cat:<18}: {actual:>2}  [{match}]")

    print("\nAudit Summary:")
    passed = (
        total_count == 100 and
        with_img == 100 and
        with_desc == 100 and
        duplicate_count == 0 and
        is_demo_count == 100 and
        is_static_count == 100 and
        all_categories_pass
    )

    if passed:
        print("\nSTATUS: PASS")
        return True
    else:
        print("\nSTATUS: FAIL")
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_demo_dataset())
    if not success:
        sys.exit(1)
