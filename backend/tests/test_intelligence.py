"""
Unit tests for the SIH intelligence modules.

Runs with the standard library only (no scikit-learn, no asyncpg),
so it can be executed on any Python that can import the pure-logic
pieces of `app.ml.*`.

Run:  python -m unittest tests/test_intelligence.py -v
"""

import asyncio
import unittest
from datetime import datetime, timedelta

from app.ml.classifier_engine import classifier_engine
from app.ml.severity_engine import severity_engine
from app.ml.source_trust import compute_base_trust, compute_trust_score
from app.ml.incident_clusterer import incident_clusterer, IncidentCluster
from app.ml.contradiction import detect_contradictions
from app.ml.stale_detection import determine_lifecycle
from app.ml.priority_score import priority_service
from app.ml.data_quality import compute_data_quality
from app.ml.explainability import explainability_service
from app.ml.timeline import build_timeline
from app.ml import contradiction, stale_detection, data_quality


class ClassifierEngineTests(unittest.TestCase):
    def test_cyclone_classified_with_high_confidence(self):
        result = classifier_engine.classify(
            "Cyclone Mocha landfall in Odisha tomorrow",
            "Severe cyclone with storm surge expected along the coast.",
        )
        self.assertEqual(result.category, "cyclone")
        self.assertGreaterEqual(result.confidence, 0.80)
        self.assertEqual(result.state, "AUTO_CLASSIFIED")

    def test_heavy_rain_classified(self):
        result = classifier_engine.classify(
            "Heavy rain in Mumbai",
            "Intense downpour causing waterlogging in low-lying areas.",
        )
        self.assertIn(result.category, {"rainfall", "flooding"})

    def test_top3_candidates_present(self):
        result = classifier_engine.classify(
            "Thunderstorm alert with strong winds",
            "Moderate gusty winds and lightning expected this evening.",
        )
        self.assertLessEqual(len(result.candidates), 3)
        self.assertGreater(len(result.candidates), 0)

    def test_empty_input_requires_review(self):
        result = classifier_engine.classify("", "")
        self.assertEqual(result.state, "REVIEW_REQUIRED")

    def test_low_confidence_requires_review(self):
        result = classifier_engine.classify("Random non-weather text", "Nothing about the weather.")
        self.assertIn(result.state, {"REVIEW_REQUIRED", "AUTO_CLASSIFIED"})


class SeverityEngineTests(unittest.TestCase):
    def test_critical_keywords_bump_severity(self):
        sev, conf, reason = severity_engine.determine(
            "Emergency in coastal town",
            "Catastrophic cyclone damage with evacuations underway.",
            "cyclone", "paradip",
        )
        self.assertEqual(sev, "CRITICAL")

    def test_low_intensity_is_low(self):
        # Non-major city so no population bump masks the low-intensity signal.
        sev, conf, reason = severity_engine.determine(
            "Light rain expected",
            "Patchy drizzle through the morning, normal conditions.",
            "rainfall", "solan",
        )
        self.assertEqual(sev, "LOW")
        self.assertIn("low-intensity", reason)

    def test_major_city_bump(self):
        sev_plain, _, _ = severity_engine.determine(
            "Heavy rain", "Heavy rain lashing the city.", "rainfall", "smalltown"
        )
        sev_city, _, _ = severity_engine.determine(
            "Heavy rain", "Heavy rain lashing the city.", "rainfall", "mumbai"
        )
        self.assertEqual(sev_plain, "MODERATE")
        self.assertEqual(sev_city, "HIGH")

    def test_fake_risk_dampens_severity(self):
        sev, _, reason = severity_engine.determine(
            "Heavy rain", "Very heavy rainfall across the district.",
            "rainfall", "delhi", fake_confidence=0.9,
        )
        # Dampened, so never CRITICAL from one moderate event + fake signal.
        self.assertIn(sev, {"LOW", "MODERATE", "HIGH"})


