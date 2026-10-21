---
last_mapped_commit: b50f312119162bd0faea8034ca2ed1cb5f59b76f
last_mapped_at: 2026-10-21
---
# External Integrations

**Analysis Date:** 2026-10-21

## APIs & External Services

**Artificial Intelligence & Vision:**
- Google Gemini API (`generativelanguage.googleapis.com/v1beta`) - Powers natural language food meal parsing, computer vision photo plate macro estimation, daily recovery-aware workout prescriptions, and conversational fitness chat.
  - SDK/Client: `google-genai` (v2.32.0) and resilient `requests` REST client (`backend/ai_coach.py`)
  - Models: `gemini-3.5-flash-lite` (primary low-latency workhorse), `gemini-3.8-flash` (reasoning fallback), `gemini-flash-latest`
  - Auth: `GEMINI_API_KEY` (injected via environment variable)

**Food & Nutrition Databases:**
- Open Food Facts API (`world.openfoodfacts.org/api/v2`) - Provides crowd-sourced, verified nutritional facts for global packaged food barcodes (UPC / EAN-13).
  - SDK/Client: Custom HTTP client with compliant custom User-Agent header in `backend/openfoodfacts.py`
  - Auth: None (free public open database)
  - Data returned: Product name, brand, serving size, calories (kcal), protein (g), carbohydrates (g), fat (g), dietary fiber (g), and product image URL.

## Data Storage

**Databases:**
- SQLite 3 (Embedded relational database)
  - Connection: Local disk `backend/health_journey.db` (local development) or `/tmp/health_journey.db` (Vercel serverless environment)
  - Client: Python standard library `sqlite3` with `check_same_thread=False` and `Row` dictionary factory (`backend/database.py`)
  - Schema: `user_profile`, `health_metrics`, `food_logs`, `workouts`, `ai_recommendations`

**File Storage:**
- Local filesystem / Serverless memory only: Uploaded food plate photos are parsed in-memory as byte streams by `UploadFile` and forwarded as base64 payloads to Gemini Vision without permanent disk persistence, preventing storage bloat (`backend/app.py`, `backend/ai_coach.py`).

**Caching:**
- Browser ServiceWorker cache (`pulsehealth-v1`) for offline PWA static asset loading (`frontend/sw.js`).
- In-memory chat history in client session (`frontend/js/app.js`).

## Authentication & Identity

**Auth Provider:**
- Shared Token Webhook Authentication (`backend/app.py`, `backend/database.py`).
  - Implementation: User profile generates a unique `sync_token` (`health-sync-token-12345`). Incoming payloads from Apple Shortcuts must supply this token in the JSON body or header to write health telemetry to the database.

## Monitoring & Observability

**Error Tracking:**
- Console error logging and FastAPI HTTP exception handlers (`HTTPException` with explicit status codes: 401, 404, 500 in `backend/app.py`).

**Logs:**
- Uvicorn access and application logs in stdout/stderr.
- Vercel Function runtime logs available in the Vercel project dashboard.

## CI/CD & Deployment

**Hosting:**
- Vercel (`https://pulsehealth-jade.vercel.app`) - Edge CDN for static PWA assets and serverless Python execution for `/api/*` endpoints.

**CI Pipeline:**
- GitHub automatic deployment integration: Git pushes to `main` branch on `https://github.com/Aleksi-UwU/pulsehealth` trigger instant builds on Vercel.

## Environment Configuration

**Required env vars:**
- `GEMINI_API_KEY`: Required for AI meal parsing, photo vision analysis, and workout generation.
- `VERCEL`: Provided automatically by Vercel to route SQLite writes to `/tmp`.

**Secrets location:**
- Local development: Environment variables or shell session.
- Production: Vercel Project Settings ➔ **Environment Variables**.

## Webhooks & Callbacks

**Incoming:**
- `POST /api/sync/health`: Ingests real-time biometric telemetry from the iPhone 16 Pro Max and Apple Watch Series 10 via the native Apple Shortcuts automation (`shortcuts/Apple_Health_Sync_Shortcut.md`).
  - Payload attributes: `active_calories`, `resting_calories`, `steps`, `exercise_minutes`, `stand_hours`, `resting_heart_rate`, `hrv_ms`, `sleep_hours`, `weight_kg`.

**Outgoing:**
- None.

---

*Integration audit: 2026-10-21*
