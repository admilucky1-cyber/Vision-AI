"""
Vision AI — central model lifecycle registry.
Live discovery + deprecation map + capability metadata.
Do NOT treat archived/static lists as truth without status checks.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vision-ai.model_catalog")

# ---------------------------------------------------------------------------
# Deprecation / migration (authoritative for retired IDs)
# ---------------------------------------------------------------------------
MIGRATIONS: Dict[str, str] = {
    # Groq — retired Aug 2026
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
    "gemma2-9b-it": "openai/gpt-oss-20b",
    # Gemini shut down / legacy
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-1.5-flash": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
    "text-embedding-004": "text-embedding-005",
}

SHUTDOWN: set = {
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "gemini-2.0-flash",
    "text-embedding-004",
}

# Bundled fallbacks when live discovery fails (production defaults only)
GROQ_FALLBACK: List[Dict[str, Any]] = [
    {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B", "tokens": 131_072, "status": "active", "type": "chat", "provider": "groq", "production": True},
    {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B", "tokens": 131_072, "status": "active", "type": "chat", "provider": "groq", "production": True},
    {"id": "groq/compound", "name": "Groq Compound", "tokens": 131_072, "status": "active", "type": "agent", "provider": "groq", "production": True},
    {"id": "groq/compound-mini", "name": "Groq Compound Mini", "tokens": 131_072, "status": "active", "type": "agent", "provider": "groq", "production": True},
]

GEMINI_FALLBACK: List[Dict[str, Any]] = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "tokens": 1_000_000, "status": "active", "type": "chat", "provider": "gemini", "production": True},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "tokens": 1_000_000, "status": "active", "type": "chat", "provider": "gemini", "production": True},
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash-Lite", "tokens": 1_000_000, "status": "active", "type": "chat", "provider": "gemini", "production": True},
]

OPENROUTER_FALLBACK: List[Dict[str, Any]] = [
    {"id": "openai/gpt-oss-20b:free", "name": "GPT-OSS 20B (free)", "tokens": 131_072, "status": "active", "type": "chat", "provider": "openrouter"},
    {"id": "qwen/qwen-2.5-72b-instruct:free", "name": "Qwen 2.5 72B (free)", "tokens": 131_072, "status": "active", "type": "chat", "provider": "openrouter"},
    {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1 (free)", "tokens": 64_000, "status": "active", "type": "reasoning", "provider": "openrouter"},
    {"id": "google/gemma-3-27b-it:free", "name": "Gemma 3 27B (free)", "tokens": 131_072, "status": "active", "type": "chat", "provider": "openrouter"},
]

DEEPSEEK_FALLBACK: List[Dict[str, Any]] = [
    {"id": "deepseek-chat", "name": "DeepSeek Chat", "tokens": 64_000, "status": "active", "type": "chat", "provider": "deepseek"},
    {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "tokens": 64_000, "status": "active", "type": "reasoning", "provider": "deepseek"},
]

_CACHE: Dict[str, Any] = {}
_LOCK = threading.RLock()
_TTL = int(os.getenv("MODEL_CATALOG_TTL_SEC", "600") or 600)


def migrate_model_id(model_id: str) -> str:
    mid = (model_id or "").strip()
    if not mid:
        return mid
    if mid in MIGRATIONS:
        return MIGRATIONS[mid]
    # strip provider prefix variants
    low = mid.lower()
    for old, new in MIGRATIONS.items():
        if low == old or low.endswith("/" + old) or low.endswith(old):
            return new
    return mid


def is_shutdown(model_id: str) -> bool:
    mid = (model_id or "").strip()
    return mid in SHUTDOWN or migrate_model_id(mid) != mid and mid in SHUTDOWN


def _cache_get(key: str) -> Optional[Any]:
    with _LOCK:
        row = _CACHE.get(key)
        if not row:
            return None
        if time.time() - row["ts"] > _TTL:
            return None
        return row["data"]


def _cache_set(key: str, data: Any) -> None:
    with _LOCK:
        _CACHE[key] = {"ts": time.time(), "data": data}


def discover_groq(api_key: str = "") -> List[Dict[str, Any]]:
    key = (api_key or os.getenv("GROQ_API_KEY") or "").strip()
    cached = _cache_get("groq")
    if cached is not None:
        return cached
    models: List[Dict[str, Any]] = []
    if key:
        try:
            import requests
            r = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=8,
            )
            if r.status_code == 200:
                for m in (r.json().get("data") or []):
                    mid = m.get("id") or ""
                    if not mid or mid in SHUTDOWN:
                        continue
                    mid = migrate_model_id(mid)
                    if mid in SHUTDOWN:
                        continue
                    models.append({
                        "id": mid,
                        "name": mid.split("/")[-1],
                        "tokens": 131_072,
                        "status": "active",
                        "type": "chat",
                        "provider": "groq",
                        "production": mid in ("openai/gpt-oss-20b", "openai/gpt-oss-120b", "groq/compound", "groq/compound-mini"),
                    })
        except Exception as e:
            logger.warning("groq discovery: %s", e)
    if not models:
        models = [dict(x) for x in GROQ_FALLBACK]
    # Always ensure production defaults present
    have = {m["id"] for m in models}
    for fb in GROQ_FALLBACK:
        if fb["id"] not in have:
            models.insert(0, dict(fb))
    # Strip any shutdown IDs that slipped in
    models = [m for m in models if m["id"] not in SHUTDOWN]
    _cache_set("groq", models)
    return models


def discover_openrouter(api_key: str = "") -> List[Dict[str, Any]]:
    key = (api_key or os.getenv("OPENROUTER_API_KEY") or "").strip()
    cached = _cache_get("openrouter")
    if cached is not None:
        return cached
    models: List[Dict[str, Any]] = []
    if key:
        try:
            import requests
            r = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10,
            )
            if r.status_code == 200:
                for m in (r.json().get("data") or [])[:80]:
                    mid = m.get("id") or ""
                    if not mid:
                        continue
                    pricing = m.get("pricing") or {}
                    # prefer free or very cheap for catalog subset
                    models.append({
                        "id": mid,
                        "name": m.get("name") or mid,
                        "tokens": int((m.get("context_length") or 0) or 0) or 32_000,
                        "status": "active",
                        "type": "chat",
                        "provider": "openrouter",
                        "pricing": pricing,
                    })
        except Exception as e:
            logger.warning("openrouter discovery: %s", e)
    if not models:
        models = [dict(x) for x in OPENROUTER_FALLBACK]
    _cache_set("openrouter", models)
    return models


def groq_chat_models() -> List[Dict[str, Any]]:
    return [m for m in discover_groq() if m.get("type") in ("chat", "reasoning", "agent") and m["id"] not in SHUTDOWN]


def gemini_chat_models() -> List[Dict[str, Any]]:
    return [dict(x) for x in GEMINI_FALLBACK]


def openrouter_chat_models() -> List[Dict[str, Any]]:
    return discover_openrouter()[:24]


def deepseek_chat_models() -> List[Dict[str, Any]]:
    return [dict(x) for x in DEEPSEEK_FALLBACK]


def default_groq_model() -> str:
    return "openai/gpt-oss-20b"


def default_gemini_model() -> str:
    return "gemini-2.5-flash"


def snapshot(keys: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    keys = keys or {}
    groq = discover_groq(keys.get("GROQ_API_KEY", ""))
    orouter = discover_openrouter(keys.get("OPENROUTER_API_KEY", ""))
    return {
        "ok": True,
        "migrations": dict(MIGRATIONS),
        "shutdown": sorted(SHUTDOWN),
        "providers": {
            "groq": {
                "configured": bool(keys.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")),
                "models": groq,
            },
            "gemini": {
                "configured": bool(keys.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")),
                "models": gemini_chat_models(),
            },
            "openrouter": {
                "configured": bool(keys.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")),
                "models": orouter[:40],
            },
            "deepseek": {
                "configured": bool(keys.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")),
                "models": deepseek_chat_models(),
            },
        },
        "defaults": {
            "groq": default_groq_model(),
            "gemini": default_gemini_model(),
            "auto": "auto",
        },
    }
