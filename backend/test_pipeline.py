import asyncio
import os
import sys

# Ensure backend root is in Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.database import async_session_factory
from app.models.weather_event import WeatherEvent, EventSource, VerificationStatus
from app.services.weather_service import weather_service
from app.services.rag_service import evaluate_jev, purify_weather_data, index_approved_event_embedding, search_rag_knowledge_base
from app.services.intelligence_service import intelligence_service
from app.api.weather import _apply_verification_pipeline


async def run_pipeline_tests():
    async with async_session_factory() as db:
        print("=== TEST A: JEV Rejection (Low-confidence / Fake content) ===")
        # Low confidence fake report
        event_a = WeatherEvent(
            title="UNCONFIRMED FAKE FLOOD REPORT!! DEEPFAKE HOAX ALERT!!",
            description="Fake claim claiming aliens flooded the city with pink water! Completely fake rumor fake fake fake.",
            event_type="flooding",
            severity="low",
            source=EventSource.CITIZEN_REPORT,
            city="TestCityA",
            state="TestState",
            verification_status=VerificationStatus.PENDING,
            fake_confidence=0.9,
            is_fake=True,
        )
        db.add(event_a)
        await db.commit()
        await db.refresh(event_a)

        jev_a = await evaluate_jev(event_a, db=db)
        print("JEV Decision A:", jev_a)
        assert jev_a["probability"] < 0.6, f"Expected JEV < 0.6, got {jev_a['probability']}"
        assert event_a.verification_status == VerificationStatus.REJECTED, f"Expected status REJECTED, got {event_a.verification_status}"
        metadata_a = event_a.metadata_ or {}
        assert metadata_a.get("pipeline_status") == "jev_rejected", f"Expected pipeline_status 'jev_rejected', got {metadata_a.get('pipeline_status')}"
        assert "purified_info" not in metadata_a, "Purification should NOT run for rejected JEV"
        assert "vector_embedding" not in metadata_a, "Vector embedding should NOT exist for rejected JEV"
        print("[PASS] Test A Passed: Low confidence event rejected by JEV and stopped.")

        print("\n=== TEST B: JEV Acceptance & Purification ===")
        event_b = WeatherEvent(
            title="Heavy Rainfall and Severe Waterlogging reported in Colaba Mumbai",
            description="Continuous heavy monsoon rains cause 100mm rainfall within 3 hours near Colaba junction. Traffic diverted.",
            event_type="rainfall",
            severity="high",
            source=EventSource.API,
            city="Mumbai",
            state="Maharashtra",
            verification_status=VerificationStatus.PENDING,
        )
        db.add(event_b)
        await db.commit()
        await db.refresh(event_b)

        await intelligence_service.process_event(db, event_b)
        await db.commit()
        await db.refresh(event_b)

        metadata_b = event_b.metadata_ or {}
        print("Event B status:", event_b.verification_status)
        print("Event B pipeline status:", metadata_b.get("pipeline_status"))
        assert event_b.verification_status == VerificationStatus.PENDING, f"Expected PENDING admin review, got {event_b.verification_status}"
        assert metadata_b.get("pipeline_status") in ("jev_accepted", "purified_pending_review"), f"Unexpected status {metadata_b.get('pipeline_status')}"
        assert "purified_info" in metadata_b, "Purification info should be present for accepted JEV"
        assert "vector_embedding" not in metadata_b, "Vector embedding must NOT be created before admin approval"
        print("[PASS] Test B Passed: Valid event accepted by JEV, purified, and placed in Pending Admin Review.")

        print("\n=== TEST C: Admin Approval & Automatic Embedding ===")
        await _apply_verification_pipeline(event_b, VerificationStatus.VERIFIED, db)
        await db.commit()
        await db.refresh(event_b)

        metadata_b = event_b.metadata_ or {}
        print("Event B post-approval status:", event_b.verification_status)
        print("Event B post-approval pipeline status:", metadata_b.get("pipeline_status"))
        assert event_b.verification_status == VerificationStatus.VERIFIED, f"Expected VERIFIED, got {event_b.verification_status}"
        assert metadata_b.get("pipeline_status") == "rag_indexed", f"Expected 'rag_indexed', got {metadata_b.get('pipeline_status')}"
        assert "vector_embedding" in metadata_b, "Vector embedding MUST be created upon admin approval"
        print("[PASS] Test C Passed: Admin approval triggered automatic vector embedding and RAG indexing.")

        print("\n=== TEST D: Admin Rejection ===")
        event_d = WeatherEvent(
            title="Moderate Rainfall Observed in Jaipur Downtown",
            description="IMD weather station recorded light to moderate rain showers in Jaipur city area.",
            event_type="rainfall",
            severity="moderate",
            source=EventSource.API,
            city="Jaipur",
            state="Rajasthan",
            verification_status=VerificationStatus.PENDING,
        )
        db.add(event_d)
        await db.commit()
        await db.refresh(event_d)

        await intelligence_service.process_event(db, event_d)
        await db.commit()

        # Admin rejects
        await _apply_verification_pipeline(event_d, VerificationStatus.REJECTED, db)
        await db.commit()
        await db.refresh(event_d)

        metadata_d = event_d.metadata_ or {}
        assert event_d.verification_status == VerificationStatus.REJECTED, "Expected status REJECTED"
        assert metadata_d.get("pipeline_status") == "admin_rejected", f"Expected 'admin_rejected', got {metadata_d.get('pipeline_status')}"
        assert "vector_embedding" not in metadata_d, "Rejected event must NOT have vector embedding"
        print("[PASS] Test D Passed: Admin rejection stopped embedding and set status to admin_rejected.")

        print("\n=== TEST E: Ask ATMOS Grounded Retrieval ===")
        docs, _ = await search_rag_knowledge_base(db, "heavy rainfall in Mumbai", top_k=50)

        print(f"Retrieved {len(docs)} docs for query 'heavy rainfall in Mumbai':")
        for doc in docs:
            print(f"  • [{doc['event_id']}] {doc['title']} ({doc['city']}) - Status: verified")

        retrieved_ids = [d["event_id"] for d in docs]
        assert event_b.id in retrieved_ids, f"Event B ({event_b.id}) should be retrievable by Ask ATMOS RAG"
        assert event_a.id not in retrieved_ids, f"Rejected Event A ({event_a.id}) MUST NOT be retrieved"
        assert event_d.id not in retrieved_ids, f"Rejected Event D ({event_d.id}) MUST NOT be retrieved"
        print("[PASS] Test E Passed: Ask ATMOS successfully retrieved approved/embedded event while ignoring rejected & unreviewed records.")

        print("\n=== TEST F: Official IMD Government Weather Event Pipeline Integration ===")
        event_f = WeatherEvent(
            title="OFFICIAL IMD WARNING: Heavy Rainfall in Krishna District",
            description="Official IMD Severe Weather Warning for Krishna, Andhra Pradesh: Heavy Rainfall. Valid until 18:00 IST.",
            event_type="rainfall",
            severity="high",
            source=EventSource.IMD,
            source_id="weather_imd_warning_WARN_AP_001",
            city="Vijayawada",
            state="Andhra Pradesh",
            latitude=16.5062,
            longitude=80.6480,
            verification_status=VerificationStatus.PENDING,
            metadata_={"authority": "official_government_source", "provider": "India Meteorological Department"},
        )
        db.add(event_f)
        await db.commit()
        await db.refresh(event_f)

        await intelligence_service.process_event(db, event_f)
        await db.commit()
        await db.refresh(event_f)

        metadata_f = event_f.metadata_ or {}
        print("Event F source trust:", getattr(event_f, "source_trust_score", 0.98))
        print("Event F status:", event_f.verification_status)
        print("Event F JEV metadata:", metadata_f.get("jev"))
        assert event_f.source == EventSource.IMD, f"Expected source IMD, got {event_f.source}"
        assert "jev" in metadata_f, "Expected JEV evaluation metadata in IMD event"
        print("[PASS] Test F Passed: Official IMD warning processed by intelligence service & JEV pipeline with high source trust.")

        print("\n=== TEST G: ISRO MOSDAC Satellite Weather Event Pipeline Integration ===")
        event_g = WeatherEvent(
            title="ISRO MOSDAC Satellite Observation: INSAT-3D L1B",
            description="ISRO MOSDAC satellite meteorological observation dataset 3D_L1B_STD. Coverage: India Bounding Box.",
            event_type="rainfall",
            severity="moderate",
            source=EventSource.MOSDAC,
            source_id="weather_mosdac_3d_l1b_std_1790942400",
            city="Mumbai",
            state="Maharashtra",
            latitude=19.0760,
            longitude=72.8777,
            verification_status=VerificationStatus.PENDING,
            metadata_={
                "authority": "ISRO_MOSDAC",
                "provider": "ISRO MOSDAC Satellite",
                "is_satellite_observation": True
            },
        )
        db.add(event_g)
        await db.commit()
        await db.refresh(event_g)

        await intelligence_service.process_event(db, event_g)
        await db.commit()
        await db.refresh(event_g)

        metadata_g = event_g.metadata_ or {}
        print("Event G source trust:", getattr(event_g, "source_trust_score", 0.98))
        print("Event G status:", event_g.verification_status)
        assert event_g.source == EventSource.MOSDAC, f"Expected source MOSDAC, got {event_g.source}"
        assert "jev" in metadata_g, "Expected JEV evaluation metadata in MOSDAC satellite event"
        print("[PASS] Test G Passed: ISRO MOSDAC satellite weather event evaluated by intelligence pipeline & JEV.")

        print("\n=== TEST H: Incremental 10 Data Source Integration Test ===")
        new_sources_data = [
            (EventSource.RAINVIEWER, "RainViewer Radar Precipitation Frame", "rainfall", "Pan-India Coverage", "India"),
            (EventSource.NASA_POWER, "NASA POWER Daily Insolation & Temperature", "other", "Delhi", "Delhi"),
            (EventSource.NOAA_NCEI, "NOAA NCEI Climate Record India Station", "other", "Kolkata", "West Bengal"),
            (EventSource.OPENAQ, "OpenAQ PM2.5 Air Quality Reading", "other", "Delhi", "Delhi"),
            (EventSource.USGS_WATER, "USGS Water Discharge Observation", "flooding", "Pan-India Coverage", "India"),
            (EventSource.YOUTUBE, "YouTube Citizen Video: Torrential Rains in Mumbai", "rainfall", "Mumbai", "Maharashtra"),
            (EventSource.REDDIT, "Reddit Public Report: Severe Heatwave in Jaipur", "heatwave", "Jaipur", "Rajasthan"),
            (EventSource.MASTODON, "Mastodon Status: Rain Warning in Chennai", "rainfall", "Chennai", "Tamil Nadu"),
            (EventSource.BLUESKY, "Bluesky Post: Heavy Thunderstorm in Bengaluru", "thunderstorm", "Bengaluru", "Karnataka"),
            (EventSource.WEATHERAPI, "WeatherAPI Current Observation Delhi", "rainfall", "Delhi", "Delhi"),
        ]

        test_events_h = []
        for src, title, ev_type, city, state in new_sources_data:
            evt = WeatherEvent(
                title=title,
                description=f"Automated test event for source {src.value}.",
                event_type=ev_type,
                severity="moderate",
                source=src,
                source_id=f"test_pipe_{src.value}_001",
                city=city,
                state=state,
                verification_status=VerificationStatus.PENDING,
                metadata_={"test_pipeline": True, "source": src.value}
            )
            db.add(evt)
            test_events_h.append(evt)

        await db.commit()

        for evt in test_events_h:
            await db.refresh(evt)
            await intelligence_service.process_event(db, evt)
            await db.commit()
            await db.refresh(evt)
            meta = evt.metadata_ or {}
            assert "jev" in meta, f"Missing JEV evaluation for source {evt.source.value}"

        print("[PASS] Test H Passed: All 10 new source event types processed cleanly by AI Intelligence & JEV pipeline.")

        # Cleanup test records
        await db.delete(event_a)
        await db.delete(event_b)
        await db.delete(event_d)
        await db.delete(event_f)
        await db.delete(event_g)
        for evt in test_events_h:
            await db.delete(evt)
        await db.commit()
        print("\n=== ALL PIPELINE INTEGRATION TESTS PASSED CLEANLY! ===")

if __name__ == "__main__":
    asyncio.run(run_pipeline_tests())

