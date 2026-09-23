"""Local token / cost / resource expenditure tracker per thread and profile."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_PATH = Path(__file__).resolve().parent.parent / "data" / "cost_tracker.json"
_PATH.parent.mkdir(parents=True, exist_ok=True)

# rough USD per 1M tokens (illustrative defaults)
RATES = {
    "groq": 0.10,
    "deepseek": 0.27,
    "openrouter": 0.50,
    "gemini": 0.35,
    "auto": 0.30,
    "local": 0.0,
}

_STATE: Dict[str, Any] = {"threads": {}, "profiles": {}, "total_tokens": 0, "total_cost_usd": 0.0}


def _load():
    global _STATE
    if _PATH.exists():
        try:
            _STATE = json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass


def _save():
    try:
        _PATH.write_text(json.dumps(_STATE, indent=2), encoding="utf-8")
    except Exception:
        pass


_load()


def estimate_tokens(text: str) -> int:
    return max(0, len(text or "") // 4)


def record(
    thread_id: str = "local",
    profile: str = "auto",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cpu_ms: float = 0.0,
) -> Dict[str, Any]:
    profile = (profile or "auto").lower()
    tokens = int(prompt_tokens) + int(completion_tokens)
    rate = RATES.get(profile, RATES["auto"])
    cost = (tokens / 1_000_000.0) * rate
    with _LOCK:
        th = _STATE.setdefault("threads", {}).setdefault(thread_id, {
            "tokens": 0, "cost_usd": 0.0, "calls": 0, "cpu_ms": 0.0, "last": 0
        })
        pr = _STATE.setdefault("profiles", {}).setdefault(profile, {
            "tokens": 0, "cost_usd": 0.0, "calls": 0
        })
        th["tokens"] += tokens
        th["cost_usd"] += cost
        th["calls"] += 1
        th["cpu_ms"] += float(cpu_ms or 0)
        th["last"] = time.time()
        pr["tokens"] += tokens
        pr["cost_usd"] += cost
        pr["calls"] += 1
        _STATE["total_tokens"] = int(_STATE.get("total_tokens") or 0) + tokens
        _STATE["total_cost_usd"] = float(_STATE.get("total_cost_usd") or 0) + cost
        if th["calls"] % 3 == 0:
            _save()
        return {"tokens": tokens, "cost_usd": round(cost, 6), "thread_total": th["tokens"]}


def snapshot() -> Dict[str, Any]:
    with _LOCK:
        return {
            "ok": True,
            "total_tokens": _STATE.get("total_tokens", 0),
            "total_cost_usd": round(float(_STATE.get("total_cost_usd") or 0), 4),
            "threads": _STATE.get("threads") or {},
            "profiles": _STATE.get("profiles") or {},
            "rates_usd_per_m_tokens": RATES,
        }
