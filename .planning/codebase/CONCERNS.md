---
last_mapped_commit: b50f312119162bd0faea8034ca2ed1cb5f59b76f
last_mapped_at: 2026-10-21
---
# Codebase Concerns

**Analysis Date:** 2026-10-21

## Tech Debt

**Serverless Database Ephemerality:**
- Issue: On Vercel, the database path defaults to `/tmp/health_journey.db`. While this prevents read-only filesystem crashes, `/tmp` storage is ephemeral and is cleared when Vercel serverless containers cold-start or recycle.
- Files: `backend/database.py` (lines 7–12)
- Impact: Food logs and health metrics logged on Vercel may be reset during container spin-downs unless a persistent cloud database is connected.
- Fix approach: Add a database adapter supporting **Turso** (serverless SQLite over HTTP via `libsql-client`) or **Neon / Supabase** (PostgreSQL) when a `DATABASE_URL` environment variable is detected.

**Single-User Hardcoding:**
- Issue: `user_profile` table enforces `CHECK (id = 1)` as a dedicated personal single-user companion.
- Files: `backend/database.py` (lines 20–35), `backend/app.py`
- Impact: Suitable for a dedicated personal device, but prevents multi-tenant or multi-account usage.
- Fix approach: Decouple user ID from fixed 1 to JWT/session-based user ID if multi-user support is desired in the future.

**Static Asset Caching Invalidation:**
- Issue: `frontend/sw.js` uses a static cache key `pulsehealth-v1`. When `styles.css` or `app.js` are updated, users who added the PWA to their iPhone home screen may need to clear their cache or wait for service worker lifecycle re-activation.
- Files: `frontend/sw.js`
- Impact: Stale CSS or JavaScript might temporarily persist on client devices after production deployments.
- Fix approach: Implement automated cache busting (e.g. `styles.css?v=1.1`) or a network-first strategy for script assets.

## Known Bugs & Edge Cases

**Desktop Browser Barcode Support:**
- Symptoms: Camera scanner opens video stream but fails to decode barcode frames on certain desktop browsers (Firefox desktop).
- Files: `frontend/js/app.js` (lines 280–325)
- Trigger: Browsers lacking native implementation of `window.BarcodeDetector`.
- Workaround: Modern iOS 17+ Safari on the user's iPhone 16 Pro Max has full hardware-accelerated `BarcodeDetector` support. On unsupported browsers, the manual barcode input box or AI text logging provides immediate fallback.

**Regional Food Database Coverage:**
- Symptoms: Scanning hyper-local or artisanal food items may return "Product not found" from Open Food Facts.
- Files: `backend/openfoodfacts.py`
- Trigger: Packaged items not yet indexed in Open Food Facts' open database.
- Workaround: UI prompts user to use the **✨ AI Food Log** instead, which uses Gemini to analyze any dish from natural text or plate photos.

## Security & Secrets

**Default Sync Token:**
- Issue: Default seed configuration sets `sync_token` to `'health-sync-token-12345'`.
- Files: `backend/database.py:27`
- Impact: Anyone discovering the public endpoint could potentially post mock health metrics if token verification is enabled with default credentials.
- Fix approach: Prompt user to change their sync token in the Settings tab and update their Apple Shortcut accordingly.

---

*Concerns analysis: 2026-10-21*
