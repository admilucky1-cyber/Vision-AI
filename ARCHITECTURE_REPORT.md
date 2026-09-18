# Architecture Report — Vision AI v5.6.2

## Old architecture
- Users in `data/users.json` (process-local locks)
- Preferences mostly `localStorage` (browser-scoped)
- Quota/usage partially JSON-based
- Settings UI could look authoritative while state was per-browser

## New architecture (modular monolith)
```
UI → FastAPI → Auth / Settings / Chat / Models / Quota
              → SQLAlchemy → SQLite (dev) | PostgreSQL (prod)
              → AI Router (providers)
```

## Database
- `services/db.py` — engine, sessions, `init_db()`
- `services/models_db.py` — `User`, `UserPreferences`, `RefreshToken`, `UsageEvent`
- Default: SQLite file `data/vision_ai.db`
- Production: `DATABASE_URL=postgresql://...`

## Settings
- Server is source of truth for authenticated users
- `GET/PATCH /api/settings`, `POST /api/settings/reset`, `GET /api/settings/schema`
- Frontend caches to `vision_ai_preferences` + legacy keys for first paint
- `response_style` / `reasoning_level` feed `build_policy_prompt()` for LLM system policy

## Auth
- Existing JWT login retained (`routes/login.py` + JSON user store)
- DB users lazy-created on first settings access from JSON snapshot
- `scripts/migrate_json_to_db.py` for bulk import

## What was not fully replaced
- JSON `UserDatabase` still serves login paths (compatibility)
- Refresh-token rotation table exists; full login rewrite deferred to avoid breaking sessions
- Redis optional; not required for settings

## Principle
Backend owns truth. Frontend presents state. Database persists preferences.
