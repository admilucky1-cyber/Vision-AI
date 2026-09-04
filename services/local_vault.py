"""
Persistent local vault backup — snapshots vector stats, themes metadata,
routing analytics, branches index to a user-configured directory.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT = APP_ROOT / "data" / "vault_backups"
CONFIG = APP_ROOT / "data" / "vault_config.json"


def get_config() -> Dict[str, Any]:
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"target_dir": str(DEFAULT_VAULT), "interval_min": 30, "last_backup": None}


def set_config(target_dir: str, interval_min: int = 30) -> Dict[str, Any]:
    cfg = {"target_dir": target_dir, "interval_min": int(interval_min), "last_backup": get_config().get("last_backup")}
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def run_backup(label: str = "manual") -> Dict[str, Any]:
    cfg = get_config()
    dest_root = Path(cfg.get("target_dir") or DEFAULT_VAULT)
    dest_root.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = dest_root / f"vault_{label}_{ts}"
    dest.mkdir(parents=True, exist_ok=True)

    copied: List[str] = []
    sources = [
        APP_ROOT / "data" / "routing_analytics.json",
        APP_ROOT / "data" / "branches",
        APP_ROOT / "data" / "rag_namespaces",
        APP_ROOT / "VERSION",
    ]
    for src in sources:
        if not src.exists():
            continue
        try:
            if src.is_file():
                shutil.copy2(src, dest / src.name)
                copied.append(src.name)
            else:
                target = dest / src.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(src, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                copied.append(src.name + "/")
        except Exception as e:
            copied.append(f"ERR:{src.name}:{e}")

    meta = {
        "created_at": time.time(),
        "label": label,
        "copied": copied,
        "version": (APP_ROOT / "VERSION").read_text(encoding="utf-8").strip() if (APP_ROOT / "VERSION").exists() else "?",
    }
    (dest / "vault_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    cfg["last_backup"] = meta["created_at"]
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(dest), "meta": meta}


def list_backups(limit: int = 20) -> List[Dict[str, Any]]:
    cfg = get_config()
    root = Path(cfg.get("target_dir") or DEFAULT_VAULT)
    if not root.exists():
        return []
    items = []
    for p in sorted(root.glob("vault_*"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        meta = {}
        mp = p / "vault_meta.json"
        if mp.exists():
            try:
                meta = json.loads(mp.read_text(encoding="utf-8"))
            except Exception:
                pass
        items.append({"path": str(p), "name": p.name, "meta": meta})
    return items
