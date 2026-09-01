"""
Vision AI — free GPU workers (Colab / Kaggle) with AUTO-REGISTRATION.

Idea:
  Your app (Railway / Render / Docker / Cloudflare tunnel) is the brain.
  Colab/Kaggle start a small server, get a public URL (ngrok), then POST
  themselves to YOUR app. The app stores them and routes chat/images there.

  No need to paste ngrok URLs into .env every time (optional still works).

Env (optional static fallbacks):
  COLAB_WORKER_URL / KAGGLE_WORKER_URL / WORKER_URLS
  COLAB_WORKER_SECRET  (must match worker WORKER_SECRET)
  WORKER_REGISTER_SECRET  (optional extra gate for /api/workers/register)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger("vision-ai.colab_worker")

COLAB_WORKER_SECRET = (os.getenv("COLAB_WORKER_SECRET") or os.getenv("WORKER_SECRET") or "").strip()
REGISTER_SECRET = (os.getenv("WORKER_REGISTER_SECRET") or COLAB_WORKER_SECRET or "").strip()
# Fast defaults — dead ngrok must not block Railway chat for 90s
TIMEOUT_CHAT = float(os.getenv("COLAB_CHAT_TIMEOUT", "22"))
TIMEOUT_IMAGE = float(os.getenv("COLAB_IMAGE_TIMEOUT", "240"))
TIMEOUT_HEALTH = float(os.getenv("COLAB_HEALTH_TIMEOUT", "3"))
WORKER_TTL_SEC = int(os.getenv("WORKER_TTL_SEC", "900"))  # drop if no heartbeat 15 min

_DATA = Path(__file__).resolve().parent.parent / "data" / "workers.json"
_LOCK = threading.RLock()
_live_cache: Dict[str, Any] = {"url": None, "ts": 0.0}
_LIVE_TTL = 45.0  # seconds


def _load() -> List[dict]:
    if not _DATA.exists():
        return []
    try:
        rows = json.loads(_DATA.read_text(encoding="utf-8") or "[]")
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def _save(rows: List[dict]) -> None:
    _DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = _DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    tmp.replace(_DATA)


def _env_urls() -> List[str]:
    urls: List[str] = []
    for key in ("COLAB_WORKER_URL", "KAGGLE_WORKER_URL"):
        v = (os.getenv(key) or "").strip().rstrip("/")
        if v and v not in urls:
            urls.append(v)
    extra = (os.getenv("WORKER_URLS") or "").strip()
    if extra:
        for part in extra.split(","):
            u = part.strip().rstrip("/")
            if u and u not in urls:
                urls.append(u)
    return urls


def _prune(rows: List[dict]) -> List[dict]:
    now = time.time()
    kept = []
    for r in rows:
        last = float(r.get("last_seen") or 0)
        if now - last <= WORKER_TTL_SEC:
            kept.append(r)
    return kept


from services.security import validate_worker_url

def register_worker(
    url: str,
    kind: str = "colab",
    secret: str = "",
    meta: Optional[dict] = None,
) -> dict:
    """Called by Colab/Kaggle after ngrok starts."""
    if not REGISTER_SECRET:
        raise ValueError("WORKER_REGISTER_SECRET (or COLAB_WORKER_SECRET) must be configured")
    import hmac as _hmac
    if not _hmac.compare_digest(str(secret or ""), str(REGISTER_SECRET)):
        raise ValueError("invalid register secret")
    url = (url or "").strip().rstrip("/")
    if not url.startswith("http"):
        raise ValueError("url must be http(s)")
    try:
        url = validate_worker_url(url)
    except ValueError as ve:
        raise ValueError(str(ve)) from ve
    kind = (kind or "colab").lower()[:32]
    now = time.time()
    with _LOCK:
        rows = _prune(_load())
        found = None
        for r in rows:
            if r.get("url") == url:
                found = r
                break
        if found:
            found["last_seen"] = now
            found["kind"] = kind
            found["meta"] = meta or found.get("meta") or {}
            found["status"] = "online"
        else:
            # One active worker per kind: drop older URLs of same kind (ngrok restart)
            rows = [r for r in rows if (r.get("kind") or "") != kind]
            rows.append({
                "url": url,
                "kind": kind,
                "last_seen": now,
                "status": "online",
                "meta": meta or {},
                "registered_at": now,
            })
        _save(rows)
    logger.info(f"Worker registered: {kind} {url}")
    return {"ok": True, "url": url, "kind": kind, "workers": len(rows)}


def heartbeat_worker(url: str, secret: str = "") -> dict:
    """Heartbeat only updates existing workers — never creates (anti-forgery)."""
    if not REGISTER_SECRET:
        raise ValueError("WORKER_REGISTER_SECRET / COLAB_WORKER_SECRET must be set")
    if not _hmac.compare_digest(str(secret or ""), str(REGISTER_SECRET)):
        raise ValueError("invalid secret")
    url = validate_worker_url((url or "").strip().rstrip("/"))
    now = time.time()
    with _LOCK:
        rows = _load()
        for r in rows:
            if r.get("url") == url:
                r["last_heartbeat"] = now
                r["status"] = "online"
                _save(rows)
                return {"ok": True, "url": url, "created": False}
    raise ValueError("unknown worker — register first via POST /api/workers/register")



def unregister_worker(url: str, secret: str = "") -> dict:
    if REGISTER_SECRET and secret != REGISTER_SECRET:
        raise ValueError("invalid secret")
    url = (url or "").strip().rstrip("/")
    with _LOCK:
        rows = [r for r in _load() if r.get("url") != url]
        _save(rows)
    return {"ok": True, "removed": url}


def list_workers() -> dict:
    now = time.time()
    with _LOCK:
        rows = _prune(_load())
        _save(rows)
    env = _env_urls()
    enriched = []
    for r in rows:
        age = now - float(r.get("last_seen") or 0)
        rr = dict(r)
        rr["age_sec"] = int(age)
        # UI hints: fresh <120s, stale 120-150, dead >150
        if age <= 120:
            rr["ui_state"] = "online"
        elif age <= 150:
            rr["ui_state"] = "stale"
        else:
            rr["ui_state"] = "dead"
        enriched.append(rr)
    return {
        "ok": bool(enriched or env),
        "registered": enriched,
        "env_urls": env,
        "ttl_sec": WORKER_TTL_SEC,
        "heartbeat_warn_sec": 120,
        "heartbeat_dead_sec": 150,
    }


def _worker_urls() -> List[str]:
    urls = list(_env_urls())
    with _LOCK:
        rows = _prune(_load())
    for r in rows:
        u = (r.get("url") or "").rstrip("/")
        if u and u not in urls:
            urls.append(u)
    return urls


def is_enabled() -> bool:
    """True only if at least one worker URL is configured (may still be offline)."""
    return bool(_worker_urls())


def is_live() -> bool:
    """True if a worker passed a recent health check (cached)."""
    return bool(_first_live_url())


def _headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if COLAB_WORKER_SECRET:
        h["X-Worker-Secret"] = COLAB_WORKER_SECRET
    return h


def health(url: Optional[str] = None) -> Dict[str, Any]:
    targets = [url] if url else _worker_urls()
    if not targets:
        return {"ok": False, "reason": "no workers registered or configured"}
    results = []
    any_ok = False
    for u in targets:
        try:
            r = requests.get(f"{u}/worker/health", timeout=TIMEOUT_HEALTH, headers=_headers())
            if r.status_code == 200:
                data = r.json() if r.content else {}
                data["ok"] = True
                data["url"] = u
                results.append(data)
                any_ok = True
            else:
                results.append({"ok": False, "url": u, "status": r.status_code})
        except Exception as e:
            results.append({"ok": False, "url": u, "error": str(e)})
    return {"ok": any_ok, "workers": results, "count": len(targets)}


def _first_live_url() -> Optional[str]:
    now = time.time()
    cached = _live_cache.get("url")
    if cached and (now - float(_live_cache.get("ts") or 0)) < _LIVE_TTL:
        return cached
    for u in _worker_urls():
        try:
            r = requests.get(f"{u}/worker/health", timeout=TIMEOUT_HEALTH, headers=_headers())
            if r.status_code == 200:
                _live_cache["url"] = u
                _live_cache["ts"] = now
                return u
        except Exception:
            continue
    _live_cache["url"] = None
    _live_cache["ts"] = now
    return None


def chat(question: str, context: str = "", model: str = "auto") -> Optional[str]:
    """Chat via Colab worker. Returns None quickly if no live worker (does not block cascade)."""
    if not _worker_urls():
        return None
    live = _first_live_url()
    if not live:
        logger.info("Colab chat skipped — no live worker (fast-fail)")
        return None
    # Only try the live URL (avoid serial timeouts on dead ngrok tunnels)
    try:
        r = requests.post(
            f"{live}/worker/chat",
            json={"question": question, "context": context or "", "model": model},
            headers=_headers(),
            timeout=TIMEOUT_CHAT,
        )
        if r.status_code == 200:
            data = r.json()
            answer = (data.get("answer") or "").strip()
            if len(answer) > 10:
                logger.info(f"Worker chat OK via {live}")
                return answer
        else:
            logger.warning(f"worker chat HTTP {r.status_code}: {r.text[:120]}")
            # Invalidate cache so next call re-probes
            _live_cache["url"] = None
    except Exception as e:
        logger.warning(f"worker chat {live}: {e}")
        _live_cache["url"] = None
    return None


def generate_image(
    prompt: str,
    *,
    width: int = 512,
    height: int = 512,
    steps: Optional[int] = None,
    negative_prompt: str = "",
    guidance: Optional[float] = None,
    seed: Optional[int] = None,
    model_id: Optional[str] = None,
    hf_id: Optional[str] = None,
    lora_id: Optional[str] = None,
    lora_path: Optional[str] = None,
    lora_weight: float = 1.0,
    job_id: Optional[str] = None,
    **extra,
) -> Optional[Dict[str, Any]]:
    """Call Colab/Kaggle worker /worker/image — propagates model/LoRA/seed params."""
    if not _worker_urls():
        return None
    order = _worker_urls()
    live = _first_live_url()
    if live:
        order = [live] + [u for u in order if u != live]
    payload: Dict[str, Any] = {
        "prompt": prompt,
        "width": int(width or 512),
        "height": int(height or 512),
        "negative_prompt": negative_prompt or "",
        "lora_weight": float(lora_weight or 1.0),
    }
    if steps is not None:
        payload["steps"] = int(steps)
    if guidance is not None:
        payload["guidance"] = float(guidance)
    if seed is not None:
        payload["seed"] = int(seed)
    if model_id:
        payload["model_id"] = model_id
    if hf_id:
        payload["hf_id"] = hf_id
    if lora_id:
        payload["lora_id"] = lora_id
    if lora_path:
        payload["lora_path"] = lora_path
    if job_id:
        payload["job_id"] = job_id
    for u in order:
        try:
            r = requests.post(
                f"{u}/worker/image",
                json=payload,
                headers=_headers(),
                timeout=TIMEOUT_IMAGE,
            )
            if r.status_code != 200:
                logger.warning(f"worker image HTTP {r.status_code} via {u}: {r.text[:120]}")
                continue
            data = r.json()
            if data.get("success") and (data.get("image_data") or data.get("image") or data.get("url")):
                if data.get("image_data") and not data.get("image"):
                    data["image"] = data["image_data"]
                    data["data"] = data["image_data"]
                logger.info(f"Worker image OK via {u} size={data.get('size')}")
                return data
        except Exception as e:
            logger.warning(f"worker image {u}: {e}")
            _live_cache["url"] = None
    return None


def generate_images_batch(
    prompts: List[str],
    *,
    width: int = 512,
    height: int = 512,
    steps: Optional[int] = 4,
) -> Optional[Dict[str, Any]]:
    """Call Colab /worker/batch_image — keeps one T4 session busy efficiently."""
    if not _worker_urls() or not prompts:
        return None
    live = _first_live_url()
    urls = [live] if live else _worker_urls()
    payload: Dict[str, Any] = {
        "prompts": [str(p) for p in prompts[:12]],
        "width": int(width or 512),
        "height": int(height or 512),
    }
    if steps is not None:
        payload["steps"] = int(steps)
    for u in urls:
        if not u:
            continue
        try:
            r = requests.post(
                f"{u}/worker/batch_image",
                json=payload,
                headers=_headers(),
                timeout=max(TIMEOUT_IMAGE, 300.0),
            )
            if r.status_code != 200:
                continue
            data = r.json()
            if data.get("success"):
                return data
        except Exception as e:
            logger.warning(f"worker batch_image {u}: {e}")
    return None


def keep_alive_ping() -> Dict[str, Any]:
    return health()


# ---------------------------------------------------------------------------
# Job queue helpers (used by routes/workers.py)
# ---------------------------------------------------------------------------
def pick_worker_for_job(job: Dict[str, Any]) -> Optional[str]:
    """Pick a live worker URL; prefer ones with recent heartbeat."""
    urls = _worker_urls()
    live = _first_live_url()
    if live:
        return live
    return urls[0] if urls else None
