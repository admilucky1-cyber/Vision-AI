"""Smart Video API — low-load compose + optional generative queue."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services import smart_video as sv

logger = logging.getLogger("vision-ai.smart-video-api")
router = APIRouter(prefix="/api/smart-video", tags=["Smart Video"])

ASSET = Path(__file__).resolve().parent.parent / "data" / "video_assets"
ASSET.mkdir(parents=True, exist_ok=True)


class SlideshowJSON(BaseModel):
    image_paths: List[str]
    duration_per_image: float = Field(2.5, ge=0.5, le=30)
    fps: int = Field(24, ge=6, le=30)
    width: int = Field(1280, ge=320, le=1920)
    height: int = Field(720, ge=240, le=1080)
    audio_path: Optional[str] = None
    audio_volume: float = Field(0.35, ge=0, le=1)
    effect: str = Field("none")


class MuxIn(BaseModel):
    video_path: str
    audio_path: str
    volume: float = 0.4
    replace_audio: bool = False


class GenIn(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    input_image: Optional[str] = None
    frames: int = Field(14, ge=1, le=25)
    fps: int = Field(7, ge=1, le=30)


@router.get("/status")
def status():
    return {"ok": True, **sv.available()}


@router.post("/slideshow")
def slideshow(body: SlideshowJSON):
    try:
        return sv.build_slideshow(
            body.image_paths,
            duration_per_image=body.duration_per_image,
            fps=body.fps,
            width=body.width,
            height=body.height,
            audio_path=body.audio_path,
            audio_volume=body.audio_volume,
            effect=body.effect,
        )
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/slideshow-upload")
async def slideshow_upload(
    files: List[UploadFile] = File(...),
    duration_per_image: float = Form(2.5),
    fps: int = Form(24),
    width: int = Form(1280),
    height: int = Form(720),
    effect: str = Form("none"),
    audio: Optional[UploadFile] = File(None),
):
    if not files:
        raise HTTPException(400, "No images")
    paths = []
    for f in files:
        dest = ASSET / f"{uuid_name()}_{f.filename}"
        dest.write_bytes(await f.read())
        paths.append(str(dest))
    audio_path = None
    if audio is not None:
        ap = ASSET / f"aud_{uuid_name()}_{audio.filename}"
        ap.write_bytes(await audio.read())
        audio_path = str(ap)
    try:
        return sv.build_slideshow(
            paths,
            duration_per_image=duration_per_image,
            fps=fps,
            width=width,
            height=height,
            audio_path=audio_path,
            effect=effect,
        )
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/mux-audio")
def mux(body: MuxIn):
    try:
        return sv.mux_audio_on_video(
            body.video_path, body.audio_path, volume=body.volume, replace_audio=body.replace_audio
        )
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/generate-queue")
def generate_queue(body: GenIn):
    return sv.queue_generative_if_available(
        body.prompt, input_image=body.input_image, frames=body.frames, fps=body.fps
    )


@router.get("/download/{name}")
def download(name: str):
    # prevent path traversal
    safe = Path(name).name
    path = Path(__file__).resolve().parent.parent / "data" / "video_out" / safe
    if not path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(str(path), media_type="video/mp4", filename=safe)


def uuid_name() -> str:
    import uuid
    return str(uuid.uuid4())[:10]
