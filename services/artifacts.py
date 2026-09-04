"""Disk-backed generation artifacts (prefer paths over huge base64 in jobs)."""
from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vision-ai.artifacts")
ROOT = Path(__file__).resolve().parent.parent / "data" / "artifacts"
ROOT.mkdir(parents=True, exist_ok=True)


def save_image_b64(job_id: str, b64: str) -> Optional[str]:
    try:
        raw = b64
        if "," in raw and raw.strip().startswith("data:"):
            raw = raw.split(",", 1)[1]
        data = base64.b64decode(raw)
        if len(data) > 25_000_000:
            logger.warning("artifact too large")
            return None
        safe = re.sub(r"[^a-zA-Z0-9_-]", "", job_id)[:64] or "job"
        path = ROOT / f"{safe}.png"
        path.write_bytes(data)
        return str(path.relative_to(Path(__file__).resolve().parent.parent))
    except Exception as e:
        logger.warning("save artifact: %s", e)
        return None
