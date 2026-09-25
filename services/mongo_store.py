"""
Optional MongoDB store for Vision AI.

Env:
  MONGODB_URI   e.g. mongodb+srv://user:pass@cluster/dbname
  MONGODB_DB    default: vision_ai

If URI is missing or pymongo is not installed, is_available() is False
and callers should use SQLite/Postgres (services.db) as before.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vision.mongo")

_client = None
_db = None
_init_error: Optional[str] = None


def _uri() -> str:
    return (
        os.getenv("MONGODB_URI")
        or os.getenv("MONGO_URL")
        or os.getenv("MONGO_URI")
        or ""
    ).strip()


def is_configured() -> bool:
    return bool(_uri())


def is_available() -> bool:
    global _client, _db, _init_error
    if not is_configured():
        return False
    if _db is not None:
        return True
    try:
        from pymongo import MongoClient  # type: ignore
    except ImportError:
        _init_error = "pymongo not installed"
        logger.warning("MongoDB configured but pymongo missing — pip install pymongo")
        return False
    try:
        uri = _uri()
        _client = MongoClient(uri, serverSelectionTimeoutMS=4000)
        _client.admin.command("ping")
        name = (os.getenv("MONGODB_DB") or "vision_ai").strip() or "vision_ai"
        _db = _client[name]
        _init_error = None
        logger.info("MongoDB connected: db=%s", name)
        return True
    except Exception as e:
        _init_error = str(e)
        _client = None
        _db = None
        logger.warning("MongoDB unavailable: %s", e)
        return False


def status() -> Dict[str, Any]:
    ok = is_available()
    return {
        "configured": is_configured(),
        "available": ok,
        "error": None if ok else _init_error,
        "db": (os.getenv("MONGODB_DB") or "vision_ai") if is_configured() else None,
        "backend": "mongodb" if ok else "sql_fallback",
    }


def save_chat_event(
    *,
    user_id: str,
    chat_id: str,
    role: str,
    text: str,
    meta: Optional[Dict[str, Any]] = None,
) -> bool:
    if not is_available() or _db is None:
        return False
    try:
        _db.chat_events.insert_one(
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "role": role,
                "text": (text or "")[:50000],
                "meta": meta or {},
                "ts": datetime.now(timezone.utc),
            }
        )
        return True
    except Exception as e:
        logger.warning("mongo save_chat_event failed: %s", e)
        return False


def list_chat_events(user_id: str, chat_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    if not is_available() or _db is None:
        return []
    try:
        cur = (
            _db.chat_events.find({"user_id": user_id, "chat_id": chat_id})
            .sort("ts", 1)
            .limit(max(1, min(limit, 500)))
        )
        out = []
        for doc in cur:
            doc["_id"] = str(doc.get("_id"))
            ts = doc.get("ts")
            if hasattr(ts, "isoformat"):
                doc["ts"] = ts.isoformat()
            out.append(doc)
        return out
    except Exception as e:
        logger.warning("mongo list_chat_events failed: %s", e)
        return []


def upsert_user_profile(user_id: str, profile: Dict[str, Any]) -> bool:
    if not is_available() or _db is None:
        return False
    try:
        profile = dict(profile or {})
        profile["user_id"] = user_id
        profile["updated_at"] = datetime.now(timezone.utc)
        _db.users.update_one({"user_id": user_id}, {"$set": profile}, upsert=True)
        return True
    except Exception as e:
        logger.warning("mongo upsert_user_profile failed: %s", e)
        return False
