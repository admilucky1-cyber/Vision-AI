"""Persistent interactive code execution history timeline."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent / "data" / "exec_history"
ROOT.mkdir(parents=True, exist_ok=True)


def add_event(
    thread_id: str,
    code: str,
    result: Optional[str] = None,
    stdout: str = "",
    error: Optional[str] = None,
    ok: bool = True,
) -> Dict[str, Any]:
    tid = "".join(c if c.isalnum() or c in "-_" else "_" for c in (thread_id or "local"))[:64]
    path = ROOT / f"{tid}.jsonl"
    ev = {
        "id": str(uuid.uuid4())[:10],
        "ts": time.time(),
        "code": code[:8000],
        "result": result,
        "stdout": (stdout or "")[:4000],
        "error": error,
        "ok": ok,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return ev


def list_events(thread_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    tid = "".join(c if c.isalnum() or c in "-_" else "_" for c in (thread_id or "local"))[:64]
    path = ROOT / f"{tid}.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out
