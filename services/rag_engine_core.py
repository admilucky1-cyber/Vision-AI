"""
Vision AI v5.2 — RAG Engine Core
- Semantic / structure-aware chunking
- Hybrid dense + BM25 sparse search
- Per-user / per-session namespace isolation
- Async background indexing queue (asyncio)
- LRU memory pruning
- Startup integrity health check
- Offline FAISS-lite / NumPy fallback
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("vision-ai.rag-core")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "rag_namespaces"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Semantic chunking
# ---------------------------------------------------------------------------

_CODE_FENCE = re.compile(r"```[\s\S]*?```", re.M)
_MATH_BLOCK = re.compile(r"\$\$[\s\S]*?\$\$", re.M)
_PARA_SPLIT = re.compile(r"\n\s*\n+")


def semantic_chunk(text: str, target_size: int = 700, max_size: int = 1400) -> List[str]:
    """
    Structure-preserving chunking:
    - Keep fenced code and $$ math blocks intact
    - Prefer paragraph boundaries
    - Merge small paragraphs; split only when over max_size
    """
    if not text or not text.strip():
        return []

    # Protect structural blocks
    holders: List[str] = []

    def _stash(m: re.Match) -> str:
        holders.append(m.group(0))
        return f"\n\n@@HOLD{len(holders) - 1}@@\n\n"

    protected = _CODE_FENCE.sub(_stash, text)
    protected = _MATH_BLOCK.sub(_stash, protected)

    parts = [p.strip() for p in _PARA_SPLIT.split(protected) if p.strip()]
    chunks: List[str] = []
    buf = ""

    def _flush():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for part in parts:
        # Restore holders inside part
        def _restore(m: re.Match) -> str:
            i = int(m.group(1))
            return holders[i] if 0 <= i < len(holders) else m.group(0)

        part = re.sub(r"@@HOLD(\d+)@@", _restore, part)

        if len(part) > max_size:
            _flush()
            # hard-split long unstructured text by sentences
            sentences = re.split(r"(?<=[.!?])\s+", part)
            cur = ""
            for s in sentences:
                if len(cur) + len(s) + 1 <= max_size:
                    cur = (cur + " " + s).strip()
                else:
                    if cur:
                        chunks.append(cur)
                    cur = s
            if cur:
                chunks.append(cur)
            continue

        if not buf:
            buf = part
        elif len(buf) + len(part) + 2 <= target_size:
            buf = buf + "\n\n" + part
        elif len(buf) + len(part) + 2 <= max_size:
            buf = buf + "\n\n" + part
        else:
            _flush()
            buf = part

    _flush()
    return chunks or [text[:max_size]]


# ---------------------------------------------------------------------------
# BM25 sparse ranker
# ---------------------------------------------------------------------------

class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: List[List[str]] = []
        self.doc_len: List[int] = []
        self.avgdl = 0.0
        self.df: Dict[str, int] = {}
        self.N = 0

    @staticmethod
    def tokenize(text: str) -> List[str]:
        # Keep code-ish tokens and math-ish symbols as tokens
        text = text.lower()
        return re.findall(r"[a-z0-9_]+|[+\-*/=<>()\[\]{}.,;:]", text)

    def add(self, text: str) -> None:
        toks = self.tokenize(text)
        self.docs.append(toks)
        self.doc_len.append(len(toks) or 1)
        self.N = len(self.docs)
        seen = set()
        for t in toks:
            if t not in seen:
                self.df[t] = self.df.get(t, 0) + 1
                seen.add(t)
        self.avgdl = sum(self.doc_len) / max(1, self.N)

    def score(self, query: str) -> List[float]:
        q = self.tokenize(query)
        scores = [0.0] * self.N
        if not self.N:
            return scores
        for term in q:
            df = self.df.get(term, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
            for i, toks in enumerate(self.docs):
                tf = toks.count(term)
                if tf == 0:
                    continue
                dl = self.doc_len[i]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                scores[i] += idf * (tf * (self.k1 + 1)) / (denom or 1)
        return scores


# ---------------------------------------------------------------------------
# Namespace store (NumPy dense + BM25) — always available offline
# ---------------------------------------------------------------------------

@dataclass
class ChunkRec:
    id: str
    text: str
    namespace: str
    filename: str
    doc_id: str
    meta: Dict[str, Any] = field(default_factory=dict)
    last_access: float = field(default_factory=time.time)


class NamespaceStore:
    """Per-namespace isolated hybrid index with LRU pruning."""

    def __init__(self, namespace: str, max_chunks: int = 4000):
        self.namespace = namespace
        self.max_chunks = max_chunks
        self.chunks: List[ChunkRec] = []
        self.vectors: Optional[np.ndarray] = None  # (N, D)
        self.bm25 = BM25()
        self._lock = threading.RLock()
        self._embed_cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._model = None

    def _embed(self, texts: List[str]) -> np.ndarray:
        # Try sentence-transformers MiniLM (lighter than bge-large for local)
        try:
            if self._model is None:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            arr = self._model.encode(texts, normalize_embeddings=True)
            return np.asarray(arr, dtype=np.float32)
        except Exception as e:
            logger.debug("ST unavailable, hash-bag embed: %s", e)
            out = []
            for t in texts:
                key = hashlib.md5(t.encode("utf-8", errors="ignore")).hexdigest()
                if key in self._embed_cache:
                    self._embed_cache.move_to_end(key)
                    out.append(self._embed_cache[key])
                    continue
                v = np.zeros(64, dtype=np.float32)
                for tok in t.lower().split():
                    v[hash(tok) % 64] += 1.0
                n = np.linalg.norm(v) or 1.0
                v = v / n
                self._embed_cache[key] = v
                if len(self._embed_cache) > 512:
                    self._embed_cache.popitem(last=False)
                out.append(v)
            return np.stack(out, axis=0)

    def add_document(self, text: str, filename: str = "doc.txt", meta: Optional[Dict] = None) -> Dict[str, Any]:
        meta = dict(meta or {})
        pieces = semantic_chunk(text)
        doc_id = hashlib.sha256((filename + text[:240]).encode("utf-8", errors="ignore")).hexdigest()[:16]
        with self._lock:
            vecs = self._embed(pieces)
            for i, (ch, vec) in enumerate(zip(pieces, vecs)):
                cid = f"{doc_id}_{i}"
                rec = ChunkRec(
                    id=cid,
                    text=ch,
                    namespace=self.namespace,
                    filename=filename,
                    doc_id=doc_id,
                    meta={**meta, "chunk_index": i, "total_chunks": len(pieces)},
                )
                self.chunks.append(rec)
                self.bm25.add(ch)
                if self.vectors is None:
                    self.vectors = vec.reshape(1, -1)
                else:
                    # dimension mismatch guard
                    if self.vectors.shape[1] != vec.shape[0]:
                        self.vectors = None
                        self.vectors = vec.reshape(1, -1)
                        # rebuild is expensive; for safety reset bm25 parallel already ok
                    else:
                        self.vectors = np.vstack([self.vectors, vec.reshape(1, -1)])
            self._prune_lru()
        return {"doc_id": doc_id, "chunks": len(pieces), "namespace": self.namespace}

    def search(self, query: str, top_k: int = 6, alpha: float = 0.65) -> List[Dict[str, Any]]:
        """Hybrid: alpha * dense + (1-alpha) * bm25 (min-max normalized)."""
        with self._lock:
            n = len(self.chunks)
            if n == 0:
                return []
            dense = np.zeros(n, dtype=np.float32)
            if self.vectors is not None and self.vectors.shape[0] == n:
                qv = self._embed([query])[0]
                if qv.shape[0] == self.vectors.shape[1]:
                    dense = self.vectors @ qv
            sparse = np.asarray(self.bm25.score(query), dtype=np.float32)
            if sparse.shape[0] != n:
                sparse = np.zeros(n, dtype=np.float32)

            def _norm(x: np.ndarray) -> np.ndarray:
                mn, mx = float(x.min()), float(x.max())
                if mx - mn < 1e-9:
                    return np.zeros_like(x)
                return (x - mn) / (mx - mn)

            score = alpha * _norm(dense) + (1 - alpha) * _norm(sparse)
            idx = np.argsort(score)[::-1][:top_k]
            out = []
            now = time.time()
            for i in idx:
                rec = self.chunks[int(i)]
                rec.last_access = now
                out.append({
                    "text": rec.text,
                    "score": float(score[int(i)]),
                    "dense": float(dense[int(i)]),
                    "bm25": float(sparse[int(i)]),
                    "filename": rec.filename,
                    "doc_id": rec.doc_id,
                    "chunk_id": rec.id,
                    "namespace": rec.namespace,
                    "metadata": rec.meta,
                })
            return out

    def _prune_lru(self) -> None:
        if len(self.chunks) <= self.max_chunks:
            return
        order = sorted(range(len(self.chunks)), key=lambda i: self.chunks[i].last_access)
        drop = len(self.chunks) - self.max_chunks
        keep_idx = sorted(order[drop:])
        self.chunks = [self.chunks[i] for i in keep_idx]
        if self.vectors is not None and self.vectors.shape[0] >= drop:
            self.vectors = self.vectors[keep_idx]
        # rebuild bm25
        self.bm25 = BM25()
        for c in self.chunks:
            self.bm25.add(c.text)
        logger.info("LRU pruned namespace=%s → %d chunks", self.namespace, len(self.chunks))

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "namespace": self.namespace,
                "chunks": len(self.chunks),
                "docs": len({c.doc_id for c in self.chunks}),
                "vector_dim": int(self.vectors.shape[1]) if self.vectors is not None else 0,
            }

    def clear(self) -> None:
        with self._lock:
            self.chunks.clear()
            self.vectors = None
            self.bm25 = BM25()


# ---------------------------------------------------------------------------
# Global registry + async queue
# ---------------------------------------------------------------------------

_STORES: Dict[str, NamespaceStore] = {}
_STORES_LOCK = threading.RLock()
_QUEUE: Optional[asyncio.Queue] = None
_WORKER_STARTED = False


def get_store(namespace: str) -> NamespaceStore:
    ns = (namespace or "default").strip() or "default"
    # sanitize
    ns = re.sub(r"[^a-zA-Z0-9_\-:]", "_", ns)[:80]
    with _STORES_LOCK:
        if ns not in _STORES:
            _STORES[ns] = NamespaceStore(ns)
        return _STORES[ns]


def resolve_namespace(user: Optional[Dict] = None, session_id: Optional[str] = None) -> str:
    if user and user.get("id"):
        return f"user:{user.get('id')}"
    if user and user.get("username") and user.get("username") != "guest":
        return f"user:{user.get('username')}"
    if session_id:
        return f"session:{session_id}"
    return "guest:anonymous"


async def ensure_worker(loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    global _QUEUE, _WORKER_STARTED
    if _WORKER_STARTED:
        return
    _QUEUE = asyncio.Queue()
    _WORKER_STARTED = True

    async def _worker():
        while True:
            job = await _QUEUE.get()
            try:
                ns = job["namespace"]
                store = get_store(ns)
                # run blocking embed/index off event loop
                await asyncio.to_thread(
                    store.add_document,
                    job["text"],
                    job.get("filename") or "upload.txt",
                    job.get("meta") or {},
                )
                logger.info("Async indexed %s ns=%s chunks≈semantic", job.get("filename"), ns)
            except Exception as e:
                logger.exception("Async index failed: %s", e)
            finally:
                _QUEUE.task_done()

    asyncio.create_task(_worker())
    logger.info("RAG async index worker started")


async def enqueue_index(
    text: str,
    filename: str,
    namespace: str,
    meta: Optional[Dict] = None,
) -> Dict[str, Any]:
    await ensure_worker()
    assert _QUEUE is not None
    await _QUEUE.put({
        "text": text,
        "filename": filename,
        "namespace": namespace,
        "meta": meta or {},
        "ts": time.time(),
    })
    return {"queued": True, "namespace": namespace, "filename": filename}


def health_check() -> Dict[str, Any]:
    """Startup / readiness integrity check."""
    report: Dict[str, Any] = {
        "ok": True,
        "data_dir": str(DATA_DIR),
        "data_dir_writable": False,
        "namespaces": [],
        "chroma": {"available": False},
        "numpy": True,
        "errors": [],
    }
    try:
        probe = DATA_DIR / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        report["data_dir_writable"] = True
    except Exception as e:
        report["ok"] = False
        report["errors"].append(f"data_dir: {e}")

    try:
        import chromadb  # noqa: F401
        report["chroma"]["available"] = True
        try:
            from services.vector_store import vector_store
            if vector_store is not None:
                report["chroma"]["stats"] = vector_store.get_stats()
        except Exception as e:
            report["chroma"]["error"] = str(e)
    except Exception as e:
        report["chroma"]["error"] = str(e)

    with _STORES_LOCK:
        for ns, st in _STORES.items():
            report["namespaces"].append(st.stats())

    # light numpy op
    try:
        _ = np.dot(np.ones(8, dtype=np.float32), np.ones(8, dtype=np.float32))
    except Exception as e:
        report["ok"] = False
        report["numpy"] = False
        report["errors"].append(str(e))

    return report


def prune_all(max_total_chunks: int = 12000) -> Dict[str, Any]:
    with _STORES_LOCK:
        total = sum(len(s.chunks) for s in _STORES.values())
        if total <= max_total_chunks:
            return {"pruned": False, "total": total}
        # prune largest namespaces first
        for st in sorted(_STORES.values(), key=lambda s: len(s.chunks), reverse=True):
            st.max_chunks = max(200, st.max_chunks // 2)
            st._prune_lru()
            total = sum(len(s.chunks) for s in _STORES.values())
            if total <= max_total_chunks:
                break
        return {"pruned": True, "total": total}
