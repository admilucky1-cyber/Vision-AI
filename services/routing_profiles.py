"""
Vision AI — Model Routing Profiles
Task-aware model selection with automated fallback chains.
Non-breaking: used when profile is selected; auto/legacy paths unchanged.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Profile id → description + match signals + preferred provider order
PROFILES: Dict[str, Dict[str, Any]] = {
    "auto": {
        "label": "Auto (smart)",
        "description": "Detect task type and route optimally",
        "match": [],
        "chain": ["auto"],
    },
    "coding": {
        "label": "Coding",
        "description": "Code, debug, refactor, APIs, SQL",
        "match": [
            r"\b(code|python|javascript|typescript|react|fastapi|debug|refactor|function|class|api|sql|docker|git|compile|stack.?trace)\b",
        ],
        "chain": ["deepseek", "groq", "openrouter", "gemini"],
        "prefer_models": ["deepseek-chat", "llama-3.3-70b", "qwen"],
    },
    "fast": {
        "label": "Fast / lightweight",
        "description": "Quick synthesis, summaries, short answers",
        "match": [
            r"\b(summarize|summary|tldr|brief|quick|short|eli5|one.?line)\b",
        ],
        "chain": ["groq", "gemini", "openrouter", "deepseek"],
        "prefer_models": ["llama-3.1-8b", "gemini-2.0-flash", "gemma"],
    },
    "reasoning": {
        "label": "Deep reasoning",
        "description": "Math, proofs, multi-step analysis",
        "match": [
            r"\b(prove|theorem|derive|integral|derivative|reason|step.?by.?step|analyze|proof)\b",
        ],
        "chain": ["deepseek", "openrouter", "gemini", "groq"],
        "prefer_models": ["deepseek-r1", "o1", "gemini-2.5"],
    },
    "rag_docs": {
        "label": "Documents / RAG",
        "description": "Long PDFs, papers, uploaded context",
        "match": [
            r"\b(pdf|document|paper|upload|according to|based on the file|excerpt|chapter)\b",
        ],
        "chain": ["gemini", "openrouter", "deepseek", "groq"],
        "prefer_models": ["gemini-2.5-pro", "gemini-2.0-flash", "claude"],
    },
    "creative": {
        "label": "Creative writing",
        "description": "Stories, copy, curriculum narrative",
        "match": [
            r"\b(story|poem|creative|write a|narrative|curriculum|lesson plan|script)\b",
        ],
        "chain": ["openrouter", "gemini", "groq", "deepseek"],
        "prefer_models": ["claude", "gemini", "llama"],
    },
    "data_science": {
        "label": "Data science",
        "description": "Pandas, stats, ML pipelines, plots",
        "match": [
            r"\b(pandas|dataframe|numpy|sklearn|matplotlib|seaborn|regression|classifier|dataset|csv|feature)\b",
        ],
        "chain": ["deepseek", "groq", "openrouter", "gemini"],
        "prefer_models": ["deepseek-chat", "llama-3.3-70b"],
    },
}


def list_profiles() -> List[Dict[str, Any]]:
    out = []
    for pid, p in PROFILES.items():
        out.append({
            "id": pid,
            "label": p["label"],
            "description": p["description"],
            "chain": p.get("chain") or [],
        })
    return out


def detect_profile(message: str, has_files: bool = False) -> str:
    text = (message or "").lower()
    if has_files:
        return "rag_docs"
    scores: List[Tuple[int, str]] = []
    for pid, p in PROFILES.items():
        if pid == "auto":
            continue
        score = 0
        for pat in p.get("match") or []:
            if re.search(pat, text, re.I):
                score += 1
        if score:
            scores.append((score, pid))
    if not scores:
        return "auto"
    scores.sort(key=lambda x: (-x[0], x[1]))
    return scores[0][1]


def resolve_chain(profile_id: Optional[str], message: str = "", has_files: bool = False) -> List[str]:
    """Return ordered provider preference list."""
    pid = (profile_id or "auto").strip().lower()
    if pid == "auto" or pid not in PROFILES:
        pid = detect_profile(message, has_files=has_files)
    if pid == "auto":
        return ["auto"]
    return list(PROFILES[pid].get("chain") or ["auto"])


def profile_meta(profile_id: str) -> Dict[str, Any]:
    p = PROFILES.get(profile_id) or PROFILES["auto"]
    return {
        "id": profile_id if profile_id in PROFILES else "auto",
        "label": p["label"],
        "description": p["description"],
        "chain": p.get("chain") or [],
        "prefer_models": p.get("prefer_models") or [],
    }
