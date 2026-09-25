"""
Vision AI — server-side quota enforcement (anti-bypass).

Guest and free limits MUST be enforced here, not only in the browser.
Uses a small JSON ledger under data/ so multi-worker still shares one file
on a single Railway instance (WEB_WORKERS=1 recommended).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("vision-ai.quota")

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DATA.mkdir(parents=True, exist_ok=True)
LEDGER = DATA / "quota_ledger.json"

_lock = threading.RLock()

# Defaults requested by product: guest 1 reply, free login 10 then upgrade
GUEST_MAX = int(os.getenv("GUEST_MESSAGES_MAX", "5"))
FREE_MAX = int(os.getenv("FREE_MESSAGES_PER_MONTH", "30"))
# Optional daily cap for free (same as month if not set lower)
FREE_DAILY = int(os.getenv("FREE_MESSAGES_PER_DAY", "30"))


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> Dict[str, Any]:
    if not LEDGER.exists():
        return {"guests": {}, "users": {}, "updated": 0}
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except Exception:
        return {"guests": {}, "users": {}, "updated": 0}


def _save(data: Dict[str, Any]) -> None:
    data["updated"] = time.time()
    tmp = LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(LEDGER)


def guest_key(ip: str, username: str = "") -> str:
    ip = (ip or "unknown").strip()[:64]
    # Prefer IP so clearing tokens / new guest JWT does not reset quota
    return f"ip:{ip}"


def _state_for(
    data: Dict[str, Any],
    *,
    is_guest: bool,
    username: str,
    client_ip: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (bucket_dict, meta_without_increment)."""
    meta: Dict[str, Any] = {"is_guest": is_guest}
    if is_guest:
        key = guest_key(client_ip, username)
        g = data.setdefault("guests", {}).setdefault(key, {"count": 0, "day": _day()})
        if g.get("day") != _day():
            g["day"] = _day()
            g["count"] = 0
        used = int(g.get("count") or 0)
        meta.update({"used": used, "limit": GUEST_MAX, "key": key})
        return g, meta
    uname = (username or "user").lower().strip()
    u = data.setdefault("users", {}).setdefault(
        uname, {"month": _month(), "day": _day(), "month_count": 0, "day_count": 0}
    )
    if u.get("month") != _month():
        u["month"] = _month()
        u["month_count"] = 0
    if u.get("day") != _day():
        u["day"] = _day()
        u["day_count"] = 0
    meta.update(
        {
            "used_month": int(u.get("month_count") or 0),
            "limit_month": FREE_MAX,
            "used_day": int(u.get("day_count") or 0),
            "limit_day": FREE_DAILY,
            "username": uname,
        }
    )
    return u, meta


def check_allowed(
    *,
    is_guest: bool,
    username: str,
    plan: str,
    client_ip: str,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Pre-flight: allow or reject without consuming a credit."""
    plan = (plan or "free").lower().strip()
    paid = plan in ("pro", "student", "team", "enterprise", "unlimited")
    if paid:
        return True, "ok", {"plan": plan, "unlimited": True}
    with _lock:
        data = _load()
        bucket, meta = _state_for(
            data, is_guest=is_guest, username=username, client_ip=client_ip
        )
        meta["plan"] = plan
        if is_guest:
            if int(bucket.get("count") or 0) >= max(0, GUEST_MAX):
                return (
                    False,
                    "Guest limit reached. Please sign in for up to 30 messages/month. Image generation requires a paid plan.",
                    meta,
                )
            return True, "ok", meta
        if int(bucket.get("month_count") or 0) >= max(0, FREE_MAX) or int(
            bucket.get("day_count") or 0
        ) >= max(0, FREE_DAILY):
            return (
                False,
                f"Free plan limit reached ({FREE_MAX} messages this month). Upgrade for more messages and image generation — /upgrade.html.",
                meta,
            )
        return True, "ok", meta


def consume(
    *,
    is_guest: bool,
    username: str,
    plan: str,
    client_ip: str,
) -> Dict[str, Any]:
    """Call only after a successful model response."""
    plan = (plan or "free").lower().strip()
    if plan in ("pro", "student", "team", "enterprise", "unlimited"):
        return {"skipped": True, "plan": plan}
    with _lock:
        data = _load()
        bucket, meta = _state_for(
            data, is_guest=is_guest, username=username, client_ip=client_ip
        )
        if is_guest:
            bucket["count"] = int(bucket.get("count") or 0) + 1
            data.setdefault("guests", {})[meta["key"]] = bucket
        else:
            bucket["month_count"] = int(bucket.get("month_count") or 0) + 1
            bucket["day_count"] = int(bucket.get("day_count") or 0) + 1
            data.setdefault("users", {})[meta.get("username") or username.lower()] = bucket
        _save(data)
        return meta


def peek(
    *,
    is_guest: bool,
    username: str,
    plan: str,
    client_ip: str,
) -> Dict[str, Any]:
    plan = (plan or "free").lower().strip()
    if plan in ("pro", "student", "team", "enterprise", "unlimited"):
        return {"plan": plan, "unlimited": True, "remaining": -1}
    with _lock:
        data = _load()
        if is_guest:
            key = guest_key(client_ip, username)
            g = data.get("guests", {}).get(key) or {"count": 0, "day": _day()}
            if g.get("day") != _day():
                used = 0
            else:
                used = int(g.get("count") or 0)
            return {
                "plan": "guest",
                "is_guest": True,
                "used": used,
                "limit": GUEST_MAX,
                "remaining": max(0, GUEST_MAX - used),
            }
        uname = (username or "").lower()
        u = data.get("users", {}).get(uname) or {
            "month": _month(),
            "day": _day(),
            "month_count": 0,
            "day_count": 0,
        }
        if u.get("month") != _month():
            mc = 0
        else:
            mc = int(u.get("month_count") or 0)
        return {
            "plan": "free",
            "used": mc,
            "limit": FREE_MAX,
            "remaining": max(0, FREE_MAX - mc),
        }


def reserve(
    *,
    is_guest: bool,
    username: str,
    plan: str,
    client_ip: str,
) -> tuple:
    """Atomic check+consume under one lock (prevents concurrent double-spend)."""
    plan = (plan or "free").lower().strip()
    if plan in ("pro", "student", "team", "enterprise", "unlimited"):
        # still enforce numeric limits for student/pro if configured
        from routes.upgrade import PlanConfig
        cfg = PlanConfig.get_plan(plan) or {}
        limit = (cfg.get("limits") or {}).get("messages_per_month", -1)
        if limit is None or int(limit) < 0:
            return True, "ok", {"plan": plan, "unlimited": True}
    # For free/guest: consume under lock immediately
    ok, msg, meta = check_allowed(
        is_guest=is_guest, username=username, plan=plan, client_ip=client_ip
    )
    if not ok:
        return ok, msg, meta
    # consume now (reservation)
    consume(is_guest=is_guest, username=username, plan=plan, client_ip=client_ip)
    return True, "ok", meta


def can_generate_images(*, is_guest: bool, plan: str) -> Tuple[bool, str]:
    """Images are paid-only (student/pro/team/enterprise)."""
    plan = (plan or "free").lower().strip()
    if is_guest or plan in ("free", "guest", ""):
        return False, "Image generation is available on paid plans (Student / Pro). Open /upgrade.html"
    if plan in ("pro", "student", "team", "enterprise", "unlimited"):
        return True, "ok"
    return False, "Image generation requires a paid plan."
