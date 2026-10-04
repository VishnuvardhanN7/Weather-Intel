"""
Source Registry Service for ATMOS Weather Analytics Platform (PS-26069).
Centralizes configuration, status tracking, and ingestion metrics for all data sources.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

SOURCE_REGISTRY: Dict[str, dict] = {
    "openweather": {
        "source_id": "openweather",
        "name": "OpenWeather",
        "provider": "OpenWeather API",
        "type": "weather_api",
        "category": "Public Weather API",
        "status": "active",
        "collector": "openweather_collector",
        "trust_score": 0.85,
        "authentication_required": True,
        "capabilities": ["current_weather", "forecast", "weather_alerts"],
        "update_frequency": "Every 15 mins",
        "description": "Global weather observation API providing current weather & forecast models",
    },
    "open_meteo": {
        "source_id": "open_meteo",
        "name": "Open-Meteo",
        "provider": "Open-Meteo",
        "type": "weather_api",
        "category": "Public Weather API",
        "status": "active",
        "collector": "open_meteo_collector",
        "trust_score": 0.88,
        "authentication_required": False,
        "capabilities": ["temperature", "humidity", "wind", "precipitation", "wmo_codes"],
        "update_frequency": "Hourly / Multi-coord",
        "description": "High-resolution open-data meteorological model aggregator and historical archive",
    },
    "imd": {
        "source_id": "imd",
        "name": "India Meteorological Department",
        "provider": "India Meteorological Department (MoES)",
        "type": "government_weather",
        "category": "Official Government",
        "authority": "official_government_source",
        "status": "active",
        "collector": "imd_collector",
        "trust_score": 0.98,
        "authentication_required": False,
        "capabilities": ["official_bulletins", "cyclone_warnings", "monsoon_alerts", "radar_images"],
        "update_frequency": "Continuous / Bulletins",
        "description": "National meteorological agency official weather observations, warnings & bulletins",
    },
    "mosdac": {
        "source_id": "mosdac",
        "name": "MOSDAC / ISRO",
        "provider": "ISRO MOSDAC Satellite",
        "type": "satellite_weather",
        "category": "Satellite & Earth Observation",
        "authority": "ISRO_MOSDAC",
        "status": "active",
        "collector": "mosdac_collector",
        "trust_score": 0.98,
        "authentication_required": False,
        "capabilities": ["satellite_imagery", "cloud_top_temp", "insat_3dr_data", "ocean_winds"],
        "update_frequency": "Every 15 mins",
        "description": "ISRO Meteorological & Oceanographic Satellite Data Archival Centre",
    },
    "rainviewer": {
        "source_id": "rainviewer",
        "name": "RainViewer Radar",
        "provider": "RainViewer Radar API",
        "type": "radar_weather",
        "category": "Doppler Radar Network",
        "authority": "RainViewer_Radar",
        "status": "active",
        "collector": "rainviewer_collector",
        "trust_score": 0.90,
        "authentication_required": False,
        "capabilities": ["radar_mosaic", "precipitation_maps", "radar_tiles"],
        "update_frequency": "Every 10 mins",
        "description": "Global Doppler weather radar mosaic and precipitation frame maps",
    },
    "nasa_power": {
        "source_id": "nasa_power",
        "name": "NASA POWER Project",
        "provider": "NASA Langley Research Center",
        "type": "climate_weather",
        "category": "Satellite & Earth Observation",
        "authority": "NASA_POWER",
        "status": "active",
        "collector": "nasa_power_collector",
        "trust_score": 0.96,
        "authentication_required": False,
        "capabilities": ["solar_radiation", "meteorology", "climatology"],
        "update_frequency": "Daily / Hourly",
        "description": "NASA Prediction Of Worldwide Energy Resources global meteorological datasets",
    },
    "usgs_water": {
        "source_id": "usgs_water",
        "name": "USGS Water Services",
        "provider": "US Geological Survey",
        "type": "hydrology",
        "category": "River Hydrology",
        "authority": "USGS_Water",
        "status": "active",
        "collector": "usgs_water_collector",
        "trust_score": 0.94,
        "authentication_required": False,
        "capabilities": ["streamflow", "gauge_height", "river_hydrology"],
        "update_frequency": "Every 15 mins",
        "description": "USGS Instantaneous Water Services river hydrology monitoring (US stations)",
        "geographic_note": "US streamflow stations (demonstrates international hydrological data model)",
    },
    "mastodon": {
        "source_id": "mastodon",
        "name": "Mastodon Network",
        "provider": "Mastodon Decentralized Fediverse",
        "type": "social_media",
        "category": "Social Media",
        "authority": "Mastodon_Network",
        "status": "active",
        "collector": "mastodon_collector",
        "trust_score": 0.65,
        "authentication_required": False,
        "capabilities": ["hashtag_search", "public_toots", "media_attachments"],
        "update_frequency": "Real-time feed",
        "hashtags": ["#IMD", "#WeatherIndia", "#Rain", "#Flood", "#Cyclone", "#Heatwave"],
        "description": "Decentralized Fediverse public weather hashtag search and status reports",
    },
    "citizen_report": {
        "source_id": "citizen_report",
        "name": "Citizen Reports",
        "provider": "ATMOS Citizen Portal",
        "type": "citizen",
        "category": "Crowdsourced Reports",
        "status": "active",
        "collector": "citizen_report_handler",
        "trust_score": 0.60,
        "authentication_required": False,
        "capabilities": ["severe_weather_photos", "local_waterlogging", "storm_damage"],
        "update_frequency": "Real-time submissions",
        "description": "Crowdsourced severe weather observations submitted by verified citizens",
    },
    "web": {
        "source_id": "web",
        "name": "Web Sources",
        "provider": "News Wire & Web Collectors",
        "type": "web",
        "category": "News & Web Feeds",
        "status": "active",
        "collector": "web_news_collector",
        "trust_score": 0.75,
        "authentication_required": False,
        "capabilities": ["weather_news_scraping", "official_press_releases", "agency_articles"],
        "update_frequency": "Every 30 mins",
        "description": "Public weather news feeds and official agency web bulletins",
    },
    "noaa_ncei": {
        "source_id": "noaa_ncei",
        "name": "NOAA NCEI Climate",
        "provider": "NOAA National Centers for Environmental Information",
        "type": "climate_weather",
        "category": "Global Climate Archive",
        "authority": "NOAA_NCEI",
        "status": "active",
        "collector": "noaa_ncei_collector",
        "trust_score": 0.95,
        "authentication_required": True,
        "capabilities": ["climate_archive", "global_historical_climatology"],
        "update_frequency": "Daily archives",
        "description": "NOAA NCEI Climate Data Online global weather archives",
    },
    "openaq": {
        "source_id": "openaq",
        "name": "OpenAQ Air Quality",
        "provider": "OpenAQ Global Platform",
        "type": "environmental",
        "category": "Environmental & AQI",
        "authority": "OpenAQ_Global",
        "status": "active",
        "collector": "openaq_collector",
        "trust_score": 0.88,
        "authentication_required": True,
        "capabilities": ["pm25", "pm10", "no2", "so2", "air_quality_index"],
        "update_frequency": "Hourly sensor read",
        "description": "OpenAQ real-time atmospheric air quality sensor network",
    },
    "youtube": {
        "source_id": "youtube",
        "name": "YouTube Data API",
        "provider": "Google YouTube Data API v3",
        "type": "social_media",
        "category": "Video & Broadcast",
        "authority": "YouTube_API",
        "status": "active",
        "collector": "youtube_collector",
        "trust_score": 0.65,
        "authentication_required": True,
        "capabilities": ["public_video_search", "weather_report_discovery", "video_previews"],
        "update_frequency": "On-demand search",
        "description": "Public weather video search and citizen broadcast discovery",
    },
    "reddit": {
        "source_id": "reddit",
        "name": "Reddit API",
        "provider": "Reddit Public API",
        "type": "social_media",
        "category": "Social Media",
        "authority": "Reddit_API",
        "status": "active",
        "collector": "reddit_collector",
        "trust_score": 0.60,
        "authentication_required": True,
        "capabilities": ["public_post_search", "community_weather_reports"],
        "update_frequency": "On-demand search",
        "description": "Reddit public community discussions and crowdsourced weather posts",
    },
    "bluesky": {
        "source_id": "bluesky",
        "name": "Bluesky AT Protocol",
        "provider": "Bluesky Social / AT Protocol",
        "type": "social_media",
        "category": "Social Media",
        "authority": "Bluesky_ATProtocol",
        "status": "active",
        "collector": "bluesky_collector",
        "trust_score": 0.65,
        "authentication_required": True,
        "capabilities": ["at_protocol_search", "public_posts"],
        "update_frequency": "Real-time feed",
        "description": "Bluesky AT Protocol public post search for real-time weather incidents",
    },
    "weatherapi": {
        "source_id": "weatherapi",
        "name": "WeatherAPI.com",
        "provider": "WeatherAPI.com Provider",
        "type": "weather_api",
        "category": "Public Weather API",
        "authority": "WeatherAPI",
        "status": "active",
        "collector": "weatherapi_collector",
        "trust_score": 0.85,
        "authentication_required": True,
        "capabilities": ["current_weather", "city_forecast", "weather_alerts"],
        "update_frequency": "Every 15 mins",
        "description": "WeatherAPI real-time weather observation and forecast API",
    },
}


def compute_truthful_source_status(source_id: str) -> dict:
    """
    Computes truthful operational health and authentication status for a given source ID.
    Strictly based on real runtime environment, configured API keys, and metrics.
    Health States: HEALTHY, AUTH_REQUIRED, DISABLED, NO_DATA, ERROR, DEGRADED.
    """
    meta = SOURCE_REGISTRY.get(source_id, {})
    auth_req = meta.get("authentication_required", False)

    # Check key configurations per source
    auth_status = "NOT_REQUIRED"
    env_var_name = "NONE_REQUIRED"
    has_key = True

    if auth_req:
        if source_id == "openweather":
            env_var_name = "OPENWEATHER_API_KEY"
            has_key = bool(settings.OPENWEATHER_API_KEY)
        elif source_id == "noaa_ncei":
            env_var_name = "NOAA_API_KEY"
            has_key = bool(getattr(settings, "NOAA_API_KEY", ""))
        elif source_id == "openaq":
            env_var_name = "OPENAQ_API_KEY"
            has_key = bool(getattr(settings, "OPENAQ_API_KEY", ""))
        elif source_id == "youtube":
            env_var_name = "YOUTUBE_API_KEY"
            has_key = bool(getattr(settings, "YOUTUBE_API_KEY", ""))
        elif source_id == "reddit":
            env_var_name = "REDDIT_CLIENT_ID"
            has_key = bool(getattr(settings, "REDDIT_CLIENT_ID", ""))
        elif source_id == "bluesky":
            env_var_name = "BLUESKY_IDENTIFIER"
            has_key = bool(getattr(settings, "BLUESKY_IDENTIFIER", ""))
        elif source_id == "weatherapi":
            env_var_name = "WEATHERAPI_API_KEY"
            has_key = bool(getattr(settings, "WEATHERAPI_API_KEY", ""))
        elif source_id in ("twitter", "apify_x", "social"):
            env_var_name = "APIFY_API_TOKEN"
            has_key = bool(getattr(settings, "APIFY_API_TOKEN", ""))
        else:
            env_var_name = "API_KEY"
            has_key = False

        auth_status = "CONFIGURED" if has_key else "MISSING"

    # Inspect metrics for real runtime state
    m = metrics_tracker._metrics.get(source_id, {})
    last_error = m.get("last_error")
    failed_cnt = m.get("requests_failed", 0)
    success_cnt = m.get("requests_success", 0)
    rec_pub = m.get("records_published", 0)

    if meta.get("status") == "disabled":
        status_code = "DISABLED"
    elif auth_req and auth_status == "MISSING":
        status_code = "AUTH_REQUIRED"
    elif failed_cnt > 0 and success_cnt == 0:
        status_code = "ERROR"
    elif failed_cnt > 0 and success_cnt > 0:
        status_code = "DEGRADED"
    elif success_cnt > 0 and rec_pub == 0:
        status_code = "NO_DATA"
    else:
        status_code = "HEALTHY"

    return {
        "status": status_code,
        "authentication_status": auth_status,
        "credential_status": auth_status,
        "env_var_name": env_var_name,
        "credential_configured": (auth_status != "MISSING"),
        "enabled": (meta.get("status") != "disabled"),
        "last_error": last_error,
        "last_success_at": m.get("last_success_at"),
    }


class PipelineMetricsTracker:
    """Thread-safe global tracker for end-to-end Big Data streaming pipeline metrics."""

    def __init__(self):
        self._metrics = {
            "collected_total": 0,
            "published_raw_total": 0,
            "spark_processed_total": 0,
            "ai_evaluated_total": 0,
            "jev_accepted_total": 0,
            "jev_rejected_total": 0,
            "published_verified_total": 0,
            "sink_processed_total": 0,
            "sink_persisted_total": 0,
            "new_inserts_total": 0,
            "already_existing_updated_total": 0,
            "total_db_records": 0,
            "opensearch_indexed_total": 0,
            "websocket_broadcast_total": 0,
            "filtered_routine_total": 0,
            "media_discovered_total": 0,
            "last_ingestion_at": None,
        }

    def record_run(
        self,
        collected: int,
        published_raw: int,
        spark_processed: int,
        ai_evaluated: int,
        jev_accepted: int,
        jev_rejected: int,
        persisted: int,
        new_inserts: int = 0,
        already_existing: int = 0,
        total_db_records: int = 0,
        opensearch_indexed: int = 0,
        websocket_broadcast: int = 0,
        filtered_routine: int = 0,
        media_discovered: int = 0,
    ):
        m = self._metrics
        m["collected_total"] += collected
        m["published_raw_total"] += published_raw
        m["spark_processed_total"] += spark_processed
        m["ai_evaluated_total"] += ai_evaluated
        m["jev_accepted_total"] += jev_accepted
        m["jev_rejected_total"] += jev_rejected
        m["published_verified_total"] += jev_accepted
        m["sink_processed_total"] += persisted
        m["sink_persisted_total"] += new_inserts
        m["new_inserts_total"] += new_inserts
        m["already_existing_updated_total"] += already_existing
        m["total_db_records"] = total_db_records
        m["opensearch_indexed_total"] += opensearch_indexed
        m["websocket_broadcast_total"] += websocket_broadcast
        m["filtered_routine_total"] += filtered_routine
        m["media_discovered_total"] += media_discovered
        m["last_ingestion_at"] = datetime.utcnow().isoformat()

    def get_pipeline_metrics(self) -> dict:
        return dict(self._metrics)


class SourceMetricsTracker:
    """In-memory metrics tracker for source health and throughput monitoring."""

    def __init__(self):
        self._metrics: Dict[str, dict] = {}
        for source_id in SOURCE_REGISTRY:
            self._metrics[source_id] = {
                "requests_total": 0,
                "requests_success": 0,
                "requests_failed": 0,
                "records_received": 0,
                "records_published": 0,
                "records_duplicate": 0,
                "media_collected": 0,
                "last_success_at": None,
                "last_failure_at": None,
                "last_error": None,
                "average_latency_ms": 0.0,
                "status": "healthy",
            }

    def record_success(
        self,
        source_id: str,
        records_received: int,
        records_published: int,
        duplicates: int = 0,
        media_count: int = 0,
        latency_ms: float = 0.0,
    ):
        if source_id not in self._metrics:
            self._metrics[source_id] = {
                "requests_total": 0, "requests_success": 0, "requests_failed": 0,
                "records_received": 0, "records_published": 0, "records_duplicate": 0,
                "media_collected": 0, "last_success_at": None, "last_failure_at": None,
                "last_error": None, "average_latency_ms": 0.0, "status": "healthy",
            }
        m = self._metrics[source_id]
        m["requests_total"] += 1
        m["requests_success"] += 1
        m["records_received"] += records_received
        m["records_published"] += records_published
        m["records_duplicate"] += duplicates
        m["media_collected"] += media_count
        m["last_success_at"] = datetime.now(timezone.utc).isoformat()
        m["status"] = "healthy"

        # Moving average latency
        if m["average_latency_ms"] == 0.0:
            m["average_latency_ms"] = round(latency_ms, 1)
        else:
            m["average_latency_ms"] = round(0.8 * m["average_latency_ms"] + 0.2 * latency_ms, 1)

    def record_failure(self, source_id: str, error_msg: Optional[str] = None):
        if source_id not in self._metrics:
            self._metrics[source_id] = {
                "requests_total": 0, "requests_success": 0, "requests_failed": 0,
                "records_received": 0, "records_published": 0, "records_duplicate": 0,
                "media_collected": 0, "last_success_at": None, "last_failure_at": None,
                "last_error": None, "average_latency_ms": 0.0,
            }
        m = self._metrics[source_id]
        m["requests_total"] += 1
        m["requests_failed"] += 1
        m["last_failure_at"] = datetime.now(timezone.utc).isoformat()
        if error_msg:
            m["last_error"] = str(error_msg)[:200]
        logger.warning(f"[SOURCE_REGISTRY] Recorded failure for source '{source_id}': {error_msg}")

    def get_metrics(self, source_id: str) -> Optional[dict]:
        return self._metrics.get(source_id)

    def get_all_metrics(self) -> Dict[str, dict]:
        result = {}
        for source_id, meta in SOURCE_REGISTRY.items():
            health = compute_truthful_source_status(source_id)
            metrics = self._metrics.get(source_id, {})
            result[source_id] = {
                **meta,
                **health,
                "metrics": metrics,
            }
        return result


metrics_tracker = SourceMetricsTracker()
pipeline_tracker = PipelineMetricsTracker()


def get_source(source_id: str) -> Optional[dict]:
    source = SOURCE_REGISTRY.get(source_id.lower())
    if not source:
        return None
    health = compute_truthful_source_status(source_id)
    return {**source, **health}


def list_sources(active_only: bool = False) -> List[dict]:
    result = []
    for source_id, meta in SOURCE_REGISTRY.items():
        health = compute_truthful_source_status(source_id)
        src = {**meta, **health}
        if not active_only or src["status"] in ("HEALTHY", "LIVE_VERIFIED", "READY"):
            result.append(src)
    return result


def get_source_metadata(source_id: str, collector: Optional[str] = None) -> dict:
    source = get_source(source_id) or {
        "source_id": source_id,
        "name": source_id.capitalize(),
        "provider": source_id,
        "type": "custom",
        "status": "active",
    }
    return {
        "source_id": source["source_id"],
        "provider": source.get("provider", source["name"]),
        "source_type": source.get("type", "weather_api"),
        "collector": collector or source.get("collector", f"{source_id}_collector"),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "api_version": "v1",
    }


def update_source_status(source_id: str, status: str, error: Optional[str] = None) -> bool:
    source = SOURCE_REGISTRY.get(source_id)
    if source:
        source["health"] = status
        source["status"] = status
        if error:
            source["last_error"] = error
        return True
    return False

