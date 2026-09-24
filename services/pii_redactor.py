"""Privacy pre-processor — scrub PII / secrets from prompts and logs.

Prefers the memory-safe Rust binary (vision-pii-redactor) when available
for speed and safety. Falls back to pure-Python regex implementation.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("vision-ai.pii")

_BASE = Path(__file__).resolve().parent.parent
_RUST_CANDIDATES = [
    _BASE / "bin" / "vision-pii-redactor",
    Path("/usr/local/bin/vision-pii-redactor"),
    Path(shutil.which("vision-pii-redactor") or ""),
]

_RUST_BIN: Optional[Path] = None
for _c in _RUST_CANDIDATES:
    if _c and _c.is_file() and os.access(_c, os.X_OK):
        _RUST_BIN = _c
        break

PATTERNS = [
    (re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|auth)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)\b(sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})"), "[REDACTED_TOKEN]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?i)\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
    (re.compile(r"(?i)(?:/home|/Users|C:\\\\Users)/[^\s'\"]+"), "[REDACTED_PATH]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]"),
]


def _redact_python(text: str) -> Tuple[str, int]:
    if not text:
        return text, 0
    out = text
    n = 0
    for cre, repl in PATTERNS:
        out, c = cre.subn(repl, out)
        n += c
    return out, n


def _redact_rust(text: str) -> Optional[Tuple[str, int]]:
    if not _RUST_BIN:
        return None
    try:
        proc = subprocess.run(
            [str(_RUST_BIN), "--json"],
            input=json.dumps({"text": text}),
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if proc.returncode != 0:
            logger.debug("Rust PII redactor non-zero exit: %s", proc.stderr[:200])
            return None
        data = json.loads(proc.stdout)
        return data.get("text", text), int(data.get("redactions", 0))
    except Exception as e:
        logger.debug("Rust PII redactor unavailable: %s", e)
        return None


def redact(text: str) -> Tuple[str, int]:
    """Redact PII/secrets. Returns (clean_text, redaction_count).

    Uses Rust binary when present (safer + faster), otherwise pure Python.
    """
    if not text:
        return text, 0
    rust = _redact_rust(text)
    if rust is not None:
        return rust
    return _redact_python(text)


def backend_info() -> str:
    """Which implementation is active."""
    return f"rust:{_RUST_BIN}" if _RUST_BIN else "python"
