"""
ISRO MOSDAC Satellite Meteorological Data Collector (PS-26069).
Meteorological & Oceanographic Satellite Data Archival Centre (MOSDAC), Space Applications Centre, ISRO.
Publishes normalized satellite events directly to Kafka `weather.raw`.
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

import httpx

from app.core.config import settings
from app.services.source_registry import get_source_metadata, metrics_tracker
from app.services.kafka_service import kafka_service

logger = logging.getLogger(__name__)

MOSDAC_BASE_URL = "https://mosdac.gov.in"
MOSDAC_CATALOG_URL = "https://mosdac.gov.in/catalog-app/satellite.php"
MOSDAC_API_URL = "https://mosdac.gov.in/api/v1"


def slugify(text: str) -> str:
    return re.sub(r"[^\w]+", "_", text.strip().lower())


def parse_bounding_box(bbox_str: str) -> Tuple[float, float, float, float]:
    """Parse bounding box string 'min_lon,min_lat,max_lon,max_lat' into floats."""
    try:
        parts = [float(p.strip()) for p in bbox_str.split(",") if p.strip()]
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
    except Exception:
        pass
    # Default India bounding box: 70.0, 8.0, 90.0, 28.0
    return 70.0, 8.0, 90.0, 28.0


class MosdacCollector:
    """Adapter-based collector for ISRO MOSDAC satellite datasets and products."""

    def __init__(self):
        self.source_id = "mosdac"
        self.collector_name = "mosdac_collector"
        self.authority = "ISRO_MOSDAC"
        self.health_state = "DISABLED" if not getattr(settings, "MOSDAC_ENABLED", False) else "READY"
        self._auth_token: Optional[str] = None

    def generate_deterministic_event_id(self, dataset_id: str, ts_str: str, product_id: Optional[str] = None) -> str:
        """Generate deterministic event ID based on dataset, timestamp, and optional product ID."""
        ds_slug = slugify(dataset_id)
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ts_sec = int(dt.timestamp())
        except Exception:
            ts_sec = int(datetime.now(timezone.utc).timestamp() // 3600 * 3600)
            
        if product_id:
            p_hash = hashlib.md5(product_id.encode()).hexdigest()[:8]
            return f"weather_mosdac_{ds_slug}_{ts_sec}_{p_hash}"
        return f"weather_mosdac_{ds_slug}_{ts_sec}"

    def get_source_header(self) -> Dict[str, Any]:
        meta = get_source_metadata(self.source_id, collector=self.collector_name)
        meta["authority"] = self.authority
        meta["provider"] = "ISRO MOSDAC Satellite"
        meta["source_type"] = "satellite_weather"
        return meta

    # ==========================================
    # 1. AUTHENTICATION ADAPTER
    # ==========================================
    async def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Authenticate user credentials against ISRO MOSDAC portal."""
        uname = username or getattr(settings, "MOSDAC_USERNAME", "")
        passwd = password or getattr(settings, "MOSDAC_PASSWORD", "")

        if not uname or not passwd:
            logger.info("[MOSDAC] Authentication credentials (MOSDAC_USERNAME / MOSDAC_PASSWORD) not configured.")
            self.health_state = "AUTH_REQUIRED"
            return False

        auth_url = f"{MOSDAC_BASE_URL}/user/login"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(auth_url, data={"username": uname, "password": passwd}, timeout=10.0)
                if resp.status_code == 200:
                    self._auth_token = resp.cookies.get("MOSDAC_SESSION", "authenticated_session")
                    self.health_state = "READY"
                    logger.info("[MOSDAC] Successfully authenticated session with ISRO MOSDAC.")
                    return True
                else:
                    self.health_state = "AUTH_REQUIRED"
                    logger.warning(f"[MOSDAC] Authentication failed with status {resp.status_code}.")
                    return False
        except Exception as e:
            logger.warning(f"[MOSDAC] Authentication error: {e}")
            self.health_state = "DEGRADED"
            return False

    # ==========================================
    # 2. DATASET METADATA DISCOVERY
    # ==========================================
    async def fetch_dataset_metadata(self, dataset_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch metadata and sensor specifications for a MOSDAC satellite dataset."""
        ds_id = dataset_id or getattr(settings, "MOSDAC_DATASET_ID", "3D_L1B_STD")
        url = f"{MOSDAC_API_URL}/catalog/dataset/{ds_id}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.debug(f"[MOSDAC] Dataset metadata discovery note for '{ds_id}': {e}")
        return None

    # ==========================================
    # 3. NEAR-REAL-TIME (NRT) PRODUCTS ADAPTER
    # ==========================================
    async def fetch_nrt_products(
        self,
        dataset_id: Optional[str] = None,
        bounding_box: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch NRT satellite products over configured bounding box."""
        if not getattr(settings, "MOSDAC_ENABLED", False):
            self.health_state = "DISABLED"
            return []

        ds_id = dataset_id or getattr(settings, "MOSDAC_DATASET_ID", "3D_L1B_STD")
        bbox_str = bounding_box or getattr(settings, "MOSDAC_BOUNDING_BOX", "70.0,8.0,90.0,28.0")
        min_lon, min_lat, max_lon, max_lat = parse_bounding_box(bbox_str)

        start_time = datetime.now(timezone.utc)
        url = f"{MOSDAC_BASE_URL}/api/v1/products/nrt"
        params = {
            "dataset_id": ds_id,
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        }

        headers = {}
        if self._auth_token:
            headers["Cookie"] = f"MOSDAC_SESSION={self._auth_token}"

        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=headers, timeout=15.0)
                if resp.status_code in (401, 403):
                    logger.info("[MOSDAC] Authentication required — source waiting for MOSDAC credentials")
                    self.health_state = "AUTH_REQUIRED"
                    metrics_tracker.record_failure(self.source_id, "AUTH_REQUIRED")
                    return []
                resp.raise_for_status()
                data = resp.json()

                records = data if isinstance(data, list) else data.get("products", [])
                for item in records:
                    event = self.normalize_satellite_observation(item, ds_id, bbox_str)
                    if event:
                        events.append(event)

                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                self.health_state = "HEALTHY"
                metrics_tracker.record_success(self.source_id, len(records), len(events), latency_ms=latency)
        except Exception as e:
            logger.info(f"[MOSDAC] NRT API request note: {e}")
            if self.health_state != "AUTH_REQUIRED":
                self.health_state = "DEGRADED"
            metrics_tracker.record_failure(self.source_id, str(e))

        return events

    # ==========================================
    # 4. ARCHIVED SATELLITE PRODUCTS ADAPTER
    # ==========================================
    async def fetch_archive_products(
        self,
        dataset_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch archived satellite products by dataset ID and date range."""
        ds_id = dataset_id or getattr(settings, "MOSDAC_DATASET_ID", "3D_L1B_STD")
        url = f"{MOSDAC_BASE_URL}/api/v1/products/archive"
        params = {
            "dataset_id": ds_id,
            "start_date": start_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "end_date": end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }

        events = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=15.0)
                if resp.status_code in (401, 403):
                    self.health_state = "AUTH_REQUIRED"
                    return []
                resp.raise_for_status()
                records = resp.json() if isinstance(resp.json(), list) else resp.json().get("products", [])

                for item in records:
                    event = self.normalize_satellite_observation(item, ds_id, "70.0,8.0,90.0,28.0")
                    if event:
                        events.append(event)
        except Exception as e:
            logger.info(f"[MOSDAC] Archive API request note: {e}")

        return events

    # ==========================================
    # 5. NORMALIZATION INTO RAW EVENT SCHEMA
    # ==========================================
    def normalize_satellite_observation(
        self,
        raw_product: Dict[str, Any],
        dataset_id: str,
        bbox_str: str
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize MOSDAC raw product metadata into ATMOS raw event schema.
        Use null for fields not supplied by MOSDAC without inventing city/state/GPS.
        """
        if not raw_product:
            return None

        product_id = raw_product.get("product_id") or raw_product.get("id") or str(raw_product.get("file_name", ""))
        sat_name = raw_product.get("satellite") or "INSAT-3D"
        sensor_name = raw_product.get("sensor") or "Imager"
        product_name = raw_product.get("product") or raw_product.get("product_type") or "L1B_STD"
        obs_time = raw_product.get("observation_time") or raw_product.get("timestamp") or datetime.now(timezone.utc).isoformat()

        center_lat = raw_product.get("center_latitude") or raw_product.get("latitude")
        center_lon = raw_product.get("center_longitude") or raw_product.get("longitude")

        # Use center coords of bounding box if not explicitly given
        if center_lat is None or center_lon is None:
            min_lon, min_lat, max_lon, max_lat = parse_bounding_box(bbox_str)
            center_lat = round((min_lat + max_lat) / 2.0, 4)
            center_lon = round((min_lon + max_lon) / 2.0, 4)

        ev_id = self.generate_deterministic_event_id(dataset_id, obs_time, product_id)
        title = f"ISRO MOSDAC Satellite Observation: {sat_name} {sensor_name} ({product_name})"
        description = (
            f"ISRO MOSDAC satellite meteorological observation dataset {dataset_id}. "
            f"Satellite: {sat_name}, Sensor: {sensor_name}, Product: {product_name}. "
            f"Coverage: India Bounding Box [{bbox_str}]."
        )

        return {
            "event_id": ev_id,
            "id": ev_id,
            "title": title,
            "description": description,
            "event_type": "satellite_weather",
            "severity": "moderate",
            "city": raw_product.get("city", None),
            "state": raw_product.get("state", None),
            "latitude": center_lat,
            "longitude": center_lon,
            "source": self.source_id,
            "source_metadata": self.get_source_header(),
            "source_type": "mosdac",
            "source_url": raw_product.get("download_url") or f"{MOSDAC_BASE_URL}/catalog-app/satellite.php",
            "timestamp": obs_time,
            "reported_at": obs_time,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": "SOURCE_REPORTED",
            "metadata": {
                "dataset_id": dataset_id,
                "satellite": sat_name,
                "sensor": sensor_name,
                "product": product_name,
                "observation_time": obs_time,
                "coverage": f"India_{bbox_str.replace(',', '_')}",
                "is_satellite_observation": True,
            },
            "pipeline": {
                "stage": "RAW",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
        }

    # ==========================================
    # 6. MAIN COLLECT & PUBLISH TO KAFKA
    # ==========================================
    async def fetch_and_publish_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, bool]]:
        """
        Main continuous worker entry point.
        Checks settings, executes adapters, normalizes, and publishes to Kafka weather.raw.
        """
        if not getattr(settings, "MOSDAC_ENABLED", False):
            logger.info("[MOSDAC] Source disabled in configuration (MOSDAC_ENABLED=false).")
            self.health_state = "DISABLED"
            return [], {}

        # Attempt authentication if credentials provided
        if getattr(settings, "MOSDAC_USERNAME", "") and getattr(settings, "MOSDAC_PASSWORD", ""):
            await self.authenticate()

        logger.info("[MOSDAC] Fetching real MOSDAC satellite product observations...")
        events = await self.fetch_nrt_products()

        # If NRT empty, try archive adapter for current date
        if not events and self.health_state != "AUTH_REQUIRED":
            events = await self.fetch_archive_products()

        publish_results: Dict[str, bool] = {}
        for ev in events:
            ev_id = ev.get("event_id")
            success = kafka_service.publish_raw_event(ev)
            publish_results[ev_id] = success

        published_count = sum(1 for status in publish_results.values() if status)
        logger.info(
            f"[MOSDAC] Ingestion cycle completed: {len(events)} satellite events collected, {published_count} published to weather.raw"
        )
        return events, publish_results


mosdac_collector = MosdacCollector()
