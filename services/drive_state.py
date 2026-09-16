"""
Drive / model / LoRA readiness states for clearer GPU-worker errors.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Explicit states for UI / API
DRIVE_UNAVAILABLE = "DRIVE_UNAVAILABLE"
DRIVE_MOUNTING = "DRIVE_MOUNTING"
DRIVE_READY = "DRIVE_READY"
MODEL_MISSING = "MODEL_MISSING"
LORA_MISSING = "LORA_MISSING"
MODEL_READY = "MODEL_READY"
LORA_READY = "LORA_READY"
LORA_INVALID = "LORA_INVALID"
PATH_REJECTED = "PATH_REJECTED"

_ALLOWED_LORA_EXT = {".safetensors", ".pt", ".bin"}
_MAX_LORA_BYTES = int(os.getenv("MAX_LORA_BYTES", str(2 * 1024 * 1024 * 1024)))  # 2GB


def drive_root() -> Path:
    return Path(
        (
            os.getenv("VISION_DRIVE_CACHE")
            or os.getenv("COLAB_DRIVE_ROOT")
            or "/content/drive/MyDrive/vision_ai_models"
        ).rstrip("/")
    )


def detect_drive_state() -> Dict[str, Any]:
    root = drive_root()
    parent = root.parent if root.name else root
    # Colab typical mount point
    mount = Path("/content/drive")
    if str(root).startswith("/content/drive"):
        if not mount.exists():
            return {
                "state": DRIVE_UNAVAILABLE,
                "message": "Google Drive is not mounted. In Colab: drive.mount('/content/drive') and retry.",
                "path": str(root),
            }
        if not os.path.ismount(str(mount)) and not (mount / "MyDrive").exists():
            return {
                "state": DRIVE_MOUNTING,
                "message": "Google Drive mount not ready yet. Wait and retry.",
                "path": str(root),
            }
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".vision_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as e:
        return {
            "state": DRIVE_UNAVAILABLE,
            "message": f"Drive not writable: {e}",
            "path": str(root),
        }
    return {"state": DRIVE_READY, "message": "Drive ready", "path": str(root)}


def sanitize_worker_path(path: str, *, must_exist: bool = False) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate a LoRA/model path for the worker.
    Returns (resolved_path, error_dict).
    """
    raw = (path or "").strip()
    if not raw:
        return None, {
            "code": LORA_MISSING,
            "message": "No LoRA path provided",
        }
    # Reject traversal and null bytes
    if "\x00" in raw or ".." in raw.replace("\\", "/").split("/"):
        return None, {"code": PATH_REJECTED, "message": "Path traversal not allowed"}
    p = Path(raw)
    # Allow absolute under known roots only
    allowed_prefixes = [
        str(drive_root()).replace("\\", "/"),
        "/content/drive/MyDrive/vision_ai_models",
        "/content/vision_ai_cache",
        "/content/loras",
        str(Path.cwd() / "data"),
    ]
    resolved = p
    try:
        if p.is_absolute():
            rp = str(p.resolve()).replace("\\", "/")
            if not any(rp.startswith(pref.rstrip("/") + "/") or rp == pref.rstrip("/") for pref in allowed_prefixes if pref):
                # also allow VISION-AI-STORAGE style mapped under drive root
                if "VISION-AI-STORAGE" not in rp:
                    return None, {
                        "code": PATH_REJECTED,
                        "message": "LoRA path outside allowed Drive/cache directories",
                    }
        else:
            # relative → under drive root
            resolved = drive_root() / p
    except Exception as e:
        return None, {"code": PATH_REJECTED, "message": f"Invalid path: {e}"}

    if must_exist or True:
        try:
            if not resolved.exists():
                # try relative to loras folder
                alt = drive_root() / "loras" / Path(raw).name
                if alt.exists():
                    resolved = alt
                else:
                    st = detect_drive_state()
                    if st["state"] != DRIVE_READY:
                        return None, {"code": st["state"], "message": st["message"]}
                    return None, {
                        "code": LORA_MISSING,
                        "message": f"LoRA file not found: {resolved}. Place .safetensors under vision_ai_models/loras/",
                    }
        except Exception as e:
            return None, {"code": DRIVE_UNAVAILABLE, "message": str(e)}

    if resolved.is_dir():
        # pick a safetensors inside
        cands = list(resolved.glob("*.safetensors"))
        if not cands:
            return None, {"code": LORA_INVALID, "message": f"No .safetensors in directory {resolved}"}
        resolved = cands[0]

    ext = resolved.suffix.lower()
    if ext not in _ALLOWED_LORA_EXT:
        return None, {
            "code": LORA_INVALID,
            "message": f"Unsupported LoRA extension {ext}; use .safetensors",
        }
    try:
        size = resolved.stat().st_size
    except Exception as e:
        return None, {"code": LORA_MISSING, "message": str(e)}
    if size < 10_000:
        return None, {"code": LORA_INVALID, "message": "LoRA file too small / corrupted"}
    if size > _MAX_LORA_BYTES:
        return None, {"code": LORA_INVALID, "message": f"LoRA exceeds max size ({_MAX_LORA_BYTES} bytes)"}

    return str(resolved), None


def validate_lora_weight(weight: float) -> Tuple[float, Optional[Dict[str, Any]]]:
    try:
        w = float(weight)
    except Exception:
        return 1.0, {"code": LORA_INVALID, "message": "lora_weight must be a number"}
    if w < 0.05 or w > 1.5:
        return max(0.05, min(1.5, w)), {
            "code": LORA_INVALID,
            "message": "lora_weight clamped to 0.05–1.5",
            "clamped": True,
        }
    return w, None
