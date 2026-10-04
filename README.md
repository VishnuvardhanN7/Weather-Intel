# National Weather Big Data Analytics Platform (PS-26069 Next Architecture Version)

A National Weather Big Data Analytics Platform for India. It centrally stores weather observations from #IMD/social posts, weather-news sites, public APIs, and citizen reports, then applies automated categorization, fake-report scoring, duplicate detection, human verification, and RAG-based AI search.

---

## Incremental Streaming Architecture

```
External Weather Data Sources (Social / X, News Web Scraper, OpenWeather API, Citizen Reports)
        ↓
Data Source Collectors / Ingestion Service
        ↓
Apache Kafka Ingestion Buffer (weather.raw)
        ↓
Apache Spark Processing Layer (Structured Streaming)
        ↓
AI Engine 1: Event Organization (IndicBERT Text Adapter & CLIP Image Adapter + Rule Fallback)
        ↓
AI Engine 2: Fake News Detection (BaseFakeNewsEngine -> ML Fake Detector)
        ↓
AI Engine 3: Deduplication Engine (BaseDeduplicationEngine -> ML Deduplicator)
        ↓
Kafka Clean Buffer (weather.clean)
        ↓
Existing JEV Verification Engine (Joint Verification Evaluation, JEV >= 0.6)
        ↓
Existing LLM Purification Engine
        ↓
Existing Admin Review
        ├── REJECT → Stop / No Embedding (No weather.verified event)
        └── APPROVE
              ↓
          Kafka Verified Topic (weather.verified)
              ↓
          Kafka Connect / JDBC Sink (Optional Infrastructure)
              ↓
          Existing PostgreSQL / Neon Storage (Source of Truth)
              ↓
          Dashboard / Ask ATMOS / RAG Knowledge Base
```

---

## Architecture Components & Role Summary

### 1. Apache Kafka Streaming Backbone
Kafka acts as the real-time buffer backbone. Topics represent distinct processing stages:
- **`weather.raw`**: Ingested unvalidated weather observation payloads from external sources.
- **`weather.clean`**: Normalized, AI-classified, fake-checked, and deduplicated event records.
- **`weather.verified`**: Human-approved, high-confidence events ready for downstream vector indexing and analytics.

*Note*: PostgreSQL/Neon remains the persistent database source of truth. Kafka is not a database replacement.

### 2. Apache Spark Processing Layer
Located at `backend/app/spark/weather_stream_processor.py`:
- Uses **PySpark Structured Streaming** to consume from `weather.raw`.
- Normalizes and validates incoming JSON payloads.
- Orchestrates calling AI Engines 1, 2, and 3.
- Outputs clean events to `weather.clean`.
- Includes a modular Python stream processor fallback if Spark/JVM binaries are absent.

### 3. AI Engine Suite (`backend/app/ai/`)
- **Engine 1 — Event Organization (`event_organization.py`)**:
  - `IndicBERTEventOrganizer`: Multilingual text classification adapter ( rainfall, thunderstorms, flooding, heatwaves, fog, dust storms, strong winds, other).
  - `CLIPEventOrganizer`: Image verification adapter interface.
  - *Fallback*: Rule-based classification reusing existing classifier engine.
- **Engine 2 — Fake News Detection (`fake_news_engine.py`)**:
  - `BaseFakeNewsEngine` wrapping existing `fake_detector.py`.
- **Engine 3 — Deduplication (`deduplication_engine.py`)**:
  - `BaseDeduplicationEngine` wrapping existing `deduplicator.py`.

### 4. Kafka Connect JDBC Sink
Defined in `docker-compose.kafka.yml` and `docker/kafka-connect/jdbc-sink-connector.json` to project `weather.verified` messages into PostgreSQL tables conceptually and locally.

---

## Local Setup & Configuration

### 1. Docker Kafka Infrastructure (KRaft Mode)
To launch Apache Kafka in modern KRaft mode (no Zookeeper required):

```bash
docker-compose -f docker-compose.kafka.yml up -d
```

This starts:
- Kafka Broker (Port 9092)
- Topic Initialization Job (`weather.raw`, `weather.clean`, `weather.verified`)
- Kafka Connect Service (Port 8083)

### 2. Running Backend with Kafka Enabled
In `backend/.env`:
```env
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_RAW_TOPIC=weather.raw
KAFKA_CLEAN_TOPIC=weather.clean
KAFKA_VERIFIED_TOPIC=weather.verified
JEV_THRESHOLD=0.6
```

