"""
Vision AI v4 — Model registry + job state machine.
JSON file backend (dev); interface is repository-shaped for SQLite/Postgres later.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vision-ai.model_registry")

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DATA.mkdir(parents=True, exist_ok=True)
REGISTRY_PATH = DATA / "model_registry.json"
_LOCK = threading.RLock()

JOB_STATES = (
    "queued", "claimed", "preparing", "downloading_model", "loading_model",
    "running", "uploading", "completed", "failed", "cancelled", "expired", "retrying",
)

DEFAULT_REGISTRY: Dict[str, Any] = {
    "version": 2,
    "updated": 0,
    "storage": {
        "accounts": {
            "A_images": {"label": "IMAGE_MODELS", "drive_folder": os.getenv("DRIVE_IMAGE_MODELS", "VISION-AI-STORAGE/IMAGE_MODELS")},
            "B_videos": {"label": "VIDEO_MODELS", "drive_folder": os.getenv("DRIVE_VIDEO_MODELS", "VISION-AI-STORAGE/VIDEO_MODELS")},
            "C_datasets": {"label": "DATASETS", "drive_folder": os.getenv("DRIVE_DATASETS", "VISION-AI-STORAGE/DATASETS")},
        }
    },
    "models": [
        {
            "id": "sdxl-turbo",
            "name": "SDXL Turbo",
            "type": "image",
            "family": "sdxl",
            "source": "huggingface",
            "hf_id": "stabilityai/sdxl-turbo",
            "license": "openrail++",
            "commercial_use": True,
            "vram_gb": 6,
            "minimum_vram_gb": 4,
            "capabilities": {"t2i": True, "i2i": True, "inpainting": False, "outpainting": False, "t2v": False, "i2v": False, "v2v": False, "lora": True, "control": False, "upscale": False},
            "workflows": ["t2i", "i2i", "batch"],
            "loras": [],
            "drive_path": "VISION-AI-STORAGE/IMAGE_MODELS/sdxl-turbo",
            "enabled": True,
        },
        {
            "id": "flux-schnell",
            "name": "FLUX.1 Schnell",
            "type": "image",
            "family": "flux",
            "source": "huggingface",
            "hf_id": "black-forest-labs/FLUX.1-schnell",
            "license": "apache-2.0",
            "commercial_use": True,
            "vram_gb": 12,
            "minimum_vram_gb": 8,
            "capabilities": {"t2i": True, "i2i": True, "inpainting": False, "outpainting": False, "t2v": False, "i2v": False, "v2v": False, "lora": True, "control": False, "upscale": False},
            "workflows": ["t2i", "i2i"],
            "loras": [],
            "drive_path": "VISION-AI-STORAGE/IMAGE_MODELS/flux-schnell",
            "enabled": True,
        },
        {
            "id": "pollinations-fallback",
            "name": "Pollinations (free API fallback)",
            "type": "image",
            "family": "api",
            "source": "pollinations",
            "license": "provider-terms",
            "commercial_use": False,
            "vram_gb": 0,
            "minimum_vram_gb": 0,
            "capabilities": {"t2i": True, "i2i": False, "inpainting": False, "outpainting": False, "t2v": False, "i2v": False, "v2v": False, "lora": False, "control": False, "upscale": False},
            "workflows": ["t2i"],
            "loras": [],
            "enabled": True,
            "notes": "No LoRA; quality varies; free provider limits apply",
        },
        {
            "id": "svd-xt",
            "name": "Stable Video Diffusion XT",
            "type": "video",
            "family": "svd",
            "source": "huggingface",
            "hf_id": "stabilityai/stable-video-diffusion-img2vid-xt",
            "license": "stability-ai-community",
            "commercial_use": False,
            "vram_gb": 16,
            "minimum_vram_gb": 12,
            "capabilities": {"t2i": False, "i2i": False, "inpainting": False, "outpainting": False, "t2v": False, "i2v": True, "v2v": False, "lora": False, "control": False, "upscale": False},
            "workflows": ["i2v"],
            "loras": [],
            "drive_path": "VISION-AI-STORAGE/VIDEO_MODELS/svd-xt",
            "enabled": True,
            "notes": "I2V only (needs input image). Short clips on free T4 — not 60s HD.",
            "maximum_frames": 25,
        },
    ],
    "loras": [],
    "datasets": [],
    "jobs": [],
    "artifacts": [],
}


def sanitize_drive_path(path: str) -> str:
    """Block path traversal; only allow relative VISION-AI-STORAGE paths."""
    p = (path or "").replace("\\", "/").strip()
    if not p:
        return ""
    if p.startswith("/") or ":" in p[:3]:
        raise ValueError("Absolute paths not allowed")
    parts = []
    for part in p.split("/"):
        if part in ("", "."):
            continue
        if part == ".." or part.startswith(".."):
            raise ValueError("Path traversal not allowed")
        if re.search(r"[^\w.\- ]", part) and part not in p:
            pass
        parts.append(part)
    out = "/".join(parts)
    if not out.startswith("VISION-AI-STORAGE"):
        out = "VISION-AI-STORAGE/" + out.lstrip("/")
    return out


def _load() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        data = json.loads(json.dumps(DEFAULT_REGISTRY))
        data["updated"] = time.time()
        _save(data)
        return data
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return json.loads(json.dumps(DEFAULT_REGISTRY))
        for k, v in DEFAULT_REGISTRY.items():
            data.setdefault(k, v)
        return data
    except Exception as e:
        logger.warning("registry load failed: %s", e)
        return json.loads(json.dumps(DEFAULT_REGISTRY))


def _save(data: Dict[str, Any]) -> None:
    data["updated"] = time.time()
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(REGISTRY_PATH)


def list_models(kind: Optional[str] = None) -> List[Dict[str, Any]]:
    with _LOCK:
        models = (_load().get("models") or [])
        if kind:
            models = [m for m in models if m.get("type") == kind]
        return [m for m in models if m.get("enabled", True)]


def get_model(model_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        for m in _load().get("models") or []:
            if m.get("id") == model_id:
                return m
        return None


def model_supports(model_id: str, capability: str) -> bool:
    m = get_model(model_id)
    if not m:
        return False
    caps = m.get("capabilities") or {}
    return bool(caps.get(capability))


def list_loras(model_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with _LOCK:
        loras = _load().get("loras") or []
        if model_id:
            loras = [l for l in loras if model_id in (l.get("base_models") or []) or l.get("base_model") == model_id]
        return loras


def get_lora(lora_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        for l in _load().get("loras") or []:
            if l.get("id") == lora_id:
                return l
        return None


def register_lora(entry: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        data = _load()
        entry = dict(entry)
        entry.setdefault("id", f"lora_{uuid.uuid4().hex[:10]}")
        entry.setdefault("created_at", time.time())
        if entry.get("drive_path"):
            entry["drive_path"] = sanitize_drive_path(str(entry["drive_path"]))
        data.setdefault("loras", []).append(entry)
        _save(data)
        return entry


def register_dataset(entry: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        data = _load()
        entry = dict(entry)
        entry.setdefault("id", f"ds_{uuid.uuid4().hex[:10]}")
        entry.setdefault("created_at", time.time())
        if entry.get("drive_path"):
            entry["drive_path"] = sanitize_drive_path(str(entry["drive_path"]))
        data.setdefault("datasets", []).append(entry)
        _save(data)
        return entry


def create_job(job: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        data = _load()
        job = dict(job)
        job.setdefault("id", f"job_{uuid.uuid4().hex[:12]}")
        job.setdefault("status", "queued")
        job.setdefault("created_at", time.time())
        job.setdefault("updated_at", time.time())
        job.setdefault("events", [{"at": time.time(), "status": job["status"], "msg": "created"}])
        if job.get("status") not in JOB_STATES:
            job["status"] = "queued"
        data.setdefault("jobs", []).insert(0, job)
        data["jobs"] = data["jobs"][:300]
        _save(data)
        return job


def transition_job(job_id: str, status: str, msg: str = "", **fields) -> Optional[Dict[str, Any]]:
    if status not in JOB_STATES:
        raise ValueError(f"invalid job status: {status}")
    with _LOCK:
        data = _load()
        for j in data.get("jobs") or []:
            if j.get("id") == job_id:
                j["status"] = status
                j["updated_at"] = time.time()
                j.setdefault("events", []).append({"at": time.time(), "status": status, "msg": msg})
                j["events"] = j["events"][-50:]
                j.update(fields)
                _save(data)
                return j
        return None


def update_job(job_id: str, **fields) -> Optional[Dict[str, Any]]:
    status = fields.pop("status", None)
    if status:
        return transition_job(job_id, status, fields.pop("message", ""), **fields)
    with _LOCK:
        data = _load()
        for j in data.get("jobs") or []:
            if j.get("id") == job_id:
                j.update(fields)
                j["updated_at"] = time.time()
                _save(data)
                return j
        return None


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        for j in _load().get("jobs") or []:
            if j.get("id") == job_id:
                return j
        return None


def list_jobs(limit: int = 50, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with _LOCK:
        jobs = _load().get("jobs") or []
        if owner_id:
            jobs = [j for j in jobs if j.get("owner_id") == owner_id or j.get("user") == owner_id]
        return jobs[:limit]


def add_artifact(art: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        data = _load()
        art = dict(art)
        art.setdefault("id", f"art_{uuid.uuid4().hex[:12]}")
        art.setdefault("created_at", time.time())
        data.setdefault("artifacts", []).insert(0, art)
        data["artifacts"] = data["artifacts"][:500]
        _save(data)
        return art


def storage_map() -> Dict[str, Any]:
    with _LOCK:
        return (_load().get("storage") or {})


def snapshot() -> Dict[str, Any]:
    with _LOCK:
        data = _load()
        return {
            "version": data.get("version"),
            "updated": data.get("updated"),
            "models": len(data.get("models") or []),
            "loras": len(data.get("loras") or []),
            "datasets": len(data.get("datasets") or []),
            "jobs": len(data.get("jobs") or []),
            "artifacts": len(data.get("artifacts") or []),
            "storage": data.get("storage"),
        }