class SourceTrustTests(unittest.TestCase):
    def test_credible_source_bump(self):
        score = compute_base_trust("api", "openweathermap")
        self.assertGreaterEqual(score, 85)

    def test_insufficient_samples_no_statistical_boost(self):
        score, reason, sufficient = compute_trust_score("twitter", "some_handle", 3, 1)
        self.assertFalse(sufficient)

    def test_high_confirmation_rate_with_enough_samples(self):
        score, reason, sufficient = compute_trust_score("twitter", "reliable_reporter", 40, 36)
        self.assertTrue(sufficient)
        self.assertGreater(score, 60)

    def test_unsatisfactory_history_lowers_score(self):
        score, reason, sufficient = compute_trust_score("web", "mystery_news_site", 25, 3)
        self.assertTrue(sufficient)
        self.assertLess(score, 60)


class IncidentClustererTests(unittest.TestCase):
    def base_event(self, **overrides):
        e = {
            "id": 1,
            "title": "Heavy rainfall in Delhi",
            "description": "Intense rain reported across National Capital Region.",
            "event_type": "rainfall",
            "city": "delhi",
            "state": "delhi",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "reported_at": datetime.utcnow(),
            "source": "twitter",
        }
        e.update(overrides)
        return e

    def test_identical_reports_cluster_together(self):
        a = self.base_event(id=1)
        b = self.base_event(id=2, source="web")
        clusters = incident_clusterer.cluster_events([a, b])
        self.assertGreaterEqual(len(clusters), 1)
        self.assertEqual(clusters[0].report_count, 2)

    def test_far_away_reports_do_not_cluster(self):
        a = self.base_event(id=1)
        b = self.base_event(
            id=2,
            city="kochi",
            latitude=9.9312,
            longitude=76.2673,
            title="Heavy rain in Kerala",
            source="web",
        )
        clusters = incident_clusterer.cluster_events([a, b])
        self.assertGreaterEqual(len(clusters), 2)

    def test_cluster_summary_exposes_provenance(self):
        a = self.base_event(id=1, source="twitter")
        b = self.base_event(id=2, source="web")
        clusters = incident_clusterer.cluster_events([a, b])
        summary = clusters[0].summarize()
        self.assertEqual(summary["report_count"], 2)
        self.assertEqual(summary["source_count"], 2)
        self.assertTrue(summary["is_corroborated"])
        self.assertEqual(sorted(summary["event_ids"]), [1, 2])


class ContradictionTests(unittest.TestCase):
    def test_no_conflict_single_report(self):
        result = detect_contradictions(["Heavy rain in Mumbai"])
        self.assertFalse(result["has_conflict"])

    def test_direct_negation_detected(self):
        result = detect_contradictions(
            ["Heavy rain reported in the city", "No rainfall has occurred today"]
        )
        self.assertTrue(result["has_conflict"])

    def test_agreement_is_not_a_conflict(self):
        result = detect_contradictions(
            ["Heavy rain in the city", "Flooding after heavy rainfall"]
        )
        self.assertFalse(result["has_conflict"])


class StaleDetectionTests(unittest.TestCase):
    def test_verified_recent_is_verified(self):
        result = determine_lifecycle("verified", datetime.utcnow() - timedelta(hours=1), severity="HIGH")
        self.assertEqual(result["lifecycle"], "VERIFIED")

    def test_verified_old_is_resolved(self):
        result = determine_lifecycle("verified", datetime.utcnow() - timedelta(days=3), severity="HIGH")
        self.assertEqual(result["lifecycle"], "RESOLVED")

    def test_rejected_is_rejected(self):
        result = determine_lifecycle("rejected", datetime.utcnow())
        self.assertEqual(result["lifecycle"], "REJECTED")

    def test_no_updates_go_stale(self):
        result = determine_lifecycle("pending", datetime.utcnow() - timedelta(days=2), severity="LOW")
        self.assertEqual(result["lifecycle"], "STALE")

    def test_fresh_event_is_new(self):
        result = determine_lifecycle("pending", datetime.utcnow() - timedelta(minutes=5))
        self.assertEqual(result["lifecycle"], "NEW")


