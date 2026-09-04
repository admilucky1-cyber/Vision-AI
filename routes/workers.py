"""Colab/Kaggle GPU worker registration, status, and job claim/complete API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from services import colab_worker as cw
from services import model_registry as reg

router = APIRouter(prefix="/api/workers", tags=["workers"])


class RegisterIn(BaseModel):
    url: str = Field(..., min_length=8, max_length=500)
    kind: str = Field(default="colab", max_length=32)
    secret: str = Field(default="", max_length=200)
    meta: Optional[Dict[str, Any]] = None


class HeartbeatIn(BaseModel):
    url: str = Field(..., min_length=8, max_length=500)
    secret: str = Field(default="", max_length=200)


class ClaimIn(BaseModel):
    capabilities: List[str] = Field(default_factory=lambda: ["t2i"])
    vram_gb: float = Field(default=15, ge=0, le=96)
    worker_url: Optional[str] = Field(default=None, max_length=500)


class CompleteIn(BaseModel):
    job_id: str = Field(..., min_length=4, max_length=64)
    status: str = Field(default="completed", max_length=32)
    result: Optional[Dict[str, Any]] = None
    error: str = Field(default="", max_length=2000)


def _require_worker_secret(secret: str) -> None:
    expected = (cw.REGISTER_SECRET or cw.COLAB_WORKER_SECRET or "").strip()
    if not expected:
        raise HTTPException(503, detail="Worker secrets not configured on server")
    import hmac
    if not hmac.compare_digest(str(secret or ""), expected):
        raise HTTPException(403, detail="invalid worker secret")


@router.get("")
@router.get("/")
def list_workers():
    data = cw.list_workers()
    live = {"workers": [], "any_live": False}
    try:
        if hasattr(cw, "health"):
            h = cw.health()
            if isinstance(h, dict):
                live = h
    except Exception:
        pass
    return {
        **data,
        "live": live,
        "enabled": cw.is_enabled(),
        "live_ok": cw.is_live() if hasattr(cw, "is_live") else False,
    }


@router.post("/register")
def register(body: RegisterIn):
    try:
        return cw.register_worker(
            body.url, kind=body.kind, secret=body.secret, meta=body.meta
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.post("/heartbeat")
def heartbeat(body: HeartbeatIn):
    try:
        return cw.heartbeat_worker(body.url, secret=body.secret)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.delete("")
def unregister(
    url: str,
    x_worker_secret: Optional[str] = Header(default=None, alias="X-Worker-Secret"),
):
    try:
        return cw.unregister_worker(url, secret=x_worker_secret or "")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.post("/jobs/claim")
def claim_job(
    body: ClaimIn,
    x_worker_secret: Optional[str] = Header(default=None, alias="X-Worker-Secret"),
):
    """Worker pulls next compatible queued job (image/video/train)."""
    _require_worker_secret(x_worker_secret or "")
    caps = set(c.lower() for c in (body.capabilities or []))
    jobs = reg.list_jobs(limit=80)
    for job in jobs:
        if job.get("status") != "queued":
            continue
        jtype = job.get("type")
        # capability filter
        if jtype == "image_generate" and "t2i" not in caps and "i2i" not in caps:
            continue
        if jtype == "video_generate" and "i2v" not in caps and "t2v" not in caps:
            continue
        if jtype == "lora_train" and "lora" not in caps and "train" not in caps:
            # still allow claim if worker advertises train
            if "train" not in caps:
                continue
        updated = reg.transition_job(
            job["id"],
            "claimed",
            msg="claimed by worker",
            worker_url=body.worker_url,
            claimed_vram_gb=body.vram_gb,
        )
        return {"ok": True, "job": updated or job}
    return {"ok": True, "job": None}


@router.post("/jobs/complete")
def complete_job(
    body: CompleteIn,
    x_worker_secret: Optional[str] = Header(default=None, alias="X-Worker-Secret"),
):
    _require_worker_secret(x_worker_secret or "")
    job = reg.get_job(body.job_id)
    if not job:
        raise HTTPException(404, detail="job not found")
    status = body.status if body.status in reg.JOB_STATES else ("failed" if body.error else "completed")
    result = body.result or {}
    artifact_id = None
    if status == "completed" and (result.get("image_data") or result.get("image") or result.get("url")):
        art = reg.add_artifact({
            "type": "image",
            "job_id": body.job_id,
            "owner_id": job.get("owner_id"),
            "provider": result.get("provider"),
            "size": result.get("size"),
            "has_data": bool(result.get("image_data") or result.get("image")),
        })
        artifact_id = art.get("id")
        # persist small preview path optional
        try:
            from services.artifacts import save_image_b64
            b64 = result.get("image_data") or result.get("image") or result.get("data")
            if b64 and isinstance(b64, str):
                path = save_image_b64(body.job_id, b64)
                if path:
                    reg.update_job(body.job_id, artifact_path=path)
        except Exception:
            pass
    updated = reg.transition_job(
        body.job_id,
        status,
        msg=body.error or "worker complete",
        error=body.error or None,
        result_provider=(result or {}).get("provider"),
        artifact_id=artifact_id,
    )
    return {"ok": True, "job": updated}
