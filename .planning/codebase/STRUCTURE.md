---
last_mapped_commit: b50f312119162bd0faea8034ca2ed1cb5f59b76f
last_mapped_at: 2026-10-21
---
# Codebase Structure

**Analysis Date:** 2026-10-21

## Directory Layout

```text
Health app/
├── api/                        # Vercel serverless deployment entry points
│   └── index.py                # Serverless ASGI bridge to FastAPI application
├── backend/                    # Python backend application core
│   ├── ai_coach.py             # Gemini API integration & exercise prescription engine
│   ├── app.py                  # FastAPI router, endpoints, request schemas, static mount
│   ├── database.py             # SQLite database layer, schema, queries, and migrations
│   ├── health_journey.db       # Local SQLite database file (created on runtime)
│   ├── openfoodfacts.py        # Open Food Facts barcode lookup client
│   └── requirements.txt        # Backend dependencies
├── frontend/                   # Progressive Web App client (served as static assets)
│   ├── css/
│   │   └── styles.css          # Apple Health dark OLED CSS, safe-area layout, animations
│   ├── icons/
│   │   ├── icon-192.png        # Standard PWA launcher icon
│   │   └── icon-512.png        # High-res splash & home screen icon
│   ├── js/
│   │   └── app.js              # Client state, SVG ring math, barcode scanner, UI modals
│   ├── index.html              # Mobile PWA single-page layout
│   ├── manifest.json           # Web app manifest for iOS home-screen installation
│   └── sw.js                   # Service worker for offline asset caching
├── shortcuts/                  # iOS Automation definitions
│   └── Apple_Health_Sync_Shortcut.md # Step-by-step Apple Shortcuts setup for Apple Watch
├── .gitignore                  # Git exclusions for secrets, local databases, and caches
├── README.md                   # Project overview, installation, and user instructions
├── requirements.txt            # Root dependencies mirror for Vercel builds
├── run.bat                     # Windows 1-click execution script
├── start_server.py             # Local network IP detector and Uvicorn development launcher
├── test_system.py              # End-to-end integration and verification script
└── vercel.json                 # Vercel serverless build and routing configuration
```

## Directory Purposes

**`api/`:**
- Purpose: Serverless entry points required by cloud platforms.
- Contains: Single lightweight adapter `api/index.py` that puts `backend/` into `sys.path` and exposes `app`.

**`backend/`:**
- Purpose: All server-side business logic, database queries, and external API connectors.
- Contains: Pure Python modules (`app.py`, `database.py`, `ai_coach.py`, `openfoodfacts.py`).
- Key files: `backend/app.py` (main API dispatcher), `backend/database.py` (data access layer).

**`frontend/`:**
- Purpose: Client-side single-page Progressive Web App running in iOS Safari and desktop browsers.
- Contains: Native web standards (HTML5, modern CSS3, ES6 JavaScript) without heavyweight frontend bundlers or frameworks.
- Key files: `frontend/index.html` (DOM skeleton), `frontend/js/app.js` (client state and event handlers), `frontend/css/styles.css` (design system).

**`shortcuts/`:**
- Purpose: Integration bridge for Apple ecosystem.
- Contains: Setup instructions, step-by-step action guides, and dictionary mappings for Apple HealthKit telemetry.

## Key File Locations

**Entry Points:**
- `start_server.py`: Local developer launcher initializing network discovery and Uvicorn.
- `api/index.py`: Serverless entry point for Vercel/AWS Lambda.
- `frontend/index.html`: Web client root.

**Configuration:**
- `vercel.json`: Cloud deployment and rewrite routing rules.
- `frontend/manifest.json`: iOS PWA standalone configuration.
- `requirements.txt`: Python package specifications.

**Core Logic:**
- `backend/app.py`: Endpoint definition and HTTP request dispatching.
- `backend/database.py`: Relational database operations and BMR/TDEE math.
- `backend/ai_coach.py`: Prompt engineering, Gemini API calls, and workout recommendation algorithms.

**Testing:**
- `test_system.py`: End-to-end smoke test suite verifying database, health sync, barcode lookup, and Gemini AI.

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g. `ai_coach.py`, `openfoodfacts.py`)
- Web files: `kebab-case` or lowercase (e.g. `index.html`, `styles.css`, `manifest.json`)
- Documentation: `UPPERCASE.md` or `CamelCase.md` (e.g. `README.md`, `Apple_Health_Sync_Shortcut.md`)

**Directories:**
- Lowercase alphanumeric: `api`, `backend`, `frontend`, `css`, `js`, `icons`, `shortcuts`

## Where to Add New Code

**New API Endpoint / Feature:**
- Add request/response Pydantic models and route handler to `backend/app.py`.
- If database persistence is required, add helper functions and SQL queries to `backend/database.py`.
- Update client API client routines in `frontend/js/app.js`.

**New AI Coach Capability:**
- Add specialized prompt function and schema extractor in `backend/ai_coach.py`.
- Expose the corresponding route in `backend/app.py`.

**New Client UI View / Tab:**
- Add new `<section class="tab-content" id="tab-<name>">` in `frontend/index.html`.
- Add tab button in `<nav class="nav-bar">` in `frontend/index.html`.
- Implement rendering and state updates in `frontend/js/app.js`.

**Shared Utilities:**
- Backend utilities belong in a new helper module in `backend/` or as clean functions in `backend/database.py`.
- Frontend utilities belong at the bottom of `frontend/js/app.js`.

## Special Directories

**`.planning/`:**
- Purpose: Project roadmap, codebase maps, and planning specifications.
- Generated: Managed by GSD workflows.
- Committed: Yes.

**`backend/__pycache__/`:**
- Purpose: Compiled Python bytecode.
- Generated: Automatically by Python interpreter.
- Committed: No (excluded via `.gitignore`).

---

*Structure analysis: 2026-10-21*
