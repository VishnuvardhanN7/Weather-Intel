"""
Unified Ingestion Service for ATMOS Weather Analytics Platform (PS-26069).
Orchestrates heterogeneous data collectors, Kafka RAW ingestion, Spark/AI processing,
JEV verification, and Sink Consumer persistence across all 16 registered data sources.
"""

import logging
from typing import Iterable, List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.models.weather_event import WeatherEvent
from app.services.source_registry import (
    SOURCE_REGISTRY,
    metrics_tracker,
    pipeline_tracker,
    compute_truthful_source_status,
)
from app.services.kafka_service import kafka_service
from app.spark.weather_stream_processor import weather_stream_processor
from app.services.streaming_pipeline import jev_stream_processor
from app.services.sink_consumer import sink_consumer

# Collectors for all 16 source families
from app.collectors.api_collector import api_collector
from app.collectors.open_meteo_collector import OpenMeteoCollector
from app.collectors.imd_collector import imd_collector
from app.collectors.mosdac_collector import mosdac_collector
from app.collectors.rainviewer_collector import rainviewer_collector
from app.collectors.nasa_power_collector import nasa_power_collector
from app.collectors.usgs_water_collector import usgs_water_collector
from app.collectors.mastodon_collector import mastodon_collector
from app.collectors.citizen_report import citizen_report_handler
from app.collectors.web_scraper import web_scraper
from app.collectors.noaa_ncei_collector import noaa_ncei_collector
from app.collectors.openaq_collector import openaq_collector
from app.collectors.youtube_collector import youtube_collector
from app.collectors.reddit_collector import reddit_collector
from app.collectors.bluesky_collector import bluesky_collector
from app.collectors.weatherapi_collector import weatherapi_collector

logger = logging.getLogger(__name__)

AVAILABLE_SOURCES = set(SOURCE_REGISTRY.keys()).union({
    "social",
    "web",
    "public_api",
    "sample_citizen_reports",
    "all",
})

open_meteo_collector = OpenMeteoCollector()


