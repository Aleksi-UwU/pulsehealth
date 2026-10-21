---
last_mapped_commit: b50f312119162bd0faea8034ca2ed1cb5f59b76f
last_mapped_at: 2026-10-21
---
# Testing Patterns

**Analysis Date:** 2026-10-21

## Test Framework

**Runner:**
- Python standard test execution (`python test_system.py`)
- Compatible with `pytest` for automated test discovery

**Assertion Library:**
- Python built-in assertion syntax (`assert condition`, status code checks)

**Run Commands:**

```bash
python test_system.py               # Run full end-to-end integration and smoke suite
python -m pytest                    # (Optional) Run pytest test suite if installed
```

## Test File Organization

**Location:**
- Dedicated root-level test suite: `test_system.py`
- Ad-hoc endpoint verification via FastAPI's `TestClient` (`starlette.testclient`)

**Naming:**
- Test files follow `test_*.py` pattern.

## Test Structure

**Integration & Smoke Pattern (`test_system.py`):**

```python

# 1. Database Initialization

db.init_db()
profile = db.get_profile()
assert profile.get("name") is not None

# 2. Apple Watch Telemetry Sync

mock_metrics = {
    "date": "2026-10-21",
    "steps": 9240,
    "active_calories": 610.0,
    "hrv_ms": 62.0,
    "sleep_hours": 7.6
}
saved_health = db.upsert_health_metrics(mock_metrics)
assert saved_health.get("active_calories") == 610.0

# 3. Food Logging

food_item = db.add_food_log({
    "date": "2026-10-21",
    "meal_type": "breakfast",
    "food_name": "Greek Yogurt",
    "calories": 220,
    "protein_g": 20
})
assert food_item["id"] is not None

# 4. Open Food Facts Barcode Lookup

prod = off.fetch_barcode_nutrition("5449000000996")
assert prod is not None
assert prod["calories"] > 0

# 5. Gemini AI Meal Parsing

parsed_food = ai_coach.parse_food_text("2 eggs, 1 toast")
assert len(parsed_food.get("items", [])) > 0

# 6. Gemini AI Exercise Coach

rec = ai_coach.recommend_daily_workout_and_deficit(profile, saved_health, [food_item], [])
assert rec.get("readiness_score") is not None
```

## Mocking

**Approach:**
- `test_system.py` focuses on real-world grounding: tests live API connectivity to Open Food Facts and Google Gemini API to ensure upstream contracts and API keys are functioning as expected.
- For isolated unit testing without network dependencies, `unittest.mock.patch` can mock `requests.post` and `requests.get` responses in `backend/ai_coach.py` and `backend/openfoodfacts.py`.

## Fixtures and Factories

**Test Payloads:**
- Defined inline within `test_system.py` mimicking realistic Apple Watch Series 10 telemetry:
  - High HRV (>60 ms) & optimal sleep (~7.5 hrs) to test high-readiness resistance training prescriptions.
  - Low HRV (<35 ms) to test active recovery / Zone 2 cardio adaptation.

## Test Types

**Unit Tests:**
- Mifflin-St Jeor BMR calculations in `backend/database.py`.
- JSON string parsing and repair in `backend/ai_coach.py:_extract_json`.
- Barcode response extraction in `backend/openfoodfacts.py`.

**Integration Tests:**
- Multi-component flow in `test_system.py`: SQLite write ➔ Gemini AI analysis ➔ Recommendation persistence.
- FastAPI endpoint test via `TestClient(app)` verifying status 200 on `/` and `/api/dashboard`.

**E2E / Live Verification:**
- Live verification against the production deployment at `https://pulsehealth-jade.vercel.app` via curl probing:
  - Verified `GET /api/profile` (200 OK)
  - Verified `GET /api/dashboard` (200 OK)
  - Verified `POST /api/sync/health` (200 OK)
  - Verified `POST /api/food/parse-text` (200 OK)
  - Verified `POST /api/coach/generate` (200 OK)

---

*Testing analysis: 2026-10-21*
