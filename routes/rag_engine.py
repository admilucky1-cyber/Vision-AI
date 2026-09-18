"""
Vision AI v5.2 — RAG Engine API
Namespaces, async index, hybrid search, health, citations payload.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("vision-ai.rag_engine")
router = APIRouter(prefix="/api/rag", tags=["RAG Engine"])

try:
    from routes.login import get_current_active_user
except Exception:  # pragma: no cover
    async def get_current_active_user():  # type: ignore
        return {"id": "guest", "username": "guest"}


class IndexBody(BaseModel):
    text: str = Field(..., min_length=1)
    filename: str = "paste.txt"
    metadata: Optional[Dict[str, Any]] = None
    async_mode: bool = True


class SearchBody(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(6, ge=1, le=20)
    alpha: float = Field(0.65, ge=0.0, le=1.0)


def _ns(request: Request, user: dict) -> str:
    from services.rag_engine_core import resolve_namespace
    sid = request.cookies.get("vision_sid") or request.headers.get("X-Vision-Session") or ""
    return resolve_namespace(user, sid)


@router.get("/status")
async def rag_status(request: Request, current_user: dict = Depends(get_current_active_user)):
    from services.rag_engine_core import get_store, health_check
    ns = _ns(request, current_user)
    st = get_store(ns).stats()
    health = health_check()
    return {
        "ok": health.get("ok", True),
        "namespace": ns,
        "store": st,
        "health": health,
        "backend": "hybrid-numpy+bm25",
        "ts": time.time(),
    }


@router.get("/health")
async def rag_health():
    from services.rag_engine_core import health_check
    return health_check()


@router.post("/index")
async def rag_index(body: IndexBody, request: Request, current_user: dict = Depends(get_current_active_user)):
    text = body.text.strip()
    if len(text) < 20:
        raise HTTPException(400, "Text too short to index")
    ns = _ns(request, current_user)
    meta = dict(body.metadata or {})
    meta["user"] = (current_user or {}).get("username")
    meta["indexed_at"] = time.time()

    if body.async_mode:
        from services.rag_engine_core import enqueue_index
        res = await enqueue_index(text, body.filename, ns, meta)
        return {"ok": True, "mode": "async", **res}

    from services.rag_engine_core import get_store
    import asyncio
    res = await asyncio.to_thread(get_store(ns).add_document, text, body.filename, meta)
    return {"ok": True, "mode": "sync", **res}


@router.post("/search")
async def rag_search(body: SearchBody, request: Request, current_user: dict = Depends(get_current_active_user)):
    from services.rag_engine_core import get_store
    ns = _ns(request, current_user)
    hits = get_store(ns).search(body.query, top_k=body.top_k, alpha=body.alpha)
    citations = []
    for i, h in enumerate(hits, 1):
        citations.append({
            "id": f"C{i}",
            "chunk_id": h.get("chunk_id"),
            "doc_id": h.get("doc_id"),
            "filename": h.get("filename"),
            "score": h.get("score"),
            "snippet": (h.get("text") or "")[:280],
            "text": h.get("text"),
        })
    return {"ok": True, "namespace": ns, "query": body.query, "results": hits, "citations": citations}


@router.get("/documents")
async def rag_documents(request: Request, current_user: dict = Depends(get_current_active_user)):
    from services.rag_engine_core import get_store
    ns = _ns(request, current_user)
    store = get_store(ns)
    docs: Dict[str, Any] = {}
    for c in store.chunks:
        docs.setdefault(c.doc_id, {"doc_id": c.doc_id, "filename": c.filename, "chunks": 0})
        docs[c.doc_id]["chunks"] += 1
    return {"ok": True, "namespace": ns, "documents": list(docs.values()), "count": len(docs)}


@router.delete("/clear")
async def rag_clear(request: Request, current_user: dict = Depends(get_current_active_user)):
    from services.rag_engine_core import get_store
    ns = _ns(request, current_user)
    get_store(ns).clear()
    return {"ok": True, "namespace": ns, "cleared": True}


@router.post("/prune")
async def rag_prune(current_user: dict = Depends(get_current_active_user)):
    from services.rag_engine_core import prune_all
    return {"ok": True, **prune_all()}