Start the stream processor, background sink consumer worker & main server:
```bash
cd backend
.\venv\Scripts\python.exe -m app.spark.weather_stream_processor
.\venv\Scripts\python.exe scripts\run_sink_consumer.py
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 3. Running Backend Without Kafka (Fail-Safe Mode)
Set `KAFKA_ENABLED=false` in `backend/.env`.
The backend will automatically bypass Kafka streaming while maintaining complete database ingestion, REST APIs, JEV verification, Admin Review, and Ask ATMOS RAG search.

---

## Verification & Testing Suite

Run all 67 backend unit & integration tests covering Kafka configuration, topic publishing, AI engines, JEV thresholding, admin review, and RAG search:

```bash
cd backend
.\venv\Scripts\python.exe -m pytest tests/
.\venv\Scripts\python.exe test_pipeline.py
```

Build the frontend UI:
```bash
cd frontend
npm run build
```

---

## Multi-Source Big-Data Sources Integration

### 1. OpenWeather API Collector
Fetches real-time weather observations for 50+ Indian cities into `weather.raw`.

### 2. Open-Meteo Collector & Historical Backfill
High-resolution meteorological model aggregator with multi-coordinate batching and historical archive API ingestion.

### 3. India Meteorological Department (IMD) Collector
Official government weather collector fetching observations, city forecasts, district nowcasts, warnings, and public RSS bulletins.

### 4. ISRO MOSDAC Satellite Collector
Meteorological & Oceanographic Satellite Data Archival Centre (MOSDAC), Space Applications Centre, ISRO.

- **Official Documentation**:
  - [MOSDAC Download API Manual](https://mosdac.gov.in/downloadapi-manual)
  - [MOSDAC Data Access Policy](https://mosdac.gov.in/data-access-policy)
  - [MOSDAC Satellite Catalogue](https://mosdac.gov.in/catalog-app/satellite.php)
- **Authentication Requirement**: Valid user registration on the ISRO MOSDAC portal is required for authenticated product catalog discovery and downloads. If credentials are not set, the collector reports `AUTH_REQUIRED` status without generating fake data.
- **Environment Configuration**:
  ```env
  MOSDAC_ENABLED=false
  MOSDAC_USERNAME=your_mosdac_username
  MOSDAC_PASSWORD=your_mosdac_password
  MOSDAC_DATASET_ID=3D_L1B_STD
  MOSDAC_INTERVAL_SECONDS=900
  MOSDAC_BOUNDING_BOX=70.0,8.0,90.0,28.0
  ```
- **NRT vs. Archive Data**:
  - **NRT (Near Real Time)**: Fetches current satellite product passes over India bounding box (`70.0,8.0,90.0,28.0`).
  - **Archive**: Queries historical satellite dataset granules by dataset ID and date range.
- **How to Execute**:
  - Run single cycle: `python scripts/run_mosdac_ingestion.py --once`
  - Run continuous loop (15-min interval): `python scripts/run_mosdac_ingestion.py --interval 15`
  - Docker service: `docker compose -f ./docker/docker-compose.yml up -d mosdac-ingestion`

---

## Complete Multi-Source Big-Data Integration Matrix

| Source | Category | Auth Required | Purpose | Implementation Status | Live Status |
|---|---|---|---|---|---|
| OpenWeather | Weather API | API Key | Live weather observations | IMPLEMENTED | LIVE-VERIFIED |
| Open-Meteo | Weather API | Public / Free | Live + historical archive | IMPLEMENTED | LIVE-VERIFIED |
| IMD | Government | API Key / RSS | Official India weather warnings | IMPLEMENTED | AUTHENTICATION-READY |
| ISRO MOSDAC | Satellite | Account / Credentials | Satellite products & archives | IMPLEMENTED | AUTHENTICATION-READY |
| RainViewer | Radar | Public / API | Radar precipitation frames | IMPLEMENTED | NOT YET VERIFIED |
| NASA POWER | Environmental | Public / API | Solar & climate data | IMPLEMENTED | NOT YET VERIFIED |
| NOAA / NCEI | Climate | API Key | Climate observations | IMPLEMENTED | AUTHENTICATION-READY |
| OpenAQ | Environmental | API Key | Air quality observations | IMPLEMENTED | NOT YET VERIFIED |
| USGS Water | Hydrology | Public / API | River discharge & water levels | IMPLEMENTED | NOT YET VERIFIED |
| YouTube Data API | Social | API Key | Public video reports | IMPLEMENTED | AUTHENTICATION-READY |
| Reddit | Social | OAuth / API Key | Community weather posts | IMPLEMENTED | AUTHENTICATION-READY |
| Mastodon | Social | Access Token | Decentralized social posts | IMPLEMENTED | AUTHENTICATION-READY |
| Bluesky | Social | App Password | Public AT protocol posts | IMPLEMENTED | AUTHENTICATION-READY |
| WeatherAPI.com | Weather API | API Key | Live city observations | IMPLEMENTED | AUTHENTICATION-READY |

---

## Tech Stack

**Backend & Streaming:**
- FastAPI & PySpark Structured Streaming
- Apache Kafka (KRaft mode) & kafka-python-ng
- SQLAlchemy 2.0 (async) + PostgreSQL / Neon
- IndicBERT & CLIP adapter interfaces with ML fallbacks

**Frontend:**
- React 18 + Vite (Vanilla CSS / Tailwind)
- Leaflet maps & Recharts visualization

---

## License
Educational and research project for National Weather Big Data Analytics.

