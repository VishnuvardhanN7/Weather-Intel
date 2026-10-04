from pathlib import Path
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "National Weather Big Data Analytics Platform"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        """Accept deployment labels injected by common hosting environments.

        A hosting environment currently supplies ``DEBUG=release``. Pydantic's
        boolean parser rejects that string before the app or Alembic can start.
        Production/release labels deliberately map to ``False``; conventional
        true/false values keep Pydantic's standard parsing behavior.
        """
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"development", "dev"}:
                return True
        return value

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/weather_platform"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/weather_platform"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v):
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

            if "?" in v:
                from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
                parsed = urlparse(v)
                query_params = parse_qsl(parsed.query, keep_blank_values=True)
                new_params = []
                for key, val in query_params:
                    if key in ("channel_binding", "gssencmode", "target_session_attrs"):
                        continue
                    if key == "sslmode":
                        if val in ("require", "verify-full", "verify-ca", "prefer", "allow"):
                            new_params.append(("ssl", "require"))
                        continue
                    new_params.append((key, val))
                new_query = urlencode(new_params)
                v = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
        return v

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def assemble_db_url_sync(cls, v):
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql://", 1)
            if "ssl=" in v and "sslmode=" not in v:
                import re
                v = re.sub(r"([?&])ssl=[^&]+", r"\1sslmode=require", v)
        return v

    # JWT
    JWT_SECRET_KEY: str = "super-secret-change-in-production-weather-platform-2024"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:80",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # External APIs
    OPENWEATHER_API_KEY: str = ""
    TWITTER_BEARER_TOKEN: str = ""
    APIFY_API_TOKEN: str = ""
    APIFY_X_ACTOR_ID: str = "data-slayer~twitter-search"

    # IMD Configuration
    IMD_ENABLED: bool = True
    IMD_API_BASE_URL: str = "https://api.imd.gov.in"
    IMD_API_KEY: str = ""
    IMD_INTERVAL_SECONDS: int = 900
    IMD_CACHE_SECONDS: int = 300

    # MOSDAC Configuration
    MOSDAC_ENABLED: bool = False
    MOSDAC_USERNAME: str = ""
    MOSDAC_PASSWORD: str = ""
    MOSDAC_DATASET_ID: str = "3D_L1B_STD"
    MOSDAC_INTERVAL_SECONDS: int = 900
    MOSDAC_CACHE_SECONDS: int = 300
    MOSDAC_BOUNDING_BOX: str = "70.0,8.0,90.0,28.0"

    # RainViewer Configuration
    RAINVIEWER_ENABLED: bool = False
    RAINVIEWER_CACHE_SECONDS: int = 300
    RAINVIEWER_INTERVAL_SECONDS: int = 900

    # NASA POWER Configuration
    NASA_POWER_ENABLED: bool = False
    NASA_POWER_INTERVAL_SECONDS: int = 3600
    NASA_POWER_CACHE_SECONDS: int = 1800

    # NOAA / NCEI Configuration
    NOAA_ENABLED: bool = False
    NOAA_API_KEY: str = ""
    NOAA_INTERVAL_SECONDS: int = 900

    # OpenAQ Configuration
    OPENAQ_ENABLED: bool = False
    OPENAQ_API_KEY: str = ""
    OPENAQ_INTERVAL_SECONDS: int = 900

    # USGS Water Configuration
    USGS_WATER_ENABLED: bool = False
    USGS_WATER_INTERVAL_SECONDS: int = 900

    # YouTube Configuration
    YOUTUBE_ENABLED: bool = False
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_INTERVAL_SECONDS: int = 900
    YOUTUBE_SEARCH_TERMS: str = "weather India,heavy rainfall India,flood India,cyclone India,heatwave India,thunderstorm India,IMD weather,weather warning India"

    # Reddit Configuration
    REDDIT_ENABLED: bool = False
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "ATMOS-WeatherPlatform/1.0"
    REDDIT_INTERVAL_SECONDS: int = 900
    REDDIT_SEARCH_TERMS: str = "weather India,rain India,flood India,cyclone India,heatwave India,IMD,thunderstorm India"

    # Mastodon Configuration
    MASTODON_ENABLED: bool = False
    MASTODON_INSTANCE: str = "mastodon.social"
    MASTODON_ACCESS_TOKEN: str = ""
    MASTODON_INTERVAL_SECONDS: int = 900
    MASTODON_HASHTAGS: str = "IMD,WeatherIndia,Rain,Flood,Cyclone,Heatwave"

    # Bluesky Configuration
    BLUESKY_ENABLED: bool = False
    BLUESKY_IDENTIFIER: str = ""
    BLUESKY_APP_PASSWORD: str = ""
    BLUESKY_INTERVAL_SECONDS: int = 900
    BLUESKY_SEARCH_TERMS: str = "weather India,rain India,flood India,cyclone India,IMD,heatwave India"

    # WeatherAPI Configuration
    WEATHERAPI_ENABLED: bool = False
    WEATHERAPI_API_KEY: str = ""
    WEATHERAPI_INTERVAL_SECONDS: int = 900

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # ML
    FAKE_DETECTION_THRESHOLD: float = 0.7
    DUPLICATE_DISTANCE_KM: float = 10.0
    DUPLICATE_TIME_WINDOW_HOURS: int = 6
    JEV_THRESHOLD: float = 0.6

    # Kafka Infrastructure
    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_RAW_TOPIC: str = "weather.raw"
    KAFKA_CLEAN_TOPIC: str = "weather.clean"
    KAFKA_VERIFIED_TOPIC: str = "weather.verified"

    # OpenSearch Configuration
    OPENSEARCH_ENABLED: bool = False
    OPENSEARCH_URL: str = "http://localhost:9200"
    OPENSEARCH_INDEX: str = "weather-events"

    # Downstream Sink Configuration
    SINK_ALERTNESS_THRESHOLD: float = 0.90

    # The compiled React application. It is present in the single-container image.
    FRONTEND_DIST_DIR: Path = Path(__file__).resolve().parents[3] / "frontend" / "dist"


settings = Settings()