async def run_ingestion(
    db: AsyncSession,
    sources: Iterable[str],
    use_sample_data: bool = False
) -> dict:
    """
    Executes live/production multi-source ingestion across all 16 registered weather data sources.
    Drives collected events through the complete streaming pipeline:
    Collector -> Kafka RAW -> Spark/AI -> CLEAN -> JEV -> VERIFIED -> Sink Consumer (DB/OpenSearch/WebSockets).

    Fault-Tolerant Processing:
    Missing API credentials for a source mark that source as AUTH_REQUIRED without failing the ingestion run.
    """

    requested = set(sources)
    if "all" in requested:
        target_sources = set(SOURCE_REGISTRY.keys())
    else:
        target_sources = set()
        for s in requested:
            if s == "public_api":
                target_sources.add("openweather")
                target_sources.add("open_meteo")
                target_sources.add("weatherapi")
            elif s == "social":
                target_sources.add("mastodon")
                target_sources.add("youtube")
                target_sources.add("reddit")
                target_sources.add("bluesky")
            elif s == "web":
                target_sources.add("web")
            elif s == "sample_citizen_reports":
                target_sources.add("citizen_report")
            elif s in SOURCE_REGISTRY:
                target_sources.add(s)

    results: Dict[str, dict] = {}
    collected_records: List[dict] = []
    source_breakdown: Dict[str, int] = {}
    warnings: List[str] = []
    total_media_discovered = 0
    sources_succeeded_count = 0
    sources_skipped_count = 0
    sources_failed_count = 0

    for source_id in sorted(target_sources):
        meta = SOURCE_REGISTRY.get(source_id, {})
        source_name = meta.get("name", source_id.capitalize())
        health_info = compute_truthful_source_status(source_id)
        auth_req = meta.get("authentication_required", False)
        auth_status = health_info.get("authentication_status", "NOT_REQUIRED")
        env_var = health_info.get("env_var_name", "NONE")

        # 1. Check Auth Requirement
        if auth_req and auth_status == "MISSING" and not use_sample_data:
            warn_str = f"{source_name}: skipped — API key not configured ({env_var})"
            logger.info("[INGESTION] %s", warn_str)
            warnings.append(warn_str)
            metrics_tracker.record_failure(source_id, f"AUTH_REQUIRED ({env_var} missing)")
            sources_skipped_count += 1
            results[source_id] = {
                "source": source_name,
                "source_id": source_id,
                "status": "SKIPPED",
                "credential_status": "MISSING",
                "env_var_name": env_var,
                "collected": 0,
                "published_raw": 0,
                "error": warn_str
            }
            continue

        # 2. Execute Collector for Source
        start_t = datetime.now(timezone.utc)
        try:
            records: List[dict] = []
            pub_count = 0
            media_count = 0

            if source_id == "openweather":
                if settings.KAFKA_ENABLED:
                    bulk_res = await api_collector.publish_raw_weather_bulk(use_sample_data=use_sample_data)
                    pub_count = sum(1 for success in bulk_res.values() if success)
                    records = [{"event_id": k} for k in bulk_res.keys()]
                else:
                    raw_records = await api_collector.fetch_openweather_bulk(use_sample_data=use_sample_data)
                    for r in raw_records:
                        raw_evt = {
                            "event_id": f"weather_openweather_{r.get('city', 'city').lower().replace(' ', '_')}_{int(datetime.now(timezone.utc).timestamp())}",
                            "source": "openweather",
                            "timestamp": r.get("reported_at") or datetime.now(timezone.utc).isoformat(),
                            "title": r.get("title"),
                            "description": r.get("description"),
                            "event_type": r.get("event_type", "other"),
                            "severity": r.get("severity", "low"),
                            "location": {
                                "latitude": r.get("latitude"),
                                "longitude": r.get("longitude"),
                                "city": r.get("city"),
                                "state": r.get("state", ""),
                            },
                            "media": r.get("media", []),
                            "metadata": r.get("metadata", {}),
                            "processing_status": "RAW",
                        }
                        records.append(raw_evt)
                        collected_records.append(raw_evt)
                        if kafka_service.publish_raw_event(raw_evt):
                            pub_count += 1

            elif source_id == "open_meteo":
                from app.core.location_registry import get_all_locations
                locs = get_all_locations()[:15]
                om_events = await open_meteo_collector.fetch_current_batch(locs)
                for om_evt in om_events:
                    om_evt["source"] = "open_meteo"
                    records.append(om_evt)
                    collected_records.append(om_evt)
                    if kafka_service.publish_raw_event(om_evt):
                        pub_count += 1

            elif source_id == "imd":
                imd_bulletins, _ = await imd_collector.fetch_and_publish_all()
                for b in imd_bulletins:
                    b["source"] = "imd"
                    records.append(b)
                    collected_records.append(b)
                    pub_count += 1

            elif source_id == "mosdac":
                evs, _ = await mosdac_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            elif source_id == "rainviewer":
                evs, _ = await rainviewer_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            elif source_id == "nasa_power":
                evs, _ = await nasa_power_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            elif source_id == "usgs_water":
                evs, _ = await usgs_water_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            elif source_id == "mastodon":
                evs, _ = await mastodon_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)
                media_count = sum(len(e.get("media", [])) for e in evs)

            elif source_id == "citizen_report":
                if use_sample_data:
                    mock_reports = citizen_report_handler._mock_citizen_reports()
                    stored = await citizen_report_handler.store_citizen_reports(db, mock_reports)
                    records.extend(mock_reports)
                    pub_count = stored

            elif source_id == "web":
                web_recs = await web_scraper.scrape_all_sources()
                if not web_recs and use_sample_data:
                    web_recs = web_scraper._mock_articles()
                if web_recs:
                    stored_web = await web_scraper.store_scraped_articles(db, web_recs)
                    records.extend(web_recs)
                    pub_count = stored_web

            elif source_id == "noaa_ncei":
                evs, _ = await noaa_ncei_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            elif source_id == "openaq":
                evs, _ = await openaq_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            elif source_id == "youtube":
                evs, _ = await youtube_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)
                media_count = len(evs)

            elif source_id == "reddit":
                evs, _ = await reddit_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            elif source_id == "bluesky":
                evs, _ = await bluesky_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            elif source_id == "weatherapi":
                evs, _ = await weatherapi_collector.fetch_and_publish_all()
                records.extend(evs)
                collected_records.extend(evs)
                pub_count = len(evs)

            lat_ms = (datetime.now(timezone.utc) - start_t).total_seconds() * 1000
            count = len(records)
            source_breakdown[source_name] = count
            total_media_discovered += media_count

            status_val = "HEALTHY" if count > 0 or not auth_req else "NO_DATA"
            metrics_tracker.record_success(source_id, count, pub_count, media_count=media_count, latency_ms=lat_ms)
            sources_succeeded_count += 1

            results[source_id] = {
                "source": source_name,
                "source_id": source_id,
                "status": status_val,
                "credential_status": auth_status,
                "env_var_name": env_var,
                "collected": count,
                "published_raw": pub_count,
                "media_discovered": media_count,
                "error": None
            }

        except Exception as exc:
            warn_str = f"{source_name}: error during collection — {str(exc)}"
            logger.warning("[INGESTION] Source '%s' ingestion error: %s", source_id, exc)
            warnings.append(warn_str)
            metrics_tracker.record_failure(source_id, str(exc))
            sources_failed_count += 1
            results[source_id] = {
                "source": source_name,
                "source_id": source_id,
                "status": "DEGRADED",
                "credential_status": auth_status,
                "env_var_name": env_var,
                "collected": 0,
                "published_raw": 0,
                "error": str(exc)
            }

    total_collected = sum(r.get("collected", 0) for r in results.values())
    total_published_raw = sum(r.get("published_raw", 0) for r in results.values())

    # -------------------------------------------------------------
    # DRIVE PIPELINE PROCESSING CYCLE
    # -------------------------------------------------------------
    # Step A: Spark / AI Processing (weather.raw -> weather.clean)
    if settings.KAFKA_ENABLED:
        clean_events = weather_stream_processor.process_raw_batch(max_records=max(total_published_raw, 30))
    else:
        from app.spark.weather_stream_processor import process_event_with_ai_engines
        clean_events = [process_event_with_ai_engines(rec) for rec in collected_records]

    spark_processed_count = len(clean_events)
    ai_evaluated_count = len(clean_events)

    # Step B: JEV Verification Processing (weather.clean -> weather.verified)
    if settings.KAFKA_ENABLED:
        verified_events = jev_stream_processor.process_clean_batch(max_records=max(spark_processed_count, 30))
    else:
        verified_events = []
        for evt in clean_events:
            res = jev_stream_processor.process_clean_event(evt)
            if res:
                verified_events.append(res)

    jev_accepted_count = len(verified_events)
    jev_rejected_count = max(0, ai_evaluated_count - jev_accepted_count)

    # Step C: Sink Consumer (weather.verified -> alertness > 0.90 gate -> PostgreSQL & WebSockets)
    if settings.KAFKA_ENABLED:
        sink_results = await sink_consumer.consume_loop_async(max_records=max(jev_accepted_count, 30), db_session=db)
    else:
        sink_results = []
        for v_evt in verified_events:
            r = await sink_consumer.process_verified_event_async(v_evt, db_session=db)
            sink_results.append(r)

    sink_accepted_count = sum(1 for r in sink_results if r.get("accepted"))
    new_inserts_count = sum(1 for r in sink_results if r.get("accepted") and r.get("is_new_record"))
    already_existing_count = sum(1 for r in sink_results if r.get("accepted") and not r.get("is_new_record"))
    filtered_routine_count = sum(1 for r in sink_results if r.get("status") == "FILTERED")

    # Authoritative real DB total count directly from PostgreSQL
    total_db_count = (await db.execute(select(func.count(WeatherEvent.id)))).scalar_one_or_none() or 0

    # Record global pipeline metrics
    pipeline_tracker.record_run(
        collected=total_collected,
        published_raw=total_published_raw if settings.KAFKA_ENABLED else total_collected,
        spark_processed=spark_processed_count,
        ai_evaluated=ai_evaluated_count,
        jev_accepted=jev_accepted_count,
        jev_rejected=jev_rejected_count,
        persisted=sink_accepted_count,
        new_inserts=new_inserts_count,
        already_existing=already_existing_count,
        total_db_records=total_db_count,
        opensearch_indexed=sink_accepted_count,
        websocket_broadcast=sink_accepted_count,
        filtered_routine=filtered_routine_count,
        media_discovered=total_media_discovered,
    )

    overall_status = "SUCCESS" if sources_succeeded_count > 0 else ("PARTIAL_SUCCESS" if sources_skipped_count > 0 else "NO_DATA")

    return {
        "status": overall_status,
        "sources_attempted": len(target_sources),
        "sources_succeeded": sources_succeeded_count,
        "sources_skipped": sources_skipped_count,
        "sources_failed": sources_failed_count,
        "sources_triggered": len(results),
        "collected": total_collected,
        "published_raw": total_published_raw if settings.KAFKA_ENABLED else total_collected,
        "spark_processed": spark_processed_count,
        "ai_evaluated": ai_evaluated_count,
        "jev_accepted": jev_accepted_count,
        "jev_rejected": jev_rejected_count,
        "processed_by_sink": sink_accepted_count,
        "new_inserts": new_inserts_count,
        "already_existing": already_existing_count,
        "total_db_records": total_db_count,
        "persisted": new_inserts_count,
        "opensearch_indexed": sink_accepted_count,
        "websocket_broadcast": sink_accepted_count,
        "filtered_routine": filtered_routine_count,
        "media_discovered": total_media_discovered,
        "warnings": warnings,
        "source_breakdown": source_breakdown,
        "sources": results,
        "total_stored": sink_accepted_count,
        "total_published": total_published_raw if settings.KAFKA_ENABLED else total_collected,
        "kafka_status": "Connected" if settings.KAFKA_ENABLED else "Local / DB Mode",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }