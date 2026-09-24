"""
Vision AI Smart Video Pipeline v6.4.0
------------------------------------
Low-resource video assembly: images → video, audio mix, effects.
Designed for modest GPUs/CPUs (e.g. G4-class): prefers ffmpeg composition
over heavy generative models. Optional hook to studio GPU workers for I2V.

Honest scope:
- Best *efficiency* path for slideshow/product/explainers with sound & effects
- Full generative text-to-video still requires external GPU workers when available
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vision-ai.smart-video")

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "data" / "video_out"
ASSET_DIR = BASE / "data" / "video_assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ASSET_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
    logger.info("ffmpeg: %s", " ".join(cmd[:12]) + ("..." if len(cmd) > 12 else ""))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def available() -> Dict[str, Any]:
    ok = shutil.which("ffmpeg") is not None
    return {
        "ffmpeg": ok,
        "ffprobe": shutil.which("ffprobe") is not None,
        "out_dir": str(OUT_DIR),
        "modes": ["slideshow", "image_sequence", "mux_audio", "effects"],
        "generative_i2v": "via /api/studio/video when GPU worker online",
        "note": "Smart pipeline prioritizes low CPU/GPU load composition.",
    }


def build_slideshow(
    image_paths: List[str],
    *,
    duration_per_image: float = 2.5,
    fps: int = 24,
    width: int = 1280,
    height: int = 720,
    audio_path: Optional[str] = None,
    audio_volume: float = 0.35,
    transition: str = "fade",
    effect: str = "none",
    output_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a video from many images with optional background audio and light effects.
    Runs entirely on CPU via ffmpeg — suitable for small GPUs/TPUs as host only.
    """
    if not image_paths:
        raise ValueError("At least one image is required")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not installed on server")

    job_id = str(uuid.uuid4())[:12]
    work = OUT_DIR / job_id
    work.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / (output_name or f"slide_{job_id}.mp4")

    # Normalize images to same size (scale+pad) — low RAM sequential
    normed = []
    for i, p in enumerate(image_paths):
        src = Path(p)
        if not src.exists():
            raise FileNotFoundError(str(src))
        dest = work / f"img_{i:04d}.jpg"
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        if effect == "sharpen":
            vf += ",unsharp=5:5:0.5:5:5:0.0"
        elif effect == "vignette":
            vf += ",vignette=PI/4"
        elif effect == "eq":
            vf += ",eq=contrast=1.05:brightness=0.02"
        r = _run([
            FFMPEG, "-y", "-i", str(src),
            "-vf", vf, "-q:v", "3", str(dest),
        ], timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"normalize failed: {r.stderr[-400:]}")
        normed.append(dest)

    # concat demuxer with duration
    list_file = work / "list.txt"
    lines = []
    for img in normed:
        lines.append(f"file '{img.resolve()}'")
        lines.append(f"duration {duration_per_image}")
    if normed:
        lines.append(f"file '{normed[-1].resolve()}'")  # last frame hold
    list_file.write_text("\n".join(lines), encoding="utf-8")

    silent = work / "silent.mp4"
    cmd = [
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-vf", f"fps={fps},format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        str(silent),
    ]
    r = _run(cmd, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"concat failed: {r.stderr[-500:]}")

    if audio_path and Path(audio_path).exists():
        # Slideshow silent has no audio track — map video + looped soundtrack
        r = _run([
            FFMPEG, "-y", "-i", str(silent), "-stream_loop", "-1", "-i", str(audio_path),
            "-filter_complex", f"[1:a]volume={audio_volume},afade=t=in:st=0:d=0.8,afade=t=out:st=0:d=0.8[aud]",
            "-map", "0:v:0", "-map", "[aud]",
            "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            str(out),
        ], timeout=600)
        if r.returncode != 0:
            r2 = _run([
                FFMPEG, "-y", "-i", str(silent), "-i", str(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-shortest", str(out),
            ], timeout=600)
            if r2.returncode != 0:
                shutil.copy(silent, out)
                audio_applied = False
                err = (r.stderr + r2.stderr)[-400:]
            else:
                audio_applied = True
                err = None
        else:
            audio_applied = True
            err = None
    else:
        shutil.copy(silent, out)
        audio_applied = False
        err = None

    meta = {
        "job_id": job_id,
        "output": str(out),
        "url_path": f"/data/video_out/{out.name}",
        "images": len(image_paths),
        "duration_per_image": duration_per_image,
        "fps": fps,
        "width": width,
        "height": height,
        "audio_applied": audio_applied,
        "effect": effect,
        "transition": transition,
        "engine": "ffmpeg-smart-compose",
        "load_profile": "low-cpu",
        "created_at": _now(),
        "error_detail": err,
    }
    (work / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def mux_audio_on_video(
    video_path: str,
    audio_path: str,
    *,
    volume: float = 0.4,
    replace_audio: bool = False,
) -> Dict[str, Any]:
    """Add or replace soundtrack on an existing video (CPU-only)."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg required")
    vid, aud = Path(video_path), Path(audio_path)
    if not vid.exists() or not aud.exists():
        raise FileNotFoundError("video or audio missing")
    job_id = str(uuid.uuid4())[:12]
    out = OUT_DIR / f"mux_{job_id}.mp4"
    if replace_audio:
        cmd = [
            FFMPEG, "-y", "-i", str(vid), "-i", str(aud),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(out),
        ]
    else:
        cmd = [
            FFMPEG, "-y", "-i", str(vid), "-stream_loop", "-1", "-i", str(aud),
            "-filter_complex", f"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2,volume={volume}[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out),
        ]
    r = _run(cmd, timeout=600)
    if r.returncode != 0:
        # video may have no audio track — force replace style
        cmd = [
            FFMPEG, "-y", "-i", str(vid), "-i", str(aud),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(out),
        ]
        r = _run(cmd, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-400:])
    return {
        "job_id": job_id,
        "output": str(out),
        "url_path": f"/data/video_out/{out.name}",
        "engine": "ffmpeg-mux",
        "created_at": _now(),
    }


def queue_generative_if_available(
    prompt: str,
    *,
    input_image: Optional[str] = None,
    frames: int = 14,
    fps: int = 7,
    user: Optional[dict] = None,
) -> Dict[str, Any]:
    """Delegate to studio GPU worker when present; otherwise return guidance."""
    try:
        from services import studio_engine as engine
        result = engine.queue_video(
            prompt=prompt,
            mode="i2v",
            model_id="svd-xt",
            input_image=input_image,
            frames=min(frames, 25),
            fps=fps,
            seed=None,
            user=user or {"id": "system", "username": "system"},
        )
        return {"ok": True, "mode": "generative_queued", "result": result}
    except Exception as e:
        return {
            "ok": False,
            "mode": "compose_only",
            "message": (
                "GPU generative video worker not available. "
                "Use slideshow/compose endpoints for low-load video with sound, "
                "or attach Colab/RunPod worker for I2V."
            ),
            "error": str(e),
        }
