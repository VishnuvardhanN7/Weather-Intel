import logging
from typing import List, Dict, Optional
from datetime import datetime

import tweepy
from app.core.config import settings
from app.services.weather_service import weather_service
from app.models.weather_event import EventSource

logger = logging.getLogger(__name__)

INDIAN_WEATHER_HASHTAGS = [
    "#IMD", "#Weather", "#IndiaWeather", "#Monsoon", "#Rainfall",
    "#Flood", "#Cyclone", "#Storm", "#Delhi", "#Mumbai",
    "#Chennai", "#Kolkata", "#WeatherAlert", "#Thunderstorm",
    "#HeavyRain", "#Heatwave", "#ColdWave", "#FogAlert",
    "#IndiaWeatherAlert", "#IndianWeather",
]

INDIAN_STATES_AND_CITIES = {
    "mumbai": ("Mumbai", "Maharashtra"),
    "delhi": ("New Delhi", "Delhi"),
    "bangalore": ("Bengaluru", "Karnataka"),
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
    "thiruvananthapuram": ("Thiruvananthapuram", "Kerala"),
    "coimbatore": ("Coimbatore", "Tamil Nadu"),
    "visakhapatnam": ("Visakhapatnam", "Andhra Pradesh"),
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
    "nagaland": ("Dimapur", "Nagaland"),
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
    "tiruchirappalli": ("Tiruchirappalli", "Tamil Nadu"),
}


class TwitterCollector:
    def __init__(self):
        self.client = None
        self._setup_client()

    def _setup_client(self):
        if settings.TWITTER_BEARER_TOKEN:
            try:
                self.client = tweepy.Client(
                    bearer_token=settings.TWITTER_BEARER_TOKEN,
                    wait_on_rate_limit=True,
                )
                logger.info("Twitter client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter client: {e}")
        else:
            logger.warning("Twitter Bearer Token not configured, collector will use mock data")

    def _extract_location_from_text(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for city_key in INDIAN_STATES_AND_CITIES:
            if city_key in text_lower:
                return city_key
        return None

    def _resolve_location(self, city_key: str) -> Dict:
        if city_key in INDIAN_STATES_AND_CITIES:
            city, state = INDIAN_STATES_AND_CITIES[city_key]
            from app.utils.geolocation import get_city_coordinates
            coords = get_city_coordinates(city)
            return {
                "city": city,
                "state": state,
                "latitude": coords.get("latitude"),
                "longitude": coords.get("longitude"),
            }
        return {"city": None, "state": None, "latitude": None, "longitude": None}

    async def collect_tweets(self, hashtags: Optional[List[str]] = None, max_results: int = 100) -> List[dict]:
        if not self.client:
            return self._mock_tweets()

        tags = hashtags or INDIAN_WEATHER_HASHTAGS
        collected = []

        for tag in tags:
            try:
                query = f"{tag} (weather OR rain OR storm OR flood OR cyclone OR IMD) lang:en -is:retweet"
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(max_results, 100),
                    tweet_fields=["created_at", "geo", "context_annotations", "public_metrics", "author_id"],
                    user_fields=["username", "location"],
                    expansions=["author_id"],
                )
                if response.data:
                    for tweet in response.data:
                        location_key = self._extract_location_from_text(tweet.text)
                        location = self._resolve_location(location_key) if location_key else {}

                        metrics = tweet.public_metrics or {}
                        collected.append({
                            "source_id": str(tweet.id),
                            "title": tweet.text[:200],
                            "description": tweet.text,
                            "source_url": f"https://twitter.com/i/status/{tweet.id}",
                            "city": location.get("city"),
                            "state": location.get("state"),
                            "latitude": location.get("latitude"),
                            "longitude": location.get("longitude"),
                            "metadata": {
                                "retweet_count": metrics.get("retweet_count", 0),
                                "like_count": metrics.get("like_count", 0),
                                "reply_count": metrics.get("reply_count", 0),
                                "author_id": str(tweet.author_id),
                                "hashtag": tag,
                            },
                            "reported_at": tweet.created_at.isoformat() if tweet.created_at else datetime.utcnow().isoformat(),
                        })
                        if len(collected) >= max_results:
                            break
            except Exception as e:
                logger.error(f"Error collecting tweets for hashtag {tag}: {e}")
                continue

        logger.info(f"Collected {len(collected)} tweets")
        return collected

    async def store_collected_tweets(self, db, tweets: List[dict]):
        stored_count = 0
        for tweet in tweets:
            try:
                await weather_service.ingest_event(
                    db=db,
                    title=tweet["title"],
                    description=tweet["description"],
                    source=EventSource.TWITTER,
                    source_url=tweet.get("source_url"),
                    source_id=tweet.get("source_id"),
                    city=tweet.get("city"),
                    state=tweet.get("state"),
                    latitude=tweet.get("latitude"),
                    longitude=tweet.get("longitude"),
                    metadata=tweet.get("metadata", {}),
                    reported_at=datetime.fromisoformat(tweet["reported_at"].replace("Z", "+00:00")) if "T" in tweet["reported_at"] else datetime.utcnow(),
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing tweet: {e}")
        logger.info(f"Stored {stored_count} tweets in database")
        return stored_count

    def _mock_tweets(self) -> List[dict]:
        import random
        mock_tweets = []
        cities = list(INDIAN_STATES_AND_CITIES.keys())
        event_descriptions = [
            "Heavy rainfall reported in {city}, causing waterlogging in several areas. Residents advised to stay indoors.",
            "IMD issues red alert for {city} as Cyclone approaches the coast. Evacuation orders issued for coastal areas.",
            "Severe thunderstorm with hail reported in {city}. Trees uprooted, power lines damaged across multiple areas.",
            "Record-breaking heatwave in {city} with temperatures exceeding 45°C. Water scarcity reported in rural areas.",
            "Flash flooding in {city} after overnight heavy rain. Several areas submerged, rescue operations underway.",
            "Dense fog disrupts transportation in {city}. Visibility drops to less than 50 meters at multiple locations.",
            "Strong winds of 80km/h batter {city}, damaging rooftops and outdoor structures. Schools closed as precaution.",
            "Landslides reported on highways near {city} after continuous rainfall. Traffic diverted through alternate routes.",
        ]

        for i in range(20):
            city_key = random.choice(cities)
            city, state = INDIAN_STATES_AND_CITIES[city_key]
            desc = random.choice(event_descriptions).format(city=city)
            tweet_id = str(1000000000000 + random.randint(0, 999999999999))
            from app.utils.geolocation import get_city_coordinates
            coords = get_city_coordinates(city)

            mock_tweets.append({
                "source_id": tweet_id,
                "title": desc[:200],
                "description": desc,
                "source_url": f"https://twitter.com/i/status/{tweet_id}",
                "city": city,
                "state": state,
                "latitude": coords.get("latitude"),
                "longitude": coords.get("longitude"),
                "metadata": {
                    "retweet_count": random.randint(5, 500),
                    "like_count": random.randint(10, 1000),
                    "reply_count": random.randint(2, 200),
                    "author_id": str(random.randint(100000000, 999999999)),
                    "hashtag": random.choice(INDIAN_WEATHER_HASHTAGS),
                },
                "reported_at": datetime.utcnow().isoformat(),
            })
        return mock_tweets


twitter_collector = TwitterCollector()