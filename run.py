#!/usr/bin/env python3
"""Production entrypoint — reads PORT from env. Supports --bundle workspace export."""
from __future__ import annotations

import os
import sys
import json
import zipfile
from datetime import datetime
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def bundle_workspace() -> int:
    """Package themes config, analytics, data dir, VERSION into a portable zip."""
    root = Path(__file__).resolve().parent
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out = root / "downloads" / f"vision_workspace_bundle_{ts}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    include = [
        "VERSION",
        "data",
        ".env.example",
        "frontend/static/css/aether-v50.css",
        "frontend/static/js/aether-power.js",
        "frontend/static/js/aether-advanced.js",
        "AETHER_ADVANCED_v5.1.md",
    ]
    # optional notes
    for extra in root.glob("AETHER*.md"):
        include.append(extra.name)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        meta = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "version": (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").exists() else "unknown",
            "note": "Portable Aether workspace fragment (config/data/assets). Not a full app binary.",
        }
        zf.writestr("bundle_meta.json", json.dumps(meta, indent=2))
        for rel in include:
            p = root / rel
            if p.is_file():
                zf.write(p, rel)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file() and "__pycache__" not in str(f):
                        zf.write(f, str(f.relative_to(root)))
    print(f"Bundled workspace → {out}", flush=True)
    return 0


def main() -> None:
    if "--bundle" in sys.argv:
        raise SystemExit(bundle_workspace())

    port = _int_env("PORT", 5050)
    workers = _int_env("WEB_WORKERS", 1)
    host = os.environ.get("HOST", "0.0.0.0").strip() or "0.0.0.0"
    print(f"Starting Vision AI via run.py on {host}:{port} workers={workers}", flush=True)

    import uvicorn

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=max(1, workers),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
