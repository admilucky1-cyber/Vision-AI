"""
Vision AI v3.0.1 — Autonomous background agent
Keeps Colab worker warm and suggests skills periodically.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vision-ai.agent")

_INTERVAL_SEC = int(os.getenv("AGENT_INTERVAL_SEC", "300"))  # 5 minutes


class AgentOrchestrator:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._last_warmup: Optional[str] = None
        self._colab_status = "unknown"
        self._last_error: Optional[str] = None

    def start_agents(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="vision-agent", daemon=True)
        self._thread.start()
        self._running = True
        logger.info("AgentOrchestrator started (interval=%ss)", _INTERVAL_SEC)

    def stop_agents(self) -> None:
        self._stop.set()
        self._running = False

    def _loop(self) -> None:
        # small delay so app finishes boot
        self._stop.wait(8)
        while not self._stop.is_set():
            try:
                self.warmup_colab()
            except Exception as e:
                self._last_error = str(e)
                logger.warning("agent loop: %s", e)
            self._stop.wait(_INTERVAL_SEC)

    def warmup_colab(self) -> Dict[str, Any]:
        """Ping Colab / worker health endpoints to reduce cold starts."""
        import requests

        urls: List[str] = []
        env_url = (os.getenv("COLAB_WORKER_URL") or os.getenv("WORKER_URL") or "").rstrip("/")
        if env_url:
            urls.extend([f"{env_url}/worker/health", f"{env_url}/health", env_url])

        # Try registry used by some deployments
        try:
            from services import colab_worker
            base = getattr(colab_worker, "WORKER_URL", None) or getattr(colab_worker, "get_worker_url", lambda: None)()
            if callable(base):
                base = base()
            if base:
                base = str(base).rstrip("/")
                urls.extend([f"{base}/worker/health", f"{base}/health"])
        except Exception:
            pass

        if not urls:
            self._colab_status = "inactive"
            self._last_warmup = datetime.now(timezone.utc).isoformat()
            return {"ok": False, "reason": "no worker URL configured"}

        headers = {}
        secret = (os.getenv("WORKER_SECRET") or "").strip()
        if secret:
            headers["X-Worker-Secret"] = secret
            headers["Authorization"] = f"Bearer {secret}"

        last_err = None
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=12)
                if r.status_code < 500:
                    self._colab_status = "active" if r.status_code < 400 else "degraded"
                    self._last_warmup = datetime.now(timezone.utc).isoformat()
                    self._last_error = None
                    return {"ok": True, "url": url, "status": r.status_code}
                last_err = f"{url} -> {r.status_code}"
            except Exception as e:
                last_err = str(e)
        self._colab_status = "inactive"
        self._last_warmup = datetime.now(timezone.utc).isoformat()
        self._last_error = last_err
        return {"ok": False, "error": last_err}

    def suggest_skill(self, user_query: str) -> List[str]:
        try:
            from services.skill_router import skill_router
            return skill_router.suggest_skills(user_query)
        except Exception as e:
            logger.debug("suggest_skill: %s", e)
            return []

    def get_status(self) -> Dict[str, Any]:
        return {
            "colab": self._colab_status,
            "agent": "running" if self._running else "stopped",
            "last_warmup": self._last_warmup,
            "last_error": self._last_error,
            "interval_sec": _INTERVAL_SEC,
        }


# Process singleton
agent_orchestrator = AgentOrchestrator()

__all__ = ["AgentOrchestrator", "agent_orchestrator"]
