# National Weather Intelligence & Verification Platform — SIH Final Report

An AI-powered weather intelligence platform: **COLLECT → UNDERSTAND → CLASSIFY → VERIFY → CORRELATE → SCORE → VISUALIZE → ALERT → EXPLAIN**.

Built as an incremental transformation of the existing `national-weather-platform` codebase — no data reset, no migration rewrite, no broken feature.

---

## 1. Problem Statement

Citizen-sourced and multi-source weather reports are noisy, unverified, contradictory, and unlabelled. Authorities cannot tell a credible cyclone report from a rumour, cannot rank what to act on first, and have no audit trail of *why* an AI made a decision.

## 2. Solution Architecture

```
COLLECT      → ingestion API (citizen / IMD / NDMA / OpenWeather / X)
UNDERSTAND   → data_quality + fake_detector (media/deepfake risk)
CLASSIFY     → classifier_engine (8 event types, top-3 candidates)
VERIFY       → verification_engine (6 evidence signals, weighted)
CORRELATE    → incident_clusterer (spatial/temporal/semantic) + contradiction
SCORE        → source_trust + severity + priority + data_quality (+lifecycle)
VISUALIZE    → incident intelligence page, AI dashboard, map overlays
ALERT        → radius alert engine (existing, re-verified)
EXPLAIN      → explainability "why this score" + audit trail
```

**Human-in-the-loop:** every AI decision is reconstructable; admins can override classification with a reason; original AI state is preserved in the audit trail.

### Backend (FastAPI, PostgreSQL via Neon)
| Module | Role |
|---|---|
| `app/ml/classifier_engine.py` | Lightweight keyword+syntax Naive-Bayes-style classifier (8 types, top-3 candidates, confidence, state) |
| `app/ml/verification_engine.py` | Weighted evidence score: source reliability, cross-source corroboration, geography, time, official reports, media, misinfo penalty |
| `app/ml/source_trust.py` | Per-source trust, stat-significant only (≥10 samples) |
| `app/ml/incident_clusterer.py` | Cluster linked reports ≤20 km / ≤6 h / category + semantics ≥0.45, original reports preserved |
| `app/ml/contradiction.py` | Detects negations/contradicting reports within an incident |
| `app/ml/stale_detection.py` | Lifecycle: NEW → ACTIVE → VERIFIED → RESOLVED / STALE / REJECTED |
| `app/ml/severity_engine.py` | Critical/High/Moderate/Low with low-intensity dampening |
| `app/ml/priority_score.py` | 0–100 action ranking (severity, verification, trust, lifecycle) |
| `app/ml/data_quality.py`, `app/ml/explainability.py`, `app/ml/timeline.py` | Quality, "why", timeline reconstruction |
| `app/services/intelligence_service.py` | Orchestrator (pipeline, lazy compute for historical events, JSON-safe serialization) |
| `app/api/intelligence.py` | Panel / audit / admin classify-override / source health endpoints |
| `app/api/dashboard.py` | New `/api/dashboard/intelligence-summary` |

### Frontend (React + Vite)
- **Incident Intelligence page** (`/events/:id/intelligence`) — AI decision ring, verification breakdown, corroboration, contradiction warnings, priority/lifecycle/quality, processing timeline.
- **AI Intelligence Overview dashboard band** — verification rate, corroboration rate, misinfo count/rate, priority load, top AI-ranked events, source health.
- **Map popups** — verification score ring, classification confidence, lifecycle, deep link to AI page.
- **Admin override modal** — human reclassification with reason + live audit trail.
- **Analytics** — AI Intelligence Insights band (verification/corroboration/misinfo/priority).

## 3. Thresholds & Weights (Configurable)

- Classification: HIGH ≥ 0.80, MEDIUM ≥ 0.60, LOW ≥ 0.40; REVIEW_REQUIRED when < HIGH.
- Verification weights: source reliability 25, corroboration 25, geography 20, temporal 10, official 10, media 5, misinfo −20.
- VERIFIED ≥ 75, PROBABLE ≥ 50, NEEDS_REVIEW ≥ 25, REJECTED when contradicted/fake.
- Clustering: ≤ 20 km, ≤ 6 h, category match, semantic similarity ≥ 0.45.
- Source trust: statistical boost only with ≥ 10 samples.

## 4. Data Integrity Guarantees

- "**Verified**" = evidence meets criteria, never "guaranteed true".
- No fabricated metrics — insufficient data renders as *"Insufficient data"*.
- Every intelligence decision is versioned (`classifier-v2-intelligence`, `intelligence-pipeline-v1`, etc.).
- Reprocessing (lazy compute + override) is additive and immutable in the audit trail.
- Idempotent Alembic migration (`0003_add_intelligence_columns`) — safe to re-run on Neon.

## 5. Verification Results

| Check | Result |
|---|---|
| Backend unit tests (`unittest discover`) | **48 tests, 44 run + 4 skipped, OK** |
| Intelligence test module | 31 tests (classification, verification, trust, clustering, contradiction, stale, severity, priority, quality, explainability, timeline) |
| Backend compileall + app import smoke | Clean; 31 `/api` routes; 5 intelligence routes registered |
| Frontend `vite build` | Green (chunk-size warning pre-existing) |
| Endpoint security review | Panel/source → authenticated; audit + classify override → admin-only; Pydantic-validated input (event_type enum, required reason) |

---

## 6. Where the Existing App Was Extended (no rewrites)

- `WeatherEvent` gained columns: `incident_id`, `verification_score`, `priority_score`, `source_trust_score`, `data_quality_score`, `lifecycle` (+ `to_dict()` exposes intelligence).
- `weather_service.ingest_event` now runs the full pipeline and auto-maps verification status.
- `EventTable`, `Dashboard`, `Analytics`, `AdminPanel`, `WeatherMap`, `App` expanded — existing screens unchanged in behaviour.
- Legacy `categorizer.py`, `fake_detector.py`, `deduplicator.py` retained for backward compatibility.