---
last_mapped_commit: b50f312119162bd0faea8034ca2ed1cb5f59b76f
last_mapped_at: 2026-10-21
---
# Coding Conventions

**Analysis Date:** 2026-10-21

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (`backend/app.py`, `backend/database.py`, `backend/ai_coach.py`)
- Web frontend assets: lowercase (`styles.css`, `app.js`, `sw.js`, `manifest.json`)
- Planning & documentation: `UPPERCASE.md` (`STACK.md`, `README.md`)

**Functions:**
- Python: `snake_case()` with descriptive verbs (`get_user_profile()`, `upsert_health_metrics()`, `parse_food_text()`, `fetch_barcode_nutrition()`)
- JavaScript: `camelCase()` with imperative verbs (`loadDashboard()`, `drawAppleRings()`, `startBarcodeScanner()`, `submitAITextFood()`)

**Variables:**
- Python: `snake_case` (`active_calories`, `resting_calories`, `calories_remaining`, `today_food_logs`)
- JavaScript: `camelCase` (`currentTab`, `dashboardData`, `videoStream`, `moveGoal`)
- Constants: `UPPER_SNAKE_CASE` (`DB_PATH`, `OPEN_FOOD_FACTS_URL`, `MODELS_TO_TRY`, `CACHE_NAME`)

**Types & Classes:**
- Python (Pydantic / Models): `PascalCase` (`ProfileUpdateRequest`, `HealthSyncPayload`, `FoodLogItem`, `TextParseRequest`)

## Code Style

**Python Style:**
- PEP 8 compliant, 4-space indentation.
- Type annotations utilized across API request models and core helper signatures (`Dict[str, Any]`, `Optional[float]`).
- Clean inline dictionary mapping and list comprehensions.

**JavaScript Style:**
- 2-space indentation, semi-colon terminated.
- Modern ES6+ features (`async/await`, template literals, arrow functions, destructuring).
- Native DOM queries (`document.getElementById`, `document.querySelectorAll`).
- No external heavy build tools (Webpack, Vite, Babel) — zero compilation overhead.

## Import Organization

**Python Import Order:**
1. Standard library modules (`os`, `sys`, `socket`, `json`, `base64`, `re`, `datetime`, `sqlite3`, `typing`)
2. Third-party packages (`fastapi`, `pydantic`, `requests`, `uvicorn`, `google.genai`)
3. Local application modules (`database`, `openfoodfacts`, `ai_coach`)

Example from `backend/app.py`:

```python
import os
import socket
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

import database as db
import openfoodfacts as off
import ai_coach
```

## Error Handling

**Backend Strategy:**
- Wrap risky I/O (network requests, database operations, JSON decoding) in `try...except` blocks.
- Convert internal exceptions into user-friendly HTTP exceptions with semantic status codes:
  - 400 for malformed input
  - 401 for unauthorized sync token
  - 404 for missing items or unknown barcodes
  - 500 for unrecoverable upstream API failures
- Resilient fallback lists for external APIs: Gemini models fall back across multiple versions (`gemini-3.5-flash-lite` ➔ `gemini-3.8-flash`) before surfacing an error.

**Frontend Strategy:**
- All network `fetch` calls wrapped in `try...catch`.
- Visual user feedback for errors (informative error banners or modal notices instead of silent unhandled promise rejections).

## Logging

**Framework:**
- Standard Python `print()` statements and FastAPI/Uvicorn console logging in development.
- Vercel runtime telemetry captures stdout in production.
- Client uses `console.error()` for debugging network failures.

## Comments

**Guidelines:**
- Maintain high code clarity so self-documenting naming minimizes unnecessary comments.
- Use docstrings for multi-step domain logic (e.g. `recommend_daily_workout_and_deficit` explains physiological principles of HRV recovery and caloric deficits).
- Provide section headers in both backend routes and frontend UI scripts for rapid navigation.

## Function Design

**Size:**
- Single-responsibility functions kept concise (typically under 40 lines).
- Heavy algorithmic or prompt construction logic decoupled into dedicated helpers (`_call_gemini`, `_extract_json`).

**Parameters:**
- Explicit parameter names.
- Optional parameters clearly indicated with default values or `Optional[...]` types.

**Return Values:**
- Predictable dictionary or primitive types (`Dict[str, Any]`, `bool`, `Optional[Dict]`).
- Database functions return dictionary copies of SQLite rows rather than raw cursor tuples.

---

*Convention analysis: 2026-10-21*
