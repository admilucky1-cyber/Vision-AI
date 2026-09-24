# Migration Guide — v5.6.2

## Local (SQLite)
```bash
pip install -r requirements.txt
python scripts/migrate_json_to_db.py   # if data/users.json exists
python run.py
```

## PostgreSQL
```bash
export DATABASE_URL=postgresql://user:pass@host:5432/vision_ai
export SECRET_KEY=$(openssl rand -hex 32)
python -c "from services.db import init_db; init_db()"
python scripts/migrate_json_to_db.py
python run.py
```

## Railway
1. Add PostgreSQL plugin → sets `DATABASE_URL`
2. Set `SECRET_KEY`, `ALLOWED_HOSTS=*`, provider API keys
3. Deploy; `init_db()` runs on startup
4. One-off: `python scripts/migrate_json_to_db.py`

## Environment
| Variable | Required | Notes |
|----------|----------|-------|
| SECRET_KEY | Production | Never use default |
| DATABASE_URL | Optional | SQLite if unset |
| ALLOWED_HOSTS | Railway | `*` or your domain |
| ADMIN_USERNAME / ADMIN_PASSWORD | Optional | Seed admin |

JSON users are **not deleted**; DB import is additive/idempotent.
