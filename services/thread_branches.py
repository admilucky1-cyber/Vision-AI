"""
Non-destructive chat thread branching / versioning.
Branches stored under data/branches/{user}/{root_id}/.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent / "data" / "branches"
ROOT.mkdir(parents=True, exist_ok=True)


def _user_dir(user_key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_:" else "_" for c in (user_key or "guest"))[:64]
    p = ROOT / safe
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_branch(
    user_key: str,
    root_chat_id: str,
    from_message_index: int,
    messages: List[Dict[str, Any]],
    label: str = "",
    routing_profile: str = "auto",
    system_prompt: str = "",
) -> Dict[str, Any]:
    branch_id = str(uuid.uuid4())[:12]
    # Keep history up to fork point (inclusive)
    sliced = list(messages[: max(0, from_message_index) + 1])
    rec = {
        "branch_id": branch_id,
        "root_chat_id": root_chat_id,
        "from_message_index": from_message_index,
        "label": label or f"Branch @ msg {from_message_index}",
        "routing_profile": routing_profile,
        "system_prompt": system_prompt,
        "messages": sliced,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    path = _user_dir(user_key) / f"{root_chat_id}__{branch_id}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec


def list_branches(user_key: str, root_chat_id: Optional[str] = None) -> List[Dict[str, Any]]:
    d = _user_dir(user_key)
    out = []
    for f in d.glob("*.json"):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            if root_chat_id and rec.get("root_chat_id") != root_chat_id:
                continue
            out.append({
                "branch_id": rec.get("branch_id"),
                "root_chat_id": rec.get("root_chat_id"),
                "label": rec.get("label"),
                "from_message_index": rec.get("from_message_index"),
                "routing_profile": rec.get("routing_profile"),
                "created_at": rec.get("created_at"),
                "message_count": len(rec.get("messages") or []),
            })
        except Exception:
            continue
    out.sort(key=lambda x: -float(x.get("created_at") or 0))
    return out


def get_branch(user_key: str, root_chat_id: str, branch_id: str) -> Optional[Dict[str, Any]]:
    path = _user_dir(user_key) / f"{root_chat_id}__{branch_id}.json"
    if not path.exists():
        # fallback search
        for f in _user_dir(user_key).glob(f"*__{branch_id}.json"):
            path = f
            break
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def append_message(user_key: str, root_chat_id: str, branch_id: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = get_branch(user_key, root_chat_id, branch_id)
    if not rec:
        return None
    rec.setdefault("messages", []).append(message)
    rec["updated_at"] = time.time()
    path = _user_dir(user_key) / f"{rec['root_chat_id']}__{branch_id}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec
