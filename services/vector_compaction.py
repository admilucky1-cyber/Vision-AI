"""Background compaction / pruning helpers for hybrid stores + chroma if present."""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("vision-ai.compact")


def compact_all() -> Dict[str, Any]:
    report: Dict[str, Any] = {"ok": True, "actions": []}
    try:
        from services.rag_engine_core import prune_all, _STORES
        r = prune_all()
        report["actions"].append({"hybrid_prune": r})
        # dedupe exact same text within namespace
        deduped = 0
        for ns, store in list(_STORES.items()):
            seen = set()
            keep = []
            for ch in store.chunks:
                key = ch.text.strip()
                if key in seen:
                    deduped += 1
                    continue
                seen.add(key)
                keep.append(ch)
            if len(keep) != len(store.chunks):
                store.chunks = keep
                # rebuild vectors roughly by re-adding texts would be heavy; mark for rebuild
                store.vectors = None
                store.bm25 = store.bm25.__class__()
                for c in store.chunks:
                    store.bm25.add(c.text)
        report["actions"].append({"deduped_chunks": deduped})
    except Exception as e:
        report["actions"].append({"hybrid_error": str(e)})
        report["ok"] = False

    try:
        from services.vector_store import vector_store
        if vector_store is not None and hasattr(vector_store, "get_stats"):
            report["actions"].append({"chroma_stats": vector_store.get_stats()})
    except Exception as e:
        report["actions"].append({"chroma": str(e)})
    return report