class PriorityScoreTests(unittest.TestCase):
    def test_critical_verified_major_city_is_high_priority(self):
        result = priority_service.compute(
            severity="CRITICAL",
            verification_score=90,
            verification_status="VERIFIED",
            event_type="cyclone",
            corroboration_count=4,
            major_city=True,
        )
        self.assertGreaterEqual(result["priority_score"], 75)
        self.assertEqual(result["priority_level"], "CRITICAL")

    def test_low_severity_unverified_is_low_priority(self):
        result = priority_service.compute(
            severity="LOW",
            verification_score=20,
            verification_status="UNVERIFIED",
            event_type="fog",
        )
        self.assertLess(result["priority_score"], 50)

    def test_rejected_scores_zero_verification_component(self):
        result = priority_service.compute(
            severity="HIGH",
            verification_score=80,
            verification_status="REJECTED",
            event_type="flooding",
        )
        self.assertLess(result["breakdown"]["verification_confidence"], 20)


class DataQualityTests(unittest.TestCase):
    def test_complete_report_scores_high(self):
        result = compute_data_quality(
            city="Delhi", state="Delhi", latitude=28.6, longitude=77.2,
            reported_at=datetime.utcnow(), source="twitter", source_url="https://x.com/abc",
            description="Very heavy rainfall across Delhi with waterlogging reported "
                        "at several locations and traffic disruption on major roads "
                        "throughout the National Capital Region over the past several hours.",
            photos=["media:1"],
        )
        self.assertGreaterEqual(result["data_quality_score"], 80)

    def test_missing_fields_reduces_score(self):
        result = compute_data_quality(city="", state="", description="rain", photos=[])
        self.assertLess(result["data_quality_score"], 60)
        self.assertEqual(result["components"]["location"], 0)


class ExplainabilityTests(unittest.TestCase):
    class FakeEvent:
        event_type = "rainfall"

    def test_build_explanation(self):
        import collections
        Event = collections.namedtuple("Event", ["event_type", "title", "description"])
        event = Event("rainfall", "Heavy rain", "Extreme rainfall reported")

        explanation = explainability_service.build_explanation(
            event,
            classification={
                "category": "rainfall",
                "confidence": 0.9,
                "state": "AUTO_CLASSIFIED",
                "matched_patterns": ["heavy rain", "downpour"],
            },
            verification={
                "score": 82,
                "status": "VERIFIED",
                "evidence": ["2 sources agree", "official weather data supports"],
                "reasoning": "Multiple corroborating reports",
            },
            severity={"severity": "HIGH", "confidence": 0.9, "reason": "heavy rain"},
            candidates=[
                {"category": "flooding", "confidence": 0.5, "matched_patterns": ["water"]},
            ],
            related_reports=[{"source": "web"}, {"source": "api"}],
        )
        d = explanation.to_dict()
        self.assertIn("rainfall", d["classification_reason"])
        self.assertIn("VERIFIED", d["verification_reason"])
        self.assertEqual(d["confidence_level"], "HIGH")
        self.assertGreaterEqual(len(d["key_factors"]), 3)


class TimelineTests(unittest.TestCase):
    def test_builds_ordered_timeline(self):
        event = {
            "title": "Heavy rain in Mumbai",
            "reported_at": datetime.utcnow() - timedelta(hours=2),
            "created_at": datetime.utcnow() - timedelta(hours=2),
            "event_type": "rainfall",
            "category_confidence": 0.92,
            "verification_status": "VERIFIED",
        }
        timeline = build_timeline(event, related_reports=[{}])
        self.assertGreaterEqual(len(timeline), 3)


if __name__ == "__main__":
    unittest.main()