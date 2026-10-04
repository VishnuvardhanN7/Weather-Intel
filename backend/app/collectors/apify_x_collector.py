import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from apify_client import ApifyClientAsync

from app.core.config import settings
from app.models.weather_event import EventSource
from app.services.weather_service import weather_service


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Indian cities and states
# ---------------------------------------------------------

INDIAN_STATES_AND_CITIES = {
    "mumbai": ("Mumbai", "Maharashtra"),
    "delhi": ("New Delhi", "Delhi"),
    "bangalore": ("Bengaluru", "Karnataka"),
    "bengaluru": ("Bengaluru", "Karnataka"),
    "chennai": ("Chennai", "Tamil Nadu"),
    "kolkata": ("Kolkata", "West Bengal"),
    "hyderabad": ("Hyderabad", "Telangana"),
    "pune": ("Pune", "Maharashtra"),
    "ahmedabad": ("Ahmedabad", "Gujarat"),
    "jaipur": ("Jaipur", "Rajasthan"),
    "lucknow": ("Lucknow", "Uttar Pradesh"),
    "bhopal": ("Bhopal", "Madhya Pradesh"),
    "patna": ("Patna", "Bihar"),
    "guwahati": ("Guwahati", "Assam"),
    "shimla": ("Shimla", "Himachal Pradesh"),
    "dehradun": ("Dehradun", "Uttarakhand"),
    "ranchi": ("Ranchi", "Jharkhand"),
    "bhubaneswar": ("Bhubaneswar", "Odisha"),
    "kochi": ("Kochi", "Kerala"),
    "thiruvananthapuram": (
        "Thiruvananthapuram",
        "Kerala",
    ),
    "coimbatore": ("Coimbatore", "Tamil Nadu"),
    "visakhapatnam": (
        "Visakhapatnam",
        "Andhra Pradesh",
    ),
    "vizag": ("Visakhapatnam", "Andhra Pradesh"),
    "nagpur": ("Nagpur", "Maharashtra"),
    "indore": ("Indore", "Madhya Pradesh"),
    "chandigarh": ("Chandigarh", "Chandigarh"),
    "imphal": ("Imphal", "Manipur"),
    "shillong": ("Shillong", "Meghalaya"),
    "agartala": ("Agartala", "Tripura"),
    "aizawl": ("Aizawl", "Mizoram"),
    "kohima": ("Kohima", "Nagaland"),
    "gangtok": ("Gangtok", "Sikkim"),
    "panaji": ("Panaji", "Goa"),
    "srinagar": ("Srinagar", "Jammu and Kashmir"),
    "jammu": ("Jammu", "Jammu and Kashmir"),
    "ludhiana": ("Ludhiana", "Punjab"),
    "amritsar": ("Amritsar", "Punjab"),
    "varanasi": ("Varanasi", "Uttar Pradesh"),
    "agra": ("Agra", "Uttar Pradesh"),
    "dimapur": ("Dimapur", "Nagaland"),
    "meerut": ("Meerut", "Uttar Pradesh"),
    "prayagraj": ("Prayagraj", "Uttar Pradesh"),
    "kanpur": ("Kanpur", "Uttar Pradesh"),
    "nashik": ("Nashik", "Maharashtra"),
    "surat": ("Surat", "Gujarat"),
    "rajkot": ("Rajkot", "Gujarat"),
    "vadodara": ("Vadodara", "Gujarat"),
    "jamshedpur": ("Jamshedpur", "Jharkhand"),
    "dhanbad": ("Dhanbad", "Jharkhand"),
    "warangal": ("Warangal", "Telangana"),
    "madurai": ("Madurai", "Tamil Nadu"),
    "tiruchirappalli": (
        "Tiruchirappalli",
        "Tamil Nadu",
    ),
}


# ---------------------------------------------------------
# Weather relevance keywords
# ---------------------------------------------------------

WEATHER_KEYWORDS = {
    "weather",
    "rain",
    "rainfall",
    "monsoon",
    "flood",
    "flooding",
    "cyclone",
    "storm",
    "thunderstorm",
    "heatwave",
    "heat wave",
    "cold wave",
    "fog",
    "wind",
    "winds",
    "weather alert",
    "weather warning",
    "forecast",
    "imd",
    "meteorological",
    "heavy rain",
    "hail",
    "landslide",
}


