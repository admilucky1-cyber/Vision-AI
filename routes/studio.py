"""Vision AI Model Studio API v4 — capability-aware, ownership-checked."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

try:
    from routes.login import get_current_active_user
except Exception:
    async def get_current_active_user():
        return {"id": "guest", "username": "guest", "plan": "free"}
from services import model_registry as reg
from services import studio_engine as engine
from services.quota import can_generate_images

router = APIRouter(prefix="/api/studio", tags=["Studio"])


def _uid(user: dict) -> str:
    return str(user.get("id") or user.get("username") or "")


def _is_admin(user: dict) -> bool:
    return (user.get("role") or "") == "admin"


class GenerateIn(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    model_id: str = Field(default="sdxl-turbo", max_length=64)
    lora_id: Optional[str] = Field(default=None, max_length=64)
    negative_prompt: str = Field(default="", max_length=2000)
    width: int = Field(default=1024, ge=256, le=1536)
    height: int = Field(default=1024, ge=256, le=1536)
    steps: int = Field(default=4, ge=1, le=50)
    guidance: float = Field(default=1.0, ge=0, le=30)
    seed: Optional[int] = None
    lora_weight: float = Field(default=1.0, ge=0, le=2)


class TrainIn(BaseModel):
    dataset_id: str = Field(..., min_length=1, max_length=64)
    base_model: str = Field(default="flux-schnell", max_length=64)
    rank: int = Field(default=16, ge=4, le=128)
    epochs: int = Field(default=10, ge=1, le=50)
    resolution: int = Field(default=1024, ge=512, le=1024)
    learning_rate: float = Field(default=1e-4, ge=1e-6, le=1e-2)


class VideoIn(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    mode: str = Field(default="i2v", max_length=16)  # svd-xt is I2V
    model_id: str = Field(default="svd-xt", max_length=64)
    input_image: Optional[str] = Field(default=None, max_length=5_000_000)
    frames: int = Field(default=14, ge=1, le=25)
    fps: int = Field(default=7, ge=1, le=30)
    seed: Optional[int] = None


class DatasetIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    drive_path: str = Field(default="", max_length=500)
    image_count: int = Field(default=0, ge=0)


@router.get("/status")
async def studio_status(current_user: dict = Depends(get_current_active_user)):
    return {"ok": True, "registry": reg.snapshot()}


@router.get("/models")
async def studio_models(type: Optional[str] = None, current_user: dict = Depends(get_current_active_user)):
    return {"ok": True, "models": reg.list_models(type)}


@router.get("/loras")
async def studio_loras(model_id: Optional[str] = None, current_user: dict = Depends(get_current_active_user)):
    return {"ok": True, "loras": reg.list_loras(model_id)}


@router.get("/storage")
async def studio_storage(current_user: dict = Depends(get_current_active_user)):
    return {"ok": True, "storage": reg.storage_map()}


@router.get("/jobs")
async def studio_jobs(current_user: dict = Depends(get_current_active_user), limit: int = 30):
    limit = min(max(limit, 1), 100)
    if _is_admin(current_user):
        jobs = reg.list_jobs(limit=limit)
    else:
        jobs = reg.list_jobs(limit=limit, owner_id=_uid(current_user))
    return {"ok": True, "jobs": jobs}


@router.get("/jobs/{job_id}")
async def studio_job(job_id: str, current_user: dict = Depends(get_current_active_user)):
    job = reg.get_job(job_id)
    if not job:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Job not found"})
    if not _is_admin(current_user) and job.get("owner_id") != _uid(current_user) and job.get("user") != current_user.get("username"):
        raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "Not your job"})
    return {"ok": True, "job": job}


@router.post("/generate")
async def studio_generate(body: GenerateIn, current_user: dict = Depends(get_current_active_user)):
    plan = (current_user.get("plan") or "free").lower()
    ok, msg = can_generate_images(is_guest=bool(current_user.get("is_guest")), plan=plan)
    if not ok:
        raise HTTPException(402, detail={"code": "PAYMENT_REQUIRED", "message": msg})
    result = await engine.generate_image(
        prompt=body.prompt,
        model_id=body.model_id,
        lora_id=body.lora_id,
        negative_prompt=body.negative_prompt,
        width=body.width,
        height=body.height,
        steps=body.steps,
        guidance=body.guidance,
        seed=body.seed,
        lora_weight=body.lora_weight,
        user=current_user,
    )
    if not result.get("ok"):
        err = result.get("error") or {"code": "FAILED", "message": "Generation failed"}
        raise HTTPException(503, detail=err)
    return result


@router.post("/train")
async def studio_train(body: TrainIn, current_user: dict = Depends(get_current_active_user)):
    if current_user.get("is_guest"):
        raise HTTPException(401, detail={"code": "AUTH", "message": "Sign in required"})
    # Allow free users to QUEUE train jobs (execution needs their own Colab worker)
    result = engine.queue_lora_train(
        dataset_id=body.dataset_id,
        base_model=body.base_model,
        rank=body.rank,
        epochs=body.epochs,
        resolution=body.resolution,
        learning_rate=body.learning_rate,
        user=current_user,
    )
    if not result.get("ok"):
        raise HTTPException(400, detail=result.get("error"))
    return result


@router.post("/video")
async def studio_video(body: VideoIn, current_user: dict = Depends(get_current_active_user)):
    if current_user.get("is_guest"):
        raise HTTPException(401, detail={"code": "AUTH", "message": "Sign in required"})
    result = engine.queue_video(
        prompt=body.prompt,
        mode=body.mode,
        model_id=body.model_id,
        input_image=body.input_image,
        frames=body.frames,
        fps=body.fps,
        seed=body.seed,
        user=current_user,
    )
    if not result.get("ok"):
        raise HTTPException(400, detail=result.get("error"))
    return result


@router.post("/datasets")
async def studio_register_dataset(body: DatasetIn, current_user: dict = Depends(get_current_active_user)):
    if current_user.get("is_guest"):
        raise HTTPException(401, detail={"code": "AUTH", "message": "Sign in required"})
    try:
        entry = reg.register_dataset({
            "name": body.name,
            "description": body.description,
            "drive_path": body.drive_path,
            "image_count": body.image_count,
            "owner_id": _uid(current_user),
            "owner": current_user.get("username"),
        })
    except ValueError as e:
        raise HTTPException(400, detail={"code": "BAD_PATH", "message": str(e)})
    return {"ok": True, "dataset": entry}
