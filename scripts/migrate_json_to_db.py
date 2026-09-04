#!/usr/bin/env python3
"""Idempotent import of data/users.json into SQLAlchemy users + preferences."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.db import init_db, SessionLocal
from services.models_db import User, UserPreferences
from services.preferences import ensure_preferences


def main() -> int:
    init_db()
    path = ROOT / "data" / "users.json"
    if not path.exists():
        print("No data/users.json — nothing to import")
        return 0
    raw = json.loads(path.read_text(encoding="utf-8"))
    users = raw.get("users") or {}
    db = SessionLocal()
    created = updated = 0
    try:
        for key, u in users.items():
            username = (u.get("username") or key).lower()
            email = (u.get("email") or f"{username}@local").lower()
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                existing.email = email
                existing.full_name = u.get("full_name") or existing.full_name
                if u.get("hashed_password"):
                    existing.password_hash = u["hashed_password"]
                existing.plan = u.get("plan") or existing.plan
                existing.disabled = bool(u.get("disabled", False))
                updated += 1
                user = existing
            else:
                user = User(
                    username=username,
                    email=email,
                    full_name=u.get("full_name") or "",
                    password_hash=u.get("hashed_password") or "",
                    role=u.get("role") or "user",
                    plan=u.get("plan") or "free",
                    disabled=bool(u.get("disabled", False)),
                    google_id=str(u.get("google_id") or ""),
                    messages_this_month=int(u.get("messages_this_month") or 0),
                    usage_month=str(u.get("usage_month") or ""),
                )
                db.add(user)
                db.flush()
                created += 1
            ensure_preferences(db, user)
        db.commit()
        print(f"Migration complete: created={created} updated={updated}")
        return 0
    except Exception as e:
        db.rollback()
        print("Migration failed:", e)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
