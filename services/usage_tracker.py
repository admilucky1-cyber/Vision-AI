"""
Vision AI — lightweight usage analytics
Stores daily counters in data/usage.json (runtime, gitignored).
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vision-ai.usage")

_DATA = Path(__file__).resolve().parent.parent / "data" / "usage.json"
_LOCK = threading.RLock()

_COST = {
    "message": 0.002,
    "image": 0.04,
}


def _today() -> str:
    return date.today().isoformat()


def _empty_day(d: str) -> Dict[str, Any]:
    return {
        "date": d,
        "users": 0,
        "messages": 0,
        "images": 0,
        "unique_users": [],
        "saved_usd": 0.0,
        "providers": {},
    }


def _load() -> Dict[str, Any]:
    if not _DATA.exists():
        return {"days": {}, "totals": {"users": 0, "messages": 0, "images": 0, "saved_usd": 0.0}}
    try:
        data = json.loads(_DATA.read_text(encoding="utf-8") or "{}")
        if not isinstance(data, dict):
            return {"days": {}, "totals": {"users": 0, "messages": 0, "images": 0, "saved_usd": 0.0}}
        data.setdefault("days", {})
        data.setdefault("totals", {"users": 0, "messages": 0, "images": 0, "saved_usd": 0.0})
        return data
    except Exception as e:
        logger.warning(f"usage load failed: {e}")
        return {"days": {}, "totals": {"users": 0, "messages": 0, "images": 0, "saved_usd": 0.0}}


def _save(data: Dict[str, Any]) -> None:
    try:
        _DATA.parent.mkdir(parents=True, exist_ok=True)
        tmp = _DATA.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(_DATA)
    except Exception as e:
        logger.warning(f"usage save failed: {e}")


def _touch_day(data: Dict[str, Any], d: str) -> Dict[str, Any]:
    days = data.setdefault("days", {})
    if d not in days:
        days[d] = _empty_day(d)
    day = days[d]
    day.setdefault("unique_users", [])
    day.setdefault("providers", {})
    day.setdefault("saved_usd", 0.0)
    return day


def _track_user(day: Dict[str, Any], data: Dict[str, Any], user_id: Optional[str]) -> None:
    if not user_id:
        return
    uid = str(user_id)[:64]
    users = day.get("unique_users") or []
    if uid not in users:
        users.append(uid)
        day["unique_users"] = users[-500:]
        day["users"] = len(day["unique_users"])
        data["totals"]["users"] = int(data["totals"].get("users") or 0) + 1


def record_message(user_id: Optional[str] = None, provider: str = "") -> None:
    with _LOCK:
        data = _load()
        d = _today()
        day = _touch_day(data, d)
        day["messages"] = int(day.get("messages") or 0) + 1
        data["totals"]["messages"] = int(data["totals"].get("messages") or 0) + 1
        day["saved_usd"] = float(day.get("saved_usd") or 0) + _COST["message"]
        data["totals"]["saved_usd"] = float(data["totals"].get("saved_usd") or 0) + _COST["message"]
        if provider:
            day["providers"][provider] = int(day["providers"].get(provider) or 0) + 1
        _track_user(day, data, user_id)
        _save(data)


def record_image(user_id: Optional[str] = None, provider: str = "") -> None:
    with _LOCK:
        data = _load()
        d = _today()
        day = _touch_day(data, d)
        day["images"] = int(day.get("images") or 0) + 1
        data["totals"]["images"] = int(data["totals"].get("images") or 0) + 1
        day["saved_usd"] = float(day.get("saved_usd") or 0) + _COST["image"]
        data["totals"]["saved_usd"] = float(data["totals"].get("saved_usd") or 0) + _COST["image"]
        if provider:
            key = f"img:{provider}"
            day["providers"][key] = int(day["providers"].get(key) or 0) + 1
        _track_user(day, data, user_id)
        _save(data)


def record_session(user_id: Optional[str] = None) -> None:
    with _LOCK:
        data = _load()
        day = _touch_day(data, _today())
        _track_user(day, data, user_id or "anon")
        _save(data)


def get_summary(days: int = 14) -> Dict[str, Any]:
    with _LOCK:
        data = _load()
    all_days: List[Dict[str, Any]] = []
    for d, row in sorted(data.get("days", {}).items()):
        all_days.append(
            {
                "date": d,
                "users": int(row.get("users") or len(row.get("unique_users") or [])),
                "messages": int(row.get("messages") or 0),
                "images": int(row.get("images") or 0),
                "saved_usd": round(float(row.get("saved_usd") or 0), 4),
                "providers": row.get("providers") or {},
            }
        )
    recent = all_days[-max(1, days) :]
    totals = data.get("totals") or {}
    today_row = next((r for r in recent if r["date"] == _today()), None) or {
        "date": _today(),
        "users": 0,
        "messages": 0,
        "images": 0,
        "saved_usd": 0.0,
    }
    return {
        "today": today_row,
        "recent_days": recent,
        "totals": {
            "users": int(totals.get("users") or 0),
            "messages": int(totals.get("messages") or 0),
            "images": int(totals.get("images") or 0),
            "saved_usd": round(float(totals.get("saved_usd") or 0), 4),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


__all__ = ["record_message", "record_image", "record_session", "get_summary"]
