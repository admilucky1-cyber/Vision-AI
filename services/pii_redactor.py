"""Privacy pre-processor — scrub PII / secrets from prompts and logs."""
from __future__ import annotations

import re
from typing import Tuple

PATTERNS = [
    (re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|auth)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)\b(sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})"), "[REDACTED_TOKEN]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?i)\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
    (re.compile(r"(?i)(?:/home|/Users|C:\\\\Users)/[^\s'\"]+"), "[REDACTED_PATH]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]"),
]


def redact(text: str) -> Tuple[str, int]:
    if not text:
        return text, 0
    out = text
    n = 0
    for cre, repl in PATTERNS:
        out, c = cre.subn(repl, out)
        n += c
    return out, n
