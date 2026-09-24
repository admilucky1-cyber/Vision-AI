"""
Vision AI v5.2 — Routing Profile Analytics
Tracks profile selection counts, latency, and token estimates.
Persists lightly under data/routing_analytics.json
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_PATH = Path(__file__).resolve().parent.parent / "data" / "routing_analytics.json"
_PATH.parent.mkdir(parents=True, exist_ok=True)

_STATE: Dict[str, Any] = {
    "profiles": {},  # id -> {count, total_latency_ms, total_tokens_est, last_used}
    "updated_at": 0,
}


def _load() -> None:
    global _STATE
    if not _PATH.exists():
        return
    try:
        _STATE = json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass


def _save() -> None:
    try:
        _STATE["updated_at"] = time.time()
        _PATH.write_text(json.dumps(_STATE, indent=2), encoding="utf-8")
    except Exception:
        pass


_load()


def record(profile: str, latency_ms: float = 0.0, tokens_est: int = 0) -> None:
    pid = (profile or "auto").strip().lower() or "auto"
    with _LOCK:
        p = _STATE.setdefault("profiles", {}).setdefault(pid, {
            "count": 0,
            "total_latency_ms": 0.0,
            "total_tokens_est": 0,
            "last_used": 0,
        })
        p["count"] += 1
        p["total_latency_ms"] += float(latency_ms or 0)
        p["total_tokens_est"] += int(tokens_est or 0)
        p["last_used"] = time.time()
        if p["count"] % 5 == 0:
            _save()


def snapshot() -> Dict[str, Any]:
    with _LOCK:
        out = []
        for pid, p in sorted((_STATE.get("profiles") or {}).items(), key=lambda x: -x[1].get("count", 0)):
            c = max(1, int(p.get("count") or 0))
            out.append({
                "profile": pid,
                "count": c,
                "avg_latency_ms": round(float(p.get("total_latency_ms") or 0) / c, 1),
                "total_tokens_est": int(p.get("total_tokens_est") or 0),
                "last_used": p.get("last_used"),
            })
        return {"ok": True, "profiles": out, "updated_at": _STATE.get("updated_at")}


def flush() -> None:
    with _LOCK:
        _save()
