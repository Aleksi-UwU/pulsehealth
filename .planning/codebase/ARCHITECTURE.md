---
last_mapped_commit: b50f312119162bd0faea8034ca2ed1cb5f59b76f
last_mapped_at: 2026-10-21
---
<!-- refreshed: 2026-10-21 -->

# Architecture

**Analysis Date:** 2026-10-21

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 iPhone 16 Pro Max & Safari Mobile PWA                       │
├─────────────────────┬───────────────────────────┬───────────────────────────┤
│   Activity Rings    │    AI Food / Barcode      │    AI Health & Deficit    │
│    `frontend/`      │   `frontend/js/app.js`    │   Coach `frontend/js/`    │
└──────────┬──────────┴─────────────┬─────────────┴─────────────┬─────────────┘
           │                        │                           │
           ▼                        ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FastAPI ASGI Service (`backend/app.py`)                  │
│       Served via Uvicorn locally or `@vercel/python` in Serverless Cloud    │
└──────────┬────────────────────────┬───────────────────────────┬─────────────┘
           │                        │                           │
           ▼                        ▼                           ▼
┌─────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│  SQLite Persistence │  │   Google Gemini API    │  │  Open Food Facts API   │
│`backend/database.py`│  │ `backend/ai_coach.py`  │  │`backend/openfoodfacts` │
└─────────────────────┘  └────────────────────────┘  └────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **API Server & Routing** | Defines REST endpoints, validates payloads with Pydantic, mounts static PWA, handles CORS | `backend/app.py` |
| **Database & ORM** | Manages SQLite connection pooling, tables, migrations, upserts, and Mifflin-St Jeor BMR calculations | `backend/database.py` |
| **AI Nutrition & Coach** | Integrates with Google Gemini API for structured JSON meal parsing, multimodal vision, and workout prescriptions | `backend/ai_coach.py` |
| **Barcode Nutrition** | Fetches and formats food package data from Open Food Facts REST service | `backend/openfoodfacts.py` |
| **Vercel Adapter** | Bridges Vercel serverless request handling with the internal FastAPI application | `api/index.py` |
| **PWA Client App** | Manages DOM updates, user state, tab switching, camera barcode scanning, and SVG rings | `frontend/js/app.js` |
| **Styles & Themes** | Provides Apple Health dark OLED aesthetics, safe-area inset margins for Dynamic Island, and animations | `frontend/css/styles.css` |
| **Shortcut Automation** | Defines the native Apple Shortcuts pipeline querying HealthKit on iOS and posting JSON | `shortcuts/Apple_Health_Sync_Shortcut.md` |

## Pattern Overview

**Overall:** Lightweight Layered Monolith / Modern Client-Side PWA + Headless ASGI Backend.

**Key Characteristics:**
- **Decoupled Client & Server**: The frontend is a static Progressive Web App interacting exclusively via clean JSON REST APIs.
- **Dynamic Serverless Resilience**: Storage automatically falls back between persistent local disk (`backend/health_journey.db`) and ephemeral cloud container paths (`/tmp/health_journey.db`) depending on the execution environment.
- **Model Fallback Chain**: AI requests attempt low-latency `gemini-3.5-flash-lite` first, automatically degrading to `gemini-3.8-flash` or `gemini-flash-latest` in case of transient 503 capacity spikes.

## Layers

**Presentation Layer (PWA):**
- Purpose: Delivers an app-store quality mobile user interface on iOS Safari with offline capability.
- Location: `frontend/index.html`, `frontend/css/styles.css`, `frontend/js/app.js`, `frontend/sw.js`
- Contains: HTML structure, glassmorphic CSS, vanilla JavaScript state managers, SVG ring calculators.
- Depends on: Backend REST endpoints (`/api/dashboard`, `/api/food/*`, `/api/coach/*`).
- Used by: End user via iPhone 16 Pro Max Safari or desktop browser.

**API & Routing Layer:**
- Purpose: Ingestion, parameter deserialization, schema validation, and routing.
- Location: `backend/app.py`, `api/index.py`
- Contains: FastAPI router, Pydantic models (`HealthSyncPayload`, `FoodLogItem`, `TextParseRequest`).
- Depends on: `backend/database.py`, `backend/ai_coach.py`, `backend/openfoodfacts.py`.
- Used by: Mobile PWA and Apple Shortcuts webhook.

