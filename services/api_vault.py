"""
Vision AI v3.0.1 — API Vault with health-aware fallback and auto-retry.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("vision-ai.api_vault")


class ProviderVault:
    PROVIDERS: Dict[str, Dict[str, Any]] = {
        "openai": {"env": ["OPENAI_API_KEY"], "test_url": "https://api.openai.com/v1/models", "auth": "bearer"},
        "claude": {
            "env": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
            "test_url": "https://api.anthropic.com/v1/models",
            "auth": "x-api-key",
            "extra_headers": {"anthropic-version": "2023-06-01"},
        },
        "grok": {"env": ["XAI_API_KEY", "GROK_API_KEY"], "test_url": "https://api.x.ai/v1/models", "auth": "bearer"},
        "deepseek": {"env": ["DEEPSEEK_API_KEY"], "test_url": "https://api.deepseek.com/models", "auth": "bearer"},
        "gemini": {"env": ["GOOGLE_API_KEY", "GEMINI_API_KEY"], "test_url": None, "auth": "query"},
        "mistral": {"env": ["MISTRAL_API_KEY"], "test_url": "https://api.mistral.ai/v1/models", "auth": "bearer"},
        "huggingface": {"env": ["HF_TOKEN", "HUGGINGFACE_TOKEN"], "test_url": "https://huggingface.co/api/whoami-v2", "auth": "bearer"},
        "replicate": {"env": ["REPLICATE_API_TOKEN"], "test_url": "https://api.replicate.com/v1/account", "auth": "token"},
        "runpod": {"env": ["RUNPOD_API_KEY"], "test_url": "https://api.runpod.ai/v2", "auth": "bearer"},
        "groq": {"env": ["GROQ_API_KEY"], "test_url": "https://api.groq.com/openai/v1/models", "auth": "bearer"},
        "openrouter": {"env": ["OPENROUTER_API_KEY"], "test_url": "https://openrouter.ai/api/v1/models", "auth": "bearer"},
    }

    CHAT_FALLBACK_ORDER: List[str] = [
        "groq", "gemini", "openrouter", "deepseek", "openai", "claude", "mistral", "grok",
    ]

    def __init__(self) -> None:
        self._cache: Dict[str, Optional[str]] = {}
        self._key_lists: Dict[str, List[str]] = {}
        self._key_index: Dict[str, int] = {}
        self._health: Dict[str, str] = {}

    def _collect_keys(self, provider: str) -> List[str]:
        """Collect all keys for a provider: BASE, BASE_1, BASE_2, ... and comma-separated values."""
        if provider in self._key_lists:
            return self._key_lists[provider]
        meta = self.PROVIDERS.get(provider)
        if not meta:
            self._key_lists[provider] = []
            return []
        found: List[str] = []
        seen = set()
        for env_name in meta["env"]:
            # Primary: ENV and ENV_1 .. ENV_20
            for suffix in [""] + [f"_{i}" for i in range(1, 21)]:
                val = (os.getenv(env_name + suffix) or "").strip()
                if not val:
                    continue
                # Allow comma-separated list in one env var
                parts = [p.strip() for p in val.split(",") if p.strip()]
                for p in parts:
                    if p not in seen:
                        seen.add(p)
                        found.append(p)
        self._key_lists[provider] = found
        return found

    def get_key(self, provider: str) -> Optional[str]:
        """Return next healthy key for provider (round-robin across key_1, key_2, ...)."""
        provider = (provider or "").lower().strip()
        keys = self._collect_keys(provider)
        if not keys:
            self._cache[provider] = None
            return None
        # Round-robin
        idx = self._key_index.get(provider, 0) % len(keys)
        self._key_index[provider] = idx + 1
        key = keys[idx]
        self._cache[provider] = key
        return key

    def get_all_keys(self, provider: str) -> List[str]:
        return list(self._collect_keys((provider or "").lower().strip()))

    def mark_key_bad(self, provider: str, key: Optional[str] = None) -> None:
        """Skip a failing key on next rotation (soft mark via health)."""
        provider = (provider or "").lower().strip()
        self._health[provider] = "error"
        # Advance index so next get_key uses a different key
        keys = self._collect_keys(provider)
        if len(keys) > 1:
            self._key_index[provider] = self._key_index.get(provider, 0) + 1

    def list_configured(self) -> List[str]:
        return [p for p in self.PROVIDERS if self.get_key(p)]

    def test_connection(self, provider: str, key: Optional[str] = None) -> Dict[str, Any]:
        import requests

        provider = (provider or "").lower().strip()
        meta = self.PROVIDERS.get(provider)
        if not meta:
            return {"ok": False, "provider": provider, "error": "unknown provider"}
        api_key = (key or self.get_key(provider) or "").strip()
        if not api_key:
            self._health[provider] = "missing_key"
            return {"ok": False, "provider": provider, "error": "no API key configured"}

        url = meta.get("test_url")
        if not url:
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                try:
                    r = requests.get(url, timeout=10)
                    ok = r.status_code < 400
                    self._health[provider] = "ok" if ok else ("rate_limited" if r.status_code == 429 else "error")
                    return {"ok": ok, "provider": provider, "status": r.status_code}
                except Exception as e:
                    self._health[provider] = "error"
                    return {"ok": False, "provider": provider, "error": str(e)}
            self._health[provider] = "ok"
            return {"ok": True, "provider": provider, "note": "key present"}

        headers: Dict[str, str] = {}
        auth = meta.get("auth")
        if auth == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        elif auth == "x-api-key":
            headers["x-api-key"] = api_key
        elif auth == "token":
            headers["Authorization"] = f"Token {api_key}"
        headers.update(meta.get("extra_headers") or {})

        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 429:
                self._health[provider] = "rate_limited"
            elif r.status_code < 400:
                self._health[provider] = "ok"
            else:
                self._health[provider] = "error"
            return {
                "ok": r.status_code < 400,
                "provider": provider,
                "status": r.status_code,
                "error": None if r.status_code < 400 else (r.text or "")[:200],
            }
        except Exception as e:
            self._health[provider] = "error"
            return {"ok": False, "provider": provider, "error": str(e)}

    def get_health(self) -> Dict[str, str]:
        """Return health map; probes configured providers that were never tested."""
        for p in self.list_configured():
            if p not in self._health:
                self.test_connection(p)
        # include known names even if missing
        out = {name.title() if name != "openai" else "OpenAI": self._health.get(name, "unknown") for name in self.PROVIDERS}
        # nicer keys
        mapping = {
            "groq": "Groq", "gemini": "Gemini", "openrouter": "OpenRouter", "deepseek": "DeepSeek",
            "openai": "OpenAI", "claude": "Claude", "mistral": "Mistral", "grok": "Grok",
            "huggingface": "HuggingFace", "replicate": "Replicate", "runpod": "RunPod",
        }
        return {mapping.get(k, k): self._health.get(k, "unknown" if not self.get_key(k) else "untested") for k in self.PROVIDERS}

    def get_optimal_provider(
        self,
        preferred: Optional[str] = None,
        purpose: str = "chat",
        check_health: bool = True,
    ) -> Tuple[Optional[str], Optional[str]]:
        order = list(self.CHAT_FALLBACK_ORDER)
        if purpose == "image":
            order = ["huggingface", "replicate", "runpod", "openai"]
        if preferred:
            preferred = preferred.lower().strip()
            if preferred in order:
                order.remove(preferred)
            order.insert(0, preferred)

        for name in order:
            key = self.get_key(name)
            if not key:
                continue
            if check_health:
                st = self._health.get(name)
                if st is None:
                    probe = self.test_connection(name, key)
                    st = self._health.get(name) or ("ok" if probe.get("ok") else "error")
                if st in ("error", "rate_limited", "missing_key"):
                    continue
            return name, key
        # last resort: any key even if unhealthy
        for name in order:
            key = self.get_key(name)
            if key:
                return name, key
        return None, None

    def auto_retry(
        self,
        fn: Callable[[str, str], Any],
        preferred: Optional[str] = None,
        purpose: str = "chat",
        max_retries: int = 3,
    ) -> Any:
        """
        Call fn(provider, api_key). On failure, try next optimal provider.
        max_retries counts attempts (default 3).
        """
        tried = set()
        last_exc: Optional[Exception] = None
        for attempt in range(max(1, max_retries)):
            provider, key = self.get_optimal_provider(preferred if attempt == 0 else None, purpose=purpose)
            if not provider or not key or provider in tried:
                # force skip preferred after first
                provider, key = self.get_optimal_provider(None, purpose=purpose, check_health=False)
            if not provider or not key or provider in tried:
                break
            tried.add(provider)
            try:
                result = fn(provider, key)
                self._health[provider] = "ok"
                return result
            except Exception as e:
                last_exc = e
                msg = str(e).lower()
                self._health[provider] = "rate_limited" if "429" in msg or "rate" in msg else "error"
                logger.warning("auto_retry %s failed: %s", provider, e)
                preferred = None
                time.sleep(0.15 * (attempt + 1))
        if last_exc:
            raise last_exc
        raise RuntimeError("No API providers available for auto_retry")


vault = ProviderVault()

__all__ = ["ProviderVault", "vault"]
