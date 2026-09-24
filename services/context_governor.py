"""
Adaptive context window governor — compress/prune history while keeping
code blocks, equations, and system constraints.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

CODE_RE = re.compile(r"```[\s\S]*?```")
MATH_RE = re.compile(r"\$\$[\s\S]*?\$\$|\$[^$\n]+\$")


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _priority(msg: Dict[str, Any]) -> int:
    role = (msg.get("role") or "").lower()
    content = msg.get("content") or msg.get("text") or ""
    score = 0
    if role in ("system", "tool"):
        score += 100
    if CODE_RE.search(content):
        score += 40
    if MATH_RE.search(content):
        score += 30
    if role == "user":
        score += 10
    return score


def govern_messages(messages: List[Dict[str, Any]], max_tokens: int = 24000) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Keep high-priority messages; summarize-drop low-priority older turns.
    Returns (messages, stats).
    """
    if not messages:
        return [], {"kept": 0, "dropped": 0, "tokens": 0}

    total = sum(estimate_tokens(m.get("content") or m.get("text") or "") for m in messages)
    if total <= max_tokens:
        return list(messages), {"kept": len(messages), "dropped": 0, "tokens": total, "compressed": False}

    # Always keep last 4 turns and all system/code-heavy
    n = len(messages)
    keep_idx = set(range(max(0, n - 4), n))
    ranked = sorted(range(n), key=lambda i: (-_priority(messages[i]), i))
    tokens = sum(estimate_tokens(messages[i].get("content") or messages[i].get("text") or "") for i in keep_idx)

    for i in ranked:
        if i in keep_idx:
            continue
        t = estimate_tokens(messages[i].get("content") or messages[i].get("text") or "")
        if tokens + t <= max_tokens:
            keep_idx.add(i)
            tokens += t

    kept = [messages[i] for i in sorted(keep_idx)]
    dropped = n - len(kept)
    # Insert brief marker if dropped
    if dropped:
        kept.insert(0, {
            "role": "system",
            "content": f"[Context governor: omitted {dropped} older low-priority turns to fit window]",
        })
    return kept, {"kept": len(kept), "dropped": dropped, "tokens": tokens, "compressed": True}
