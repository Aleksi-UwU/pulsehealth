---
last_mapped_commit: b50f312119162bd0faea8034ca2ed1cb5f59b76f
last_mapped_at: 2026-10-21
---
# Technology Stack

**Analysis Date:** 2026-10-21

## Languages

**Primary:**
- Python 3.14 - Backend REST API, SQLite database abstraction, Google Gemini SDK interface (`backend/app.py`, `backend/database.py`, `backend/ai_coach.py`, `backend/openfoodfacts.py`)
- JavaScript (ES6+ Vanilla) - Client-side reactive PWA engine, camera barcode scanner, SVG Activity Rings rendering (`frontend/js/app.js`, `frontend/sw.js`)
- HTML5 & CSS3 - Mobile PWA layout, Dynamic Island safe-area accommodation, Apple Health OLED dark theme (`frontend/index.html`, `frontend/css/styles.css`)

**Secondary:**
- Shell / Batch - Windows 1-click startup automation (`run.bat`, `start_server.py`)
- Markdown - Documentation, Apple Shortcuts specifications, deployment architecture (`README.md`, `shortcuts/Apple_Health_Sync_Shortcut.md`)

## Runtime

**Environment:**
- Python 3.14.7 64-bit on Windows (development)
- Vercel Serverless Python Runtime (`@vercel/python` on AWS Lambda, production)

**Package Manager:**
- Pip 26.2.1
- Lockfile: `requirements.txt` (present at root and `backend/requirements.txt`)

## Frameworks

**Core:**
- FastAPI 0.156.8 - High-performance ASGI web framework providing routing, JSON validation, and static file serving (`backend/app.py`)
- Starlette 1.7.0 - Underlying ASGI toolkit handling static file mounts and streaming responses (`backend/app.py`)
- Pydantic 2.13.5 - Request/response data models and type enforcement (`backend/app.py`)

**Testing:**
- Python standard library & custom integration suite (`test_system.py`)

**Build/Dev:**
- Uvicorn 0.54.0 - Lightning-fast ASGI web server with auto-reload (`start_server.py`)
- Vercel CLI / Vercel Serverless Builder - Cloud serverless packaging and edge distribution (`vercel.json`, `api/index.py`)

## Key Dependencies

**Critical:**
- `google-genai` (v2.32.0) - Official Google Gemini API client for multimodal vision meal analysis, natural language food parsing, and adaptive exercise prescriptions (`backend/ai_coach.py`)
- `requests` (v2.34.2) - Synchronous HTTP client querying the Open Food Facts API and Google Generative Language REST endpoints (`backend/openfoodfacts.py`, `backend/ai_coach.py`)
- `sqlite3` (Python Standard Library) - Zero-configuration embedded relational database with thread-safe connection pooling and upsert support (`backend/database.py`)
- `pillow` (v12.3.0) - Python imaging library used for PWA icon rendering and image verification

**Infrastructure:**
- `python-multipart` (v0.0.32) - Form-data parser enabling file uploads for camera food plate photos (`backend/app.py`)
- `httpx` (v0.28.1) - HTTP client utilized by google-genai and FastAPI testing harnesses

## Configuration

**Environment:**
- `GEMINI_API_KEY`: API key for Gemini 3.8 Flash and Gemini 3.5 Flash-Lite
- `VERCEL`: Automatic environment flag on Vercel serverless runtime to switch SQLite storage path from local repo to `/tmp/health_journey.db`

**Build:**
- `vercel.json` - Specifies `@vercel/python` builder targeting `api/index.py` and global route rewrites
- `frontend/manifest.json` - PWA web manifest defining standalone portrait orientation, theme color `#08090d`, and Apple touch icons
- `frontend/sw.js` - Service worker handling caching for offline PWA startup

## Platform Requirements

**Development:**
- Windows 10/11 or macOS/Linux with Python 3.10+
- Local Wi-Fi network or Tailscale mesh for LAN iPhone pairing

**Production:**
- Vercel Serverless (Primary public deployment at `https://pulsehealth-jade.vercel.app`)
- Compatible with Render, Railway, or Docker containers with persistent volume support

---

*Stack analysis: 2026-10-21*