**Domain & Intelligence Layer:**
- Purpose: Nutritional calculations, macronutrient balancing, and Gemini prompt synthesis.
- Location: `backend/ai_coach.py`, `backend/openfoodfacts.py`
- Contains: Prompt engineering templates, Gemini REST calling routines, JSON extraction and repair helpers.
- Depends on: Google Gemini API, Open Food Facts API.
- Used by: `backend/app.py`.

**Data Access Layer:**
- Purpose: CRUD operations, transactional safety, and historical data retrieval.
- Location: `backend/database.py`
- Contains: SQLite schema definitions, table creation, idempotent upsert queries, and connection factories.
- Depends on: Python standard `sqlite3` and filesystem.
- Used by: `backend/app.py`.

## Data Flow

### 1. Apple Health Ingestion Flow

1. User completes workout or daily automation triggers on iPhone 16 Pro Max (`shortcuts/Apple_Health_Sync_Shortcut.md`).
2. Native Apple Shortcut queries HealthKit for active calories, resting calories, steps, HRV, sleep, and heart rate.
3. Shortcut posts JSON payload to `POST /api/sync/health` (`backend/app.py:177`).
4. `backend/database.py:upsert_health_metrics` performs an idempotent `ON CONFLICT(date) DO UPDATE` in SQLite.
5. Client PWA re-fetches `/api/dashboard`, dynamically rendering updated Move, Exercise, and Stand rings.

### 2. AI Food Logging Flow

1. User types natural meal description ("2 eggs, whole wheat toast, coffee") in client modal.
2. Client sends payload to `POST /api/food/parse-text` (`backend/app.py:206`).
3. `ai_coach.parse_food_text` formats structured instructions and queries Gemini 3.5 Flash-Lite (`backend/ai_coach.py:75`).
4. Gemini returns itemized calories, protein, carbs, fat, fiber, and dietitian tips.
5. Client previews items and saves to `POST /api/food/log`, immediately recalculating the daily caloric deficit gauge.

### 3. Live Barcode Scan Flow

1. User activates scanner in PWA; camera stream attaches to `<video>` element (`frontend/js/app.js:283`).
2. Hardware-accelerated `BarcodeDetector` decodes UPC/EAN code from video frames.
3. Client requests `GET /api/food/barcode/{code}` (`backend/app.py:236`).
4. `openfoodfacts.fetch_barcode_nutrition` queries Open Food Facts API, normalizing serving sizes and macros (`backend/openfoodfacts.py:9`).
5. Product is displayed in UI for 1-tap addition to breakfast, lunch, dinner, or snacks.

### 4. Recovery & Deficit Workout Prescription Flow

1. User taps "Generate Plan" on Coach tab (`frontend/js/app.js:210`).
2. Server queries today's watch telemetry (HRV, Sleep, Active Energy) and today's total food intake (`backend/app.py:246`).
3. `ai_coach.recommend_daily_workout_and_deficit` evaluates central nervous system readiness:
   - High HRV (>50ms) + 7+ hrs sleep: Prescribes progressive resistance training to spare lean muscle mass.
   - Low HRV (<35ms) or <6 hrs sleep: Prescribes low-impact Zone 2 fat oxidation walk to avoid cortisol spikes.
4. Generates workout routine with sets, reps, and form tips, caching prescription into `ai_recommendations` and `workouts` tables.

## Key Abstractions

**Energy Balance Equation:**
- TDEE (Total Daily Energy Expenditure) = BMR (calculated via Mifflin-St Jeor formula based on age, sex, height, weight) + Active Calories Burned (reported by Apple Watch).
- Net Calorie Balance = Calories Consumed - TDEE.
- Target Deficit = 500 kcal/day (targeting ~0.5 kg / 1.1 lbs fat loss per week).

**CNS Recovery Readiness Score:**
- Evaluated on a 0–100 scale using Heart Rate Variability (HRV SDNN) and sleep duration as primary physiological strain indicators.

## Entry Points

- `backend/app.py`: Core application instantiation (`app = FastAPI(...)`).
- `start_server.py`: Local developer launcher determining LAN IP and booting Uvicorn.
- `api/index.py`: Serverless handler exposed to Vercel/AWS Lambda.
- `frontend/index.html`: Web client root.

## Error Handling

- API endpoints catch unhandled exceptions, returning standard `{ "detail": "..." }` JSON responses with appropriate HTTP status codes (400, 401, 404, 500).
- AI client encapsulates model switching: if a model fails with 503 or 404, it iterates to the next candidate in `MODELS_TO_TRY` before returning an error.
- Camera barcode scanning contains a manual digit entry fallback in case camera permissions are denied.

---

*Architecture analysis: 2026-10-21*
