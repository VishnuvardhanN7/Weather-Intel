"""
Data Quality Score — a separate score from classification confidence,
verification, severity, or priority.

Measures information completeness:
  - location present (city/lat-lng)
  - timestamp present
  - source metadata present
  - description length/quality
  - media availability
  - valid coordinates
  - not a duplicate
"""

DATA_QUALITY_VERSION = "data-quality-v1"

COMPONENTS = {
    "location": 25,
    "timestamp": 15,
    "source_metadata": 15,
    "description_quality": 20,
    "media": 10,
    "valid_coordinates": 10,
    "not_duplicate": 5,
}


def compute_data_quality(
    city=None,
    state=None,
    latitude=None,
    longitude=None,
    reported_at=None,
    source=None,
    source_url=None,
    description="",
    photos=None,
    videos=None,
    duplicate_of_id=None,
) -> dict:
    scores = {}

    # Location (25)
    loc = 0
    if city:
        loc += 15
    if state:
        loc += 5
    if city and state:
        loc += 5
    elif city:
        loc += 0
    scores["location"] = min(loc, 25)

    # Timestamp (15)
    scores["timestamp"] = 15 if reported_at else 0

    # Source metadata (15)
    src = 0
    if source:
        src += 7
    if source_url:
        src += 8
    scores["source_metadata"] = min(src, 15)

    # Description quality (20)
    desc_len = len(description or "")
    if desc_len >= 200:
        scores["description_quality"] = 20
    elif desc_len >= 100:
        scores["description_quality"] = 16
    elif desc_len >= 50:
        scores["description_quality"] = 12
    elif desc_len >= 20:
        scores["description_quality"] = 8
    elif desc_len > 0:
        scores["description_quality"] = 4
    else:
        scores["description_quality"] = 0

    # Media (10)
    media_count = len(photos or []) + len(videos or [])
    scores["media"] = min(media_count * 5, 10)

    # Valid coordinates (10)
    coords_valid = None not in (latitude, longitude) and latitude is not None and longitude is not None
    scores["valid_coordinates"] = 10 if coords_valid else (4 if city else 0)

    # Not duplicate (5)
    scores["not_duplicate"] = 5 if not duplicate_of_id else 2

    total = round(sum(scores.values()), 1)

    if total >= 80:
        quality = "EXCELLENT"
    elif total >= 60:
        quality = "GOOD"
    elif total >= 40:
        quality = "FAIR"
    else:
        quality = "POOR"

    return {
        "data_quality_score": total,
        "data_quality": quality,
        "components": scores,
        "version": DATA_QUALITY_VERSION,
    }