"""Shared security helpers — admin checks, SSRF guards, reserved names."""
from __future__ import annotations

import ipaddress
import os
import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status

RESERVED_USERNAMES = frozenset(
    {
        "admin",
        "administrator",
        "root",
        "owner",
        "system",
        "support",
        "moderator",
        "mod",
        "staff",
        "vision",
        "visionai",
        "api",
        "null",
        "undefined",
    }
)


def require_admin(current_user: dict) -> dict:
    """Admin access only via explicit role — never username alone."""
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    if current_user.get("is_guest"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def is_reserved_username(username: str) -> bool:
    u = (username or "").strip().lower()
    return u in RESERVED_USERNAMES


def is_private_or_local_host(host: str) -> bool:
    h = (host or "").strip().lower().rstrip(".")
    if not h:
        return True
    if h in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata", "metadata.google.internal"):
        return True
    if h.endswith(".local") or h.endswith(".internal"):
        return True
    try:
        ip = ipaddress.ip_address(h)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )
    except ValueError:
        return False


def validate_worker_url(url: str, *, allow_private: bool = False) -> str:
    """Reject SSRF targets for worker registration."""
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        raise ValueError("Worker URL must be http(s)")
    parsed = urlparse(u)
    host = parsed.hostname or ""
    if not allow_private and is_private_or_local_host(host):
        raise ValueError("Worker URL host is not allowed (private/local/metadata)")
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Invalid worker URL scheme")
    return u.rstrip("/")


def validate_openai_compat_base(url: str) -> Optional[str]:
    """
    Hosted SaaS: block arbitrary base URLs (SSRF).
    Allow only if OPENAI_COMPAT_ALLOW_CUSTOM=1 and host is not private,
    or host is in OPENAI_COMPAT_ALLOWED_HOSTS.
    """
    u = (url or "").strip()
    if not u:
        return None
    allow = os.getenv("OPENAI_COMPAT_ALLOW_CUSTOM", "0").strip() in ("1", "true", "yes")
    allowed = {
        h.strip().lower()
        for h in (os.getenv("OPENAI_COMPAT_ALLOWED_HOSTS") or "").split(",")
        if h.strip()
    }
    if not allow and not allowed:
        return None  # ignore client-supplied base in production SaaS
    try:
        parsed = urlparse(u if "://" in u else f"http://{u}")
        host = (parsed.hostname or "").lower()
        if allowed and host not in allowed:
            return None
        if is_private_or_local_host(host) and host not in allowed:
            return None
        return u.rstrip("/")
    except Exception:
        return None
