"""Intelligent query expansion — synonyms + sub-questions for hybrid retrieval."""
from __future__ import annotations

import re
from typing import List

_SYNONYMS = {
    "function": ["method", "routine", "procedure", "def"],
    "error": ["exception", "bug", "failure", "fault"],
    "fast": ["quick", "rapid", "low-latency"],
    "model": ["llm", "network", "checkpoint"],
    "train": ["fit", "optimize", "learn"],
    "data": ["dataset", "corpus", "records"],
    "image": ["picture", "photo", "frame"],
    "code": ["source", "implementation", "script"],
    "math": ["equation", "formula", "calculus", "algebra"],
}


def expand_query(query: str, max_variants: int = 4) -> List[str]:
    q = (query or "").strip()
    if not q:
        return []
    variants = [q]
    lower = q.lower()
    for stem, syns in _SYNONYMS.items():
        if stem in lower or any(s in lower for s in syns):
            for s in syns[:2]:
                v = re.sub(re.escape(stem), s, q, flags=re.I)
                if v not in variants:
                    variants.append(v)
                if len(variants) >= max_variants:
                    return variants
    # sub-question heuristics
    if len(q.split()) >= 4:
        variants.append("What is the definition of: " + q)
        variants.append("Key steps for: " + q)
    return variants[: max(1, max_variants)]
