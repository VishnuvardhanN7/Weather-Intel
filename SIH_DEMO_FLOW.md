# SIH Demo Flow — 8-Minute Script

Live system, real citizen-bearing DB. Start at the deployed URL (Render/Neon backend).

---

## 0. Setup (30s)
- Open two tabs: **Dashboard** and **Admin** (login as admin).
- Pre-seed: 1 IMD cred sample + 1 fake, one low-trust citizen report.

## 1. COLLECT & CLASSIFY (1 min)
- Submit a citizen earthquake/cyclone report via **Report Weather Event**.
- Show the **Incident Intelligence** page (`/events/:id/intelligence`):
  - **AI Decision Ring** → event type + top-3 candidates + confidence.
  - Say: *"The classifier returned 3 candidates with confidence and a decision state — AUTO_CLASSIFIED vs REVIEW_REQUIRED."*

## 2. VERIFY (1 min)
- Add a supporting IMD/NWS/GDACS report for the same location.
- Hit **Refresh** → verification score jumps via cross-source corroboration + official credit.
- Point out the **Why this score** breakdown (weights: source, corroboration, geography, time, official, media, misinfo penalty).
- Note the lifecycle moving NEW → VERIFIED.

## 3. CORRELATE & MISINFO (1.5 min)
- Switch to **Dashboard** → **AI overview**: verification rate, corroboration rate (`incidents`), misinfo count/rate, priority load.
- Open **Analytics** → **AI Intelligence Insights** band shows the same metrics at scale.
- Back on the map, submit a contradictory citizen report → marker popup shows lowered verification ring + **contradiction warning**; verdict NEEDS_REVIEW.

## 4. HUMAN-IN-THE-LOOP OVERRIDE (1.5 min)
- **Admin** → Events (Verification tab, pending) → row **AI Classify** button → choose event type, type a reason.
- Submit → modal shows the **audit trail**: original AI decision → manual decision, admin, timestamp, reason.
- Emphasize: *"The AI's original state is never destroyed — it is preserved in the audit trail for accountability."*

## 5. PRIORITISE & ALERT (1 min)
- Show **Top Priority AI-ranked events** feed on Dashboard — click through to that event's intelligence page.
- Open the affected city; matcher fires the alert to subscribers (existing alert engine).
- Explain: **priority_score = f(severity, verification, source trust, lifecycle).**

## 6. PROVENANCE (1 min)
- Open `/events/:id/intelligence` → **Trusted sources table** (source health): stat-significant source trust only (≥10 samples), "Insufficient data" never fabricated.
- Show **Processing timeline**: collected → normalized → classified → verified → clustered → scored → explained.
- Mention **versioned decisions** (`intelligence-pipeline-v1`, `classifier-v2-intelligence`) → every score is reconstructable.

## 7. CLOSE (30s)
- Numbers ammo: **48 unit tests green**, 8 category classifier, weighted 6-signal verification, ≤20 km/≤6 h clustering, idempotent migration on Neon, zero data reset.
- Hand-off line: *"Verified means evidence-checked, never guaranteed. That's the transparency SIH asks for."*

---

### Failure fallbacks
- If ingest is slow → demo the **admin override + audit**, which only needs 1 event.
- If no clustering → show verification/explainability, then manually corroborate two reports.

### Quick reference: routes
| Route | Purpose |
|---|---|
| `/` , `/dashboard` | AI Intelligence Overview |
| `/events/:id/intelligence` | Per-event AI decision + why |
| `/admin` | Verification queue + AI Classify override |
| `/analytics` | AI Intelligence Insights |
| API | `/api/intelligence/events/{id}`, `/audit`, `/classify`, `/sources` |