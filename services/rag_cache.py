"""
Vision AI — disk-backed upload cache for follow-up exam solve.
Shared across uvicorn workers via data/rag_cache/.
"""
from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vision-ai.rag_cache")

class RAGCache:
    """
    Shared upload cache for follow-up messages (upload PDF → later "solve this pdf").

    - Scoped by user_key (no cross-user paper mix)
    - Persisted under data/rag_cache/ so multi-worker processes share state
    - TTL eviction (default 1 hour)
    """

    def __init__(self, max_size: int = 8, ttl_sec: float = 3600.0):
        self._max_size = max_size
        self._ttl_sec = ttl_sec
        self._root = Path(__file__).resolve().parent.parent / "data" / "rag_cache"
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @staticmethod
    def _safe_user(user_key: str) -> str:
        uk = (user_key or "anon").strip() or "anon"
        out = []
        for ch in uk[:64]:
            if ch.isalnum() or ch in ("-", "_", ".", "@"):
                out.append(ch)
            else:
                out.append("_")
        return "".join(out) or "anon"

    def get_key(self, filename: str, content: str, user_key: str = "") -> str:
        raw = f"{user_key}|{filename}:{content[:500]}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _user_dir(self, user_key: str) -> Path:
        d = self._root / self._safe_user(user_key)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _path_for(self, key: str, user_key: str) -> Path:
        return self._user_dir(user_key) / f"{key}.json"

    def get(self, key: str, user_key: str = "") -> Optional[dict]:
        path = self._path_for(key, user_key)
        if not path.is_file():
            return None
        try:
            import json
            item = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if time.time() - float(item.get("timestamp") or 0) > self._ttl_sec:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return None
        return item

    def set(self, key: str, data: dict):
        import json
        data = dict(data)
        data.setdefault("timestamp", time.time())
        user_key = str(data.get("user_key") or "anon")
        path = self._path_for(key, user_key)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as e:
            logger.warning(f"RAGCache disk set failed: {e}")
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        self._evict(user_key)

    def _iter_user_files(self, user_key: str = ""):
        if user_key:
            roots = [self._user_dir(user_key)]
        else:
            try:
                roots = [p for p in self._root.iterdir() if p.is_dir()]
            except Exception:
                roots = []
        for root in roots:
            try:
                for path in root.glob("*.json"):
                    yield path
            except Exception:
                continue

    def _evict(self, user_key: str = ""):
        import json
        now = time.time()
        entries = []
        for path in self._iter_user_files(user_key):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                ts = float(item.get("timestamp") or 0)
                if now - ts > self._ttl_sec:
                    path.unlink(missing_ok=True)
                else:
                    entries.append((ts, path))
            except Exception:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
        if user_key and len(entries) > self._max_size:
            entries.sort(key=lambda x: x[0])
            for _, path in entries[: max(0, len(entries) - self._max_size)]:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass

    def clear(self, user_key: Optional[str] = None):
        import shutil
        if user_key is None:
            try:
                if self._root.exists():
                    shutil.rmtree(self._root, ignore_errors=True)
                self._root.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"RAGCache clear all failed: {e}")
            return
        d = self._root / self._safe_user(user_key)
        try:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        except Exception as e:
            logger.warning(f"RAGCache clear user failed: {e}")

    def get_latest(self, user_key: str = "") -> Optional[dict]:
        import json
        self._evict(user_key)
        best = None
        best_ts = -1.0
        for path in self._iter_user_files(user_key):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                ts = float(item.get("timestamp") or 0)
                if ts > best_ts:
                    best_ts = ts
                    best = item
            except Exception:
                continue
        return best


def session_user_key(request, current_user: dict) -> str:
    """Stable cache key: browser client id > JWT username > anon."""
    try:
        cid = (request.headers.get("x-vision-client-id") or "").strip()
        if len(cid) >= 8:
            return "c_" + "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in cid[:64])
    except Exception:
        pass
    return str(
        (current_user or {}).get("username")
        or (current_user or {}).get("id")
        or "anon"
    )


# default instance
rag_cache = RAGCache(max_size=8, ttl_sec=3600.0)
