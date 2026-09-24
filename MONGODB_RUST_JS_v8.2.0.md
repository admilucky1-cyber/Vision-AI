# Vision AI v8.2.0 — MongoDB + Rust + JS

## MongoDB (optional)
- Service: `services/mongo_store.py`
- Status API: `GET /api/mongo/status`
- Env: `MONGODB_URI` (or `MONGO_URL`), optional `MONGODB_DB=vision_ai`
- Without URI → SQLite/Postgres unchanged

## Rust
- Unchanged: `native/pii_redactor` (memory-safe redaction)
- Not a Mongo driver in this release (Python owns DB I/O)

## JS
- `frontend/static/js/mongo-status.js` — badge: DB · SQL / DB · Mongo

## Railway
```
MONGODB_URI=mongodb+srv://...
MONGODB_DB=vision_ai
```
Also: `pip install pymongo` (listed in requirements.txt)
