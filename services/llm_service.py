"""
Vision AI LLM Service v6.5.0 — proper multi-provider layer.

Features:
- Unified complete() / complete_detailed() API
- Ordered failover with per-provider timeouts
- Provider health snapshot
- Streaming via existing stream_openai_compatible + SSE-friendly generator
- Backend aliases: auto, gemini, groq, deepseek, openrouter, ollama, lmstudio, local
- Backward compatible: delegates to services.llm.ask_ai

Does not replace routes/chat.py orchestration (RAG, YouTube, files) —
this module is the language-model execution layer only.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger("vision-ai.llm-service")


def _version() -> str:
    try:
        p = Path(__file__).resolve().parents[1] / "VERSION"
        if p.exists():
            return p.read_text(encoding="utf-8").strip() or "6.5.0"
    except Exception:
        pass
    return "6.5.0"


@dataclass
class LLMResult:
    text: str
    provider: str = "unknown"
    model: str = ""
    latency_ms: int = 0
    backend_requested: str = "auto"
    ok: bool = True
    error: Optional[str] = None
    attempts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Normalized backend names
BACKEND_ALIASES = {
    "auto": "auto",
    "default": "auto",
    "gemini": "gemini",
    "google": "gemini",
    "groq": "groq",
    "deepseek": "deepseek",
    "openrouter": "openrouter",
    "or": "openrouter",
    "ollama": "ollama",
    "lmstudio": "lmstudio",
    "lm-studio": "lmstudio",
    "local": "ollama",
    "openai-compat": "openai-compat",
    "compat": "openai-compat",
}


def normalize_backend(backend: Optional[str]) -> str:
    b = (backend or "auto").strip().lower()
    return BACKEND_ALIASES.get(b, b)


def provider_status() -> Dict[str, Any]:
    """Snapshot of which providers are configured (keys present / clients ready)."""
    import os
    from services import llm as core

    return {
        "version": _version(),
        "product": "Vision AI",
        "providers": {
            "gemini": {
                "configured": bool(os.getenv("GOOGLE_API_KEY")),
                "client_ready": bool(getattr(core, "GEMINI_AVAILABLE", False)),
                "models": list(getattr(core, "GEMINI_MODELS", {}).keys()),
            },
            "groq": {
                "configured": bool(os.getenv("GROQ_API_KEY")),
                "available": bool(getattr(core, "GROQ_AVAILABLE", False)),
            },
            "deepseek": {
                "configured": bool(os.getenv("DEEPSEEK_API_KEY")),
                "available": bool(getattr(core, "DEEPSEEK_AVAILABLE", False)),
            },
            "openrouter": {
                "configured": bool(os.getenv("OPENROUTER_API_KEY")),
                "available": bool(getattr(core, "OPENROUTER_AVAILABLE", False)),
            },
            "ollama": {
                "base": getattr(core, "OLLAMA_BASE", ""),
                "enabled": bool(getattr(core, "LOCAL_LLM_ENABLED", True)),
            },
            "lmstudio": {
                "base": getattr(core, "LMSTUDIO_BASE", ""),
            },
            "openai_compat": {
                "base": getattr(core, "OPENAI_COMPAT_BASE", "") or None,
                "model": getattr(core, "OPENAI_COMPAT_MODEL", None),
            },
        },
        "backends": sorted(set(BACKEND_ALIASES.values())),
    }


def list_models() -> List[Dict[str, Any]]:
    from services import llm as core
    try:
        return core.list_available_models()
    except Exception as e:
        logger.warning("list_available_models failed: %s", e)
        return []


def complete(
    question: str,
    *,
    context: str = "",
    backend: str = "auto",
    key_overrides: Optional[Dict[str, str]] = None,
    username: Optional[str] = None,
) -> str:
    """Simple string API (chat-compatible)."""
    result = complete_detailed(
        question, context=context, backend=backend, key_overrides=key_overrides, username=username
    )
    return result.text


def complete_detailed(
    question: str,
    *,
    context: str = "",
    backend: str = "auto",
    key_overrides: Optional[Dict[str, str]] = None,
    username: Optional[str] = None,
) -> LLMResult:
    """
    Proper completion with metadata: provider used, latency, attempts.
    Uses core ask_ai failover chain.
    """
    from services import llm as core

    backend = normalize_backend(backend)
    q = (question or "").strip()
    if not q:
        return LLMResult(text="", ok=False, error="empty_question", backend_requested=backend)

    # Optional user policy on system side is applied inside core when streaming;
    # for ask_ai we prepend a light policy marker in context if needed.
    ctx = context or ""
    if username:
        try:
            from services.llm import append_user_policy, get_master_system_prompt
            # policy is normally on system prompt; ask_ai uses assemble_dynamic_prompt —
            # keep username in context tag for analytics only
            ctx = (ctx + f"\n[USER:{username}]").strip()
        except Exception:
            pass

    t0 = time.perf_counter()
    attempts: List[str] = []
    try:
        # ask_ai returns str; some builds return (str, provider) — handle both
        out = core.ask_ai(q, ctx, backend=backend, key_overrides=key_overrides)
        provider = "auto"
        text = out
        if isinstance(out, tuple) and len(out) >= 1:
            text = out[0]
            if len(out) >= 2:
                provider = str(out[1] or "auto")
        text = (text or "").strip()
        try:
            from services.llm import sanitize_model_text
            text = sanitize_model_text(text)
        except Exception:
            pass
        ms = int((time.perf_counter() - t0) * 1000)
        if not text:
            return LLMResult(
                text="I could not get a response from any configured provider. Check API keys in Settings.",
                provider=provider,
                latency_ms=ms,
                backend_requested=backend,
                ok=False,
                error="empty_response",
                attempts=attempts,
            )
        return LLMResult(
            text=text,
            provider=provider,
            latency_ms=ms,
            backend_requested=backend,
            ok=True,
            attempts=attempts,
        )
    except Exception as e:
        ms = int((time.perf_counter() - t0) * 1000)
        logger.exception("complete_detailed failed")
        return LLMResult(
            text=f"LLM error: {e}",
            latency_ms=ms,
            backend_requested=backend,
            ok=False,
            error=str(e),
            attempts=attempts,
        )


def stream_tokens(
    question: str,
    *,
    context: str = "",
    backend: str = "auto",
) -> Generator[Dict[str, Any], None, None]:
    """Yield SSE-style dict events from OpenAI-compatible streamers first, else one-shot."""
    from services import llm as core

    backend = normalize_backend(backend)
    try:
        if hasattr(core, "stream_openai_compatible"):
            for ev in core.stream_openai_compatible(question, context or "", backend=backend):
                yield ev
            return
    except Exception as e:
        logger.debug("stream path failed: %s", e)
        yield {"event": "error", "message": str(e)}

    # Fallback: non-stream complete as single token burst
    result = complete_detailed(question, context=context, backend=backend)
    if result.ok:
        yield {"event": "meta", "provider": result.provider}
        yield {"event": "token", "text": result.text}
        yield {"event": "done", "provider": result.provider}
    else:
        yield {"event": "error", "message": result.error or "failed"}


def test_all() -> Dict[str, Any]:
    from services import llm as core
    results = {}
    for name in ("gemini", "groq", "deepseek", "openrouter"):
        try:
            results[name] = core.test_provider(name)
        except Exception as e:
            results[name] = {"ok": False, "error": str(e)}
    return {"version": _version(), "tests": results}