class ApifyXCollector:
    """
    Collect public X/Twitter weather posts through Apify.

    Apify is the collection mechanism.
    The original event source remains EventSource.TWITTER.
    """

    def __init__(self):
        self.client: Optional[ApifyClientAsync] = None

        if settings.APIFY_API_TOKEN:
            self.client = ApifyClientAsync(
                settings.APIFY_API_TOKEN
            )

            logger.info(
                "Apify client initialized successfully"
            )

        else:
            logger.warning(
                "APIFY_API_TOKEN is not configured"
            )

    # ---------------------------------------------------------
    # Location extraction
    # ---------------------------------------------------------

    def _extract_location(
        self,
        text: str,
        user_location: str = "",
    ) -> Dict:

        combined = (
            f"{text} {user_location}"
        ).lower()

        for city_key, (
            city,
            state,
        ) in INDIAN_STATES_AND_CITIES.items():

            if city_key in combined:

                from app.utils.geolocation import (
                    get_city_coordinates,
                )

                coords = get_city_coordinates(city)

                return {
                    "city": city,
                    "state": state,
                    "latitude": coords.get(
                        "latitude"
                    ),
                    "longitude": coords.get(
                        "longitude"
                    ),
                }

        return {
            "city": None,
            "state": None,
            "latitude": None,
            "longitude": None,
        }

    # ---------------------------------------------------------
    # Weather relevance
    # ---------------------------------------------------------

    def _is_weather_relevant(
        self,
        record: dict,
    ) -> bool:

        text = str(
            record.get("text", "")
        ).lower()

        entities = record.get(
            "entities",
            {},
        ) or {}

        hashtags = entities.get(
            "hashtags",
            []
        ) or []

        hashtag_text = " ".join(
            str(item.get("text", ""))
            for item in hashtags
            if isinstance(item, dict)
        ).lower()

        combined = (
            f"{text} {hashtag_text}"
        )

        return any(
            keyword in combined
            for keyword in WEATHER_KEYWORDS
        )

    # ---------------------------------------------------------
    # Date/time parsing
    # ---------------------------------------------------------

    def _parse_datetime(
        self,
        value: Optional[str],
    ) -> datetime:

        if not value:
            return datetime.utcnow()

        try:

            parsed = datetime.strptime(
                value,
                "%a %b %d %H:%M:%S %z %Y",
            )

            return (
                parsed
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        except ValueError:

            try:

                parsed = datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00",
                    )
                )

                if parsed.tzinfo:
                    parsed = (
                        parsed
                        .astimezone(timezone.utc)
                        .replace(tzinfo=None)
                    )

                return parsed

            except ValueError:

                logger.warning(
                    "Could not parse tweet timestamp: %s",
                    value,
                )

                return datetime.utcnow()

    # ---------------------------------------------------------
    # Media extraction
    # ---------------------------------------------------------

    def _extract_media(
        self,
        record: dict,
    ):

        photos = []
        videos = []

        media = record.get(
            "media",
            []
        ) or []

        # -----------------------------------------------------
        # Apify format:
        #
        # "media": {
        #     "photo": [...],
        #     "video": [...]
        # }
        # -----------------------------------------------------

        if isinstance(media, dict):

            # -------------------------
            # Photos
            # -------------------------

            photo_items = media.get(
                "photo",
                []
            ) or []

            if isinstance(
                photo_items,
                dict,
            ):
                photo_items = [
                    photo_items
                ]

            if isinstance(
                photo_items,
                list,
            ):

                for item in photo_items:

                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    url = item.get(
                        "media_url_https"
                    )

                    if url:
                        photos.append(url)

            # -------------------------
            # Videos
            # -------------------------

            video_items = media.get(
                "video",
                []
            ) or []

            if isinstance(
                video_items,
                dict,
            ):
                video_items = [
                    video_items
                ]

            if isinstance(
                video_items,
                list,
            ):

                for item in video_items:

                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    variants = item.get(
                        "variants",
                        []
                    ) or []

                    mp4_urls = []

                    if isinstance(
                        variants,
                        list,
                    ):

                        for variant in variants:

                            if not isinstance(
                                variant,
                                dict,
                            ):
                                continue

                            if (
                                variant.get(
                                    "content_type"
                                )
                                == "video/mp4"
                                and variant.get(
                                    "url"
                                )
                            ):
                                mp4_urls.append(
                                    variant["url"]
                                )

                    if mp4_urls:

                        videos.append(
                            mp4_urls[0]
                        )

                    else:

                        thumbnail = item.get(
                            "media_url_https"
                        )

                        if thumbnail:
                            videos.append(
                                thumbnail
                            )

        # -----------------------------------------------------
        # Fallback format:
        #
        # "media": [
        #     {
        #         "type": "photo",
        #         ...
        #     }
        # ]
        # -----------------------------------------------------

        elif isinstance(
            media,
            list,
        ):

            for item in media:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                media_type = item.get(
                    "type"
                )

                # -------------------------
                # Photo
                # -------------------------

                if media_type == "photo":

                    url = item.get(
                        "media_url_https"
                    )

                    if url:
                        photos.append(url)

                # -------------------------
                # Video
                # -------------------------

                elif media_type == "video":

                    video_info = item.get(
                        "video_info",
                        {}
                    ) or {}

                    variants = video_info.get(
                        "variants",
                        []
                    ) or []

                    mp4_urls = [
                        variant.get("url")
                        for variant in variants
                        if isinstance(
                            variant,
                            dict,
                        )
                        and variant.get(
                            "content_type"
                        )
                        == "video/mp4"
                        and variant.get("url")
                    ]

                    if mp4_urls:

                        videos.append(
                            mp4_urls[0]
                        )

                    elif item.get(
                        "media_url_https"
                    ):

                        videos.append(
                            item[
                                "media_url_https"
                            ]
                        )

        return photos, videos

    # ---------------------------------------------------------
    # Normalize Apify record
    # ---------------------------------------------------------

    def _normalize_record(
        self,
        record: dict,
        search_query: str,
    ) -> Optional[dict]:

        tweet_id = str(
            record.get(
                "tweet_id",
                "",
            )
        ).strip()

        text = str(
            record.get(
                "text",
                "",
            )
        ).strip()

        screen_name = str(
            record.get(
                "screen_name",
                "",
            )
        ).strip()

        if not tweet_id or not text:
            return None

        # Ignore obviously unrelated posts.
        if not self._is_weather_relevant(
            record
        ):

            logger.debug(
                "Skipping non-weather X post: %s",
                text[:100],
            )

            return None

        user_info = (
            record.get(
                "user_info",
                {}
            )
            or {}
        )

        user_location = str(
            user_info.get(
                "location",
                "",
            )
        ).strip()

        location = self._extract_location(
            text,
            user_location,
        )

        photos, videos = (
            self._extract_media(
                record
            )
        )

        # -----------------------------------------------------
        # Hashtags
        # -----------------------------------------------------

        entities = (
            record.get(
                "entities",
                {}
            )
            or {}
        )

        hashtag_items = (
            entities.get(
                "hashtags",
                []
            )
            or []
        )

        hashtags = [
            item.get("text")
            for item in hashtag_items
            if isinstance(
                item,
                dict,
            )
            and item.get("text")
        ]

        # -----------------------------------------------------
        # Correct X URL
        # -----------------------------------------------------

        if screen_name:

            source_url = (
                f"https://x.com/"
                f"{screen_name}/status/"
                f"{tweet_id}"
            )

        else:

            source_url = (
                f"https://x.com/i/status/"
                f"{tweet_id}"
            )

        # -----------------------------------------------------
        # Metadata
        # -----------------------------------------------------

        metadata = {
            "collector": "apify",
            "actor": (
                settings.APIFY_X_ACTOR_ID
            ),
            "search_query": search_query,

            # X post information
            "tweet_id": tweet_id,
            "screen_name": screen_name,
            "language": record.get(
                "lang"
            ),

            # Engagement
            "favorites": record.get(
                "favorites",
                0,
            ),
            "retweets": record.get(
                "retweets",
                0,
            ),
            "replies": record.get(
                "replies",
                0,
            ),
            "quotes": record.get(
                "quotes",
                0,
            ),
            "bookmarks": record.get(
                "bookmarks",
                0,
            ),
            "views": record.get(
                "views",
                0,
            ),

            # Author information
            "author_name": user_info.get(
                "name"
            ),
            "author_description": user_info.get(
                "description"
            ),
            "author_location": user_location,
            "author_followers": user_info.get(
                "followers_count",
                0,
            ),
            "author_verified": user_info.get(
                "verified",
                False,
            ),
            "author_verified_type": user_info.get(
                "verified_type"
            ),

            # Hashtags
            "hashtags": hashtags,
        }

        # -----------------------------------------------------
        # Normalized event
        # -----------------------------------------------------

        return {
            "source_id": tweet_id,

            "title": text[:200],

            "description": text,

            "source_url": source_url,

            "city": location.get(
                "city"
            ),

            "state": location.get(
                "state"
            ),

            "latitude": location.get(
                "latitude"
            ),

            "longitude": location.get(
                "longitude"
            ),

            "photos": photos,

            "videos": videos,

            "metadata": metadata,

            "reported_at": (
                self._parse_datetime(
                    record.get(
                        "created_at"
                    )
                )
            ),
        }

    # ---------------------------------------------------------
    # Collect posts from Apify
    # ---------------------------------------------------------

    async def collect_posts(
        self,
        queries: Optional[List[str]] = None,
        max_pages: int = 1,
    ) -> List[dict]:

        if not self.client:

            logger.error(
                "Apify client unavailable. "
                "Check APIFY_API_TOKEN."
            )

            return []

        queries = queries or [
            "#IMD weather",
            "#IMD rainfall",
            "#IMD rain",
            "#IMD monsoon",
            "#IMD flood",
        ]

        collected = []

        seen_ids = set()

        for query in queries:

            try:

                logger.info(
                    "Running Apify X search: %s",
                    query,
                )

                actor_input = {
                    "query": query,
                    "section": "latest",
                    "maxPages": max_pages,
                }

                run = await self.client.actor(
                    settings.APIFY_X_ACTOR_ID
                ).call(
                    run_input=actor_input
                )

                dataset_id = run.get(
                    "defaultDatasetId"
                )

                if not dataset_id:

                    logger.warning(
                        "No dataset returned "
                        "for query: %s",
                        query,
                    )

                    continue

                dataset_items = (
                    await self.client
                    .dataset(dataset_id)
                    .list_items()
                )

                items = (
                    dataset_items.items
                )

                logger.info(
                    "Apify returned %d records "
                    "for '%s'",
                    len(items),
                    query,
                )

                for record in items:

                    if not isinstance(
                        record,
                        dict,
                    ):
                        continue

                    tweet_id = str(
                        record.get(
                            "tweet_id",
                            "",
                        )
                    ).strip()

                    if (
                        not tweet_id
                        or tweet_id in seen_ids
                    ):
                        continue

                    normalized = (
                        self._normalize_record(
                            record,
                            query,
                        )
                    )

                    if normalized:

                        seen_ids.add(
                            tweet_id
                        )

                        collected.append(
                            normalized
                        )

            except Exception as exc:

                logger.exception(
                    "Apify collection failed "
                    "for query '%s': %s",
                    query,
                    exc,
                )

        logger.info(
            "Apify X collection completed: "
            "%d weather posts",
            len(collected),
        )

        return collected

    # ---------------------------------------------------------
    # Store posts in database
    # ---------------------------------------------------------

    async def store_posts(
        self,
        db,
        posts: List[dict],
    ) -> int:

        stored_count = 0

        for post in posts:

            try:

                await weather_service.ingest_event(
                    db=db,
                    title=post["title"],
                    description=post[
                        "description"
                    ],
                    source=EventSource.TWITTER,
                    source_url=post.get(
                        "source_url"
                    ),
                    source_id=post.get(
                        "source_id"
                    ),
                    city=post.get(
                        "city"
                    ),
                    state=post.get(
                        "state"
                    ),
                    latitude=post.get(
                        "latitude"
                    ),
                    longitude=post.get(
                        "longitude"
                    ),
                    photos=post.get(
                        "photos",
                        [],
                    ),
                    videos=post.get(
                        "videos",
                        [],
                    ),
                    metadata=post.get(
                        "metadata",
                        {},
                    ),
                    reported_at=post.get(
                        "reported_at"
                    ),
                )

                stored_count += 1

            except Exception as exc:

                logger.exception(
                    "Failed to store Apify X "
                    "post %s: %s",
                    post.get(
                        "source_id"
                    ),
                    exc,
                )

        logger.info(
            "Stored %d Apify X "
            "weather posts",
            stored_count,
        )

        return stored_count


# ---------------------------------------------------------
# Singleton collector
# ---------------------------------------------------------

apify_x_collector = ApifyXCollector()