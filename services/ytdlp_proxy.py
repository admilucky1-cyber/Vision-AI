"""
Lightweight free-proxy helper for yt-dlp.
Enable auto: YTDLP_AUTO_PROXY=1
Static: YTDLP_PROXY=http://host:port  (or socks5://... for remote SOCKS)
Local Tor (socks5://127.0.0.1:9050) only if YTDLP_ALLOW_LOCAL_PROXY=1
"""
from __future__ import annotations

import logging
import os
import random
import socket
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("vision-ai.ytdlp_proxy")

_LOCK = threading.RLock()
_CACHE: Dict[str, Any] = {"proxy": None, "ts": 0.0}
_TTL = int(os.getenv("YTDLP_PROXY_TTL_SEC", "900") or 900)


def _is_local_host(host: str) -> bool:
    h = (host or "").strip().lower()
    return h in ("127.0.0.1", "localhost", "::1", "0.0.0.0")


def _local_proxy_allowed() -> bool:
    return (os.getenv("YTDLP_ALLOW_LOCAL_PROXY") or "").strip().lower() in ("1", "true", "yes", "on")


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _normalize_proxy(p: str) -> Optional[str]:
    p = (p or "").strip()
    if not p:
        return None
    if "://" not in p:
        p = "http://" + p
    try:
        u = urlparse(p)
        host = u.hostname or ""
        port = u.port
        if _is_local_host(host):
            if not _local_proxy_allowed():
                logger.warning(
                    "Ignoring local proxy %s (set YTDLP_ALLOW_LOCAL_PROXY=1 only if Tor/proxy runs on this host)",
                    p,
                )
                return None
            if port and not _port_open(host, port):
                logger.warning("Local proxy port closed: %s:%s — not using", host, port)
                return None
        return p
    except Exception:
        return p


def _static_proxy() -> Optional[str]:
    raw = (os.getenv("YTDLP_PROXY") or "").strip()
    # Do NOT fall back to generic HTTPS_PROXY/HTTP_PROXY for YouTube —
    # Railway/platform env often points at broken or unrelated proxies.
    if (os.getenv("YTDLP_USE_ENV_HTTP_PROXY") or "").strip().lower() in ("1", "true", "yes"):
        raw = raw or (os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or "").strip()
    return _normalize_proxy(raw)


def _fetch_github_proxies(limit: int = 40) -> List[str]:
    out: List[str] = []
    try:
        import requests
        r = requests.get(
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.json",
            timeout=12,
        )
        if r.status_code != 200:
            return out
        data = r.json()
        if not isinstance(data, list):
            return out
        random.shuffle(data)
        for row in data:
            if not isinstance(row, dict):
                continue
            proto = (row.get("protocol") or "http").lower()
            if proto not in ("http", "https"):
                continue  # skip socks for reliability on Railway
            ip = row.get("ip")
            port = row.get("port")
            if not ip or not port or _is_local_host(str(ip)):
                continue
            out.append(f"{proto}://{ip}:{port}")
            if len(out) >= limit:
                break
    except Exception as e:
        logger.info("proxy list fetch failed: %s", e)
    return out


def _quick_ok(proxy: str, timeout: float = 4.0) -> bool:
    try:
        import requests
        r = requests.get(
            "https://www.youtube.com/generate_204",
            proxies={"http": proxy, "https": proxy},
            timeout=timeout,
            allow_redirects=True,
        )
        return r.status_code < 500
    except Exception:
        return False


def get_working_proxy(force: bool = False) -> Optional[str]:
    static = _static_proxy()
    if static:
        return static

    auto = (os.getenv("YTDLP_AUTO_PROXY") or "").strip().lower() in ("1", "true", "yes", "on")
    if not auto:
        return None

    with _LOCK:
        if not force and _CACHE.get("proxy") and (time.time() - float(_CACHE.get("ts") or 0)) < _TTL:
            return _CACHE["proxy"]

    candidates = _fetch_github_proxies(50)
    tested = 0
    for proxy in candidates[:20]:
        tested += 1
        if _quick_ok(proxy):
            with _LOCK:
                _CACHE["proxy"] = proxy
                _CACHE["ts"] = time.time()
            logger.info("yt-dlp auto-proxy OK (%s tests): %s", tested, proxy)
            return proxy
    logger.warning("yt-dlp auto-proxy: none worked (%s tested)", tested)
    with _LOCK:
        _CACHE["proxy"] = None
        _CACHE["ts"] = time.time()
    return None


def invalidate_proxy() -> None:
    with _LOCK:
        _CACHE["proxy"] = None
        _CACHE["ts"] = 0.0
