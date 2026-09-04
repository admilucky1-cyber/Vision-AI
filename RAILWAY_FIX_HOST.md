# Railway 400 + router fix (2026-09-03)

## Symptoms
- `GET /` → 400 Bad Request while uvicorn is running
- Logs: `name 'get_current_active_user' is not defined` for upload/studio/models/RAG/engine

## Fixes in this package
1. **TrustedHost** — auto-allow `*`, `*.up.railway.app`, and `RAILWAY_PUBLIC_DOMAIN`
2. **upload.py** — import `get_current_active_user` (was missing)
3. **skills/studio/models/agent** — safe try/except import of auth dependency

## Railway variables
```
ALLOWED_HOSTS=*
```
Optional:
```
RAILWAY_PUBLIC_DOMAIN=web-production-XXXX.up.railway.app
CORS_ORIGINS=https://web-production-XXXX.up.railway.app
```

Start command: `python run.py`  
Health: `/health`
