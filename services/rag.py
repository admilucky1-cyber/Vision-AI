"""
Vision AI — RAG helpers (v2.7.0)

- Local re-ranker: sentence-transformers/all-MiniLM-L6-v2 (CPU-friendly)
- Used after coarse retrieval / on long document contexts
- Graceful no-op if sentence-transformers is missing
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("vision-ai.rag")

RERANK_MODEL = os.getenv("RERANK_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "6"))
RERANK_ENABLED = (os.getenv("RERANK_ENABLED", "1") or "1").strip().lower() not in (
    "0",
    "false",
    "no",
)

_rerank_model = None
_rerank_failed = False


def _get_reranker():
    global _rerank_model, _rerank_failed
    if _rerank_failed or not RERANK_ENABLED:
        return None
    if _rerank_model is not None:
        return _rerank_model
    try:
        from sentence_transformers import CrossEncoder, SentenceTransformer
        # MiniLM bi-encoder is lighter and enough for free tier re-score
        _rerank_model = SentenceTransformer(RERANK_MODEL)
        logger.info(f"RAG re-ranker loaded: {RERANK_MODEL}")
        return _rerank_model
    except Exception as e:
        logger.warning(f"RAG re-ranker unavailable ({e}) — using original order")
        _rerank_failed = True
        return None


def split_into_chunks(text: str, size: int = 500, overlap: int = 80) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            cut = text.rfind(". ", start + max(0, size - 120), end)
            if cut == -1:
                cut = text.rfind("\n", start + max(0, size - 120), end)
            if cut > start:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = max(end - overlap, start + 1)
        if start >= n:
            break
    return chunks


def rerank_chunks(
    query: str,
    chunks: List[str],
    top_k: int = RERANK_TOP_K,
) -> List[Tuple[str, float]]:
    """
    Re-rank text chunks by similarity to query.
    Returns list of (chunk, score) best-first.
    """
    if not chunks:
        return []
    q = (query or "").strip()
    if not q:
        return [(c, 0.0) for c in chunks[:top_k]]

    model = _get_reranker()
    if model is None:
        return [(c, 0.0) for c in chunks[:top_k]]

    try:
        import numpy as np

        q_emb = model.encode([q], normalize_embeddings=True)
        c_emb = model.encode(chunks, normalize_embeddings=True)
        scores = (c_emb @ q_emb.T).reshape(-1)
        order = np.argsort(-scores)
        out: List[Tuple[str, float]] = []
        for i in order[:top_k]:
            out.append((chunks[int(i)], float(scores[int(i)])))
        return out
    except Exception as e:
        logger.warning(f"rerank failed: {e}")
        return [(c, 0.0) for c in chunks[:top_k]]


def _is_full_document_intent(query: str, ctx: str = "") -> bool:
    """True when the user wants the whole paper, not a few RAG snippets."""
    q = (query or "").lower()
    c = (ctx or "")
    full_cmds = (
        "solve", "answer all", "complete solution", "mark this", "work through",
        "entire paper", "whole paper", "all questions", "every question",
        "full solution", "solve this", "solve the", "solve pdf", "solve it",
        "yeh solve", "sara solve", "poora solve", "saare questions",
    )
    if any(w in q for w in full_cmds):
        return True
    if any(m in c for m in ("[QUESTION PAPER", "[MARK SCHEME", "[SOLVE MODE")):
        return True
    return False


def build_rag_context(
    query: str,
    document_text: str,
    max_chars: int = 12000,
    chunk_size: int = 500,
) -> str:
    """
    Chunk a long document, re-rank vs query, return compact context block.
    For full-paper intents (solve / all questions), keep ordered document text
    instead of top-k similarity slices (those caused invented questions).
    """
    text = (document_text or "").strip()
    if not text:
        return ""

    if _is_full_document_intent(query, text):
        limit = max(max_chars, 80_000)
        if len(text) <= limit:
            return text
        try:
            from services.llm import _prefer_question_body
            return _prefer_question_body(text, limit)
        except Exception:
            return text[:limit] + "\n...[truncated for length]"

    if len(text) <= max_chars // 2:
        return text[:max_chars]

    chunks = split_into_chunks(text, size=chunk_size)
    ranked = rerank_chunks(query, chunks, top_k=max(RERANK_TOP_K, 8))
    parts: List[str] = []
    total = 0
    for ch, score in ranked:
        if total + len(ch) > max_chars:
            remain = max_chars - total
            if remain > 200:
                parts.append(ch[:remain])
            break
        parts.append(ch)
        total += len(ch) + 2
    header = "[RAG re-ranked document excerpts — most relevant first]\n"
    return header + "\n\n".join(parts)


def enhance_file_context(query: str, extra_context: str, max_chars: int = 12000) -> str:
    """
    If extra_context looks like a long upload, re-rank; else return as-is.
    Skip aggressive top-k RAG when the user wants the whole exam paper solved.
    """
    ctx = extra_context or ""
    if len(ctx) < 2500:
        return ctx
    if "[YOUTUBE" in ctx[:200].upper():
        return ctx
    if _is_full_document_intent(query, ctx):
        limit = max(max_chars, 100_000)
        if len(ctx) <= limit:
            logger.info(f"RAG skip (full-document intent) → keeping {len(ctx)} chars")
            return ctx
        try:
            from services.llm import _prefer_question_body
            out = _prefer_question_body(ctx, limit)
            logger.info(f"RAG skip + smart truncate → {len(out)} chars")
            return out
        except Exception:
            return ctx[:limit] + "\n...[truncated for length]"
    try:
        return build_rag_context(query, ctx, max_chars=max_chars)
    except Exception as e:
        logger.warning(f"enhance_file_context: {e}")
        return ctx[:max_chars]


__all__ = [
    "split_into_chunks",
    "rerank_chunks",
    "build_rag_context",
    "enhance_file_context",
]
