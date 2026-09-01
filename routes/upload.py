"""
Vision AI — Upload / YouTube / Media Download Router
====================================================
Format listing, multi-format download (video + audio), transcript,
size estimation, download history, secure file serving.
"""

from __future__ import annotations

import json
import time
import re
import logging
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import Depends, APIRouter, Request, HTTPException, status, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
from services.rate_limit import limiter

from services.youtube import (
    get_video_info,
    get_video_transcript,
    get_video_transcript_detailed,
    download_video,
    estimate_download_size,
    get_download_history,
    extract_video_id,
    VIDEO_FORMATS,
    AUDIO_FORMATS,
    QUALITY_HEIGHT,
)

router = APIRouter(prefix="/upload", tags=["YouTube"])
logger = logging.getLogger("vision-ai.upload")

DOWNLOAD_DIR = Path(__file__).resolve().parent.parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)

MAX_DOWNLOAD_TIMEOUT = 600
MAX_FORMAT_TIMEOUT = 45


# ==========================================================
# MODELS
# ==========================================================
class FormatResponse(BaseModel):
    status: str
    title: str
    duration: int = 0
    thumbnail: str = ""
    combined_formats: List[dict]
    video_formats: List[dict]
    audio_formats: List[dict]
    supported_video_exts: List[str] = list(VIDEO_FORMATS.keys())
    supported_audio_exts: List[str] = list(AUDIO_FORMATS.keys())
    quality_presets: List[str] = list(QUALITY_HEIGHT.keys())


class DownloadResponse(BaseModel):
    status: str
    filename: str = ""
    file_size_mb: float = 0.0
    download_url: str = ""
    video_id: str = ""
    quality: str = ""
    audio_only: bool = False
    error: Optional[str] = None


class VideoInfoResponse(BaseModel):
    status: str
    title: str
    duration: int
    uploader: str
    upload_date: str
    view_count: int
    thumbnail: str
    description: str
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None
    transcript_generated: Optional[bool] = None
    has_transcript: bool = False


class DownloadRequest(BaseModel):
    url: str
    quality: str = Field(default="medium", description="best|high|medium|low|360p|480p|720p|1080p")
    height: Optional[int] = None
    audio_only: bool = False
    video_format: str = Field(default="mp4", description="mp4|mkv|webm|avi")
    audio_format: str = Field(default="mp3", description="mp3|m4a|aac|wav|flac|ogg")
    audio_bitrate: Optional[str] = Field(default=None, description="e.g. 128K, 192K, 320K")
    format_id: Optional[str] = None


# ==========================================================
# HELPERS
# ==========================================================
async def run_ytdlp(args: List[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return await asyncio.to_thread(
            subprocess.run,
            ["yt-dlp"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Operation timed out",
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="yt-dlp is not installed. Please install it first.",
        )


def parse_formats(info: Dict[str, Any]) -> Dict[str, List[dict]]:
    combined_formats: List[dict] = []
    video_formats: List[dict] = []
    audio_formats: List[dict] = []

    for fmt in info.get("formats", []):
        if not fmt.get("format_id"):
            continue
        entry = {
            "format_id": fmt["format_id"],
            "ext": fmt.get("ext", "unknown"),
            "filesize": fmt.get("filesize") or fmt.get("filesize_approx", 0),
            "filesize_mb": round((fmt.get("filesize") or fmt.get("filesize_approx") or 0) / (1024 * 1024), 2),
            "height": fmt.get("height") or 0,
            "width": fmt.get("width") or 0,
            "abr": fmt.get("abr") or 0,
            "vcodec": fmt.get("vcodec") or "none",
            "acodec": fmt.get("acodec") or "none",
            "quality": fmt.get("format_note") or "N/A",
            "fps": fmt.get("fps") or 0,
            "tbr": fmt.get("tbr") or 0,
        }
        has_video = entry["height"] > 0 and entry["vcodec"] != "none"
        has_audio = entry["acodec"] != "none"
        if has_video and has_audio:
            combined_formats.append(entry)
        elif has_video:
            video_formats.append(entry)
        elif has_audio:
            audio_formats.append(entry)

    combined_formats.sort(key=lambda x: (x["height"], x["abr"]), reverse=True)
    video_formats.sort(key=lambda x: (x["height"], x["fps"]), reverse=True)
    audio_formats.sort(key=lambda x: x["abr"] or 0, reverse=True)
    return {
        "combined_formats": combined_formats,
        "video_formats": video_formats,
        "audio_formats": audio_formats,
    }


def is_valid_youtube_url(url: str) -> bool:
    patterns = [
        r"^(https?://)?(www\.|m\.)?youtube\.com/watch\?.*v=[a-zA-Z0-9_-]{11}",
        r"^(https?://)?(www\.)?youtu\.be/[a-zA-Z0-9_-]{11}",
        r"^(https?://)?(www\.)?youtube\.com/embed/[a-zA-Z0-9_-]{11}",
        r"^(https?://)?(www\.)?youtube\.com/shorts/[a-zA-Z0-9_-]{11}",
        r"^(https?://)?(www\.)?youtube\.com/live/[a-zA-Z0-9_-]{11}",
    ]
    return any(re.search(p, url) for p in patterns)


def sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    if len(sanitized) > 120:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        sanitized = name[: 120 - len(ext)] + ext
    return sanitized


# ==========================================================
# ROUTES
# ==========================================================
@router.get("/formats")
async def get_video_formats(
    request: Request,
    url: str = Query(..., description="YouTube video URL"),
):
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL. Must start with http:// or https://")
    if not is_valid_youtube_url(url) and not extract_video_id(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    logger.info(f"Format fetch: {url}")
    try:
        args = [
            "--no-check-certificate",
            "--no-warnings",
            "--dump-json",
            "--no-playlist",
            "--format-sort", "res,codec:av1,ext,abr",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--extractor-args", "youtube:player_client=android,web",
            url,
        ]
        result = await run_ytdlp(args, MAX_FORMAT_TIMEOUT)
        if result.returncode != 0:
            error_msg = (result.stderr or result.stdout or "Failed to fetch video information").strip()
            logger.error(f"yt-dlp formats error: {error_msg[:300]}")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": error_msg[:400]},
            )
        info = json.loads(result.stdout)
        formats = parse_formats(info)
        return {
            "status": "success",
            "title": info.get("title", "Untitled"),
            "duration": int(info.get("duration") or 0),
            "thumbnail": info.get("thumbnail") or "",
            **formats,
            "supported_video_exts": list(VIDEO_FORMATS.keys()),
            "supported_audio_exts": list(AUDIO_FORMATS.keys()),
            "quality_presets": list(QUALITY_HEIGHT.keys()),
        }
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Invalid response from video service")
    except Exception as e:
        logger.error(f"/formats error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/download", response_model=DownloadResponse)
async def download_media_get(
    request: Request,
    url: str = Query(...),
    format_id: Optional[str] = Query(None),
    quality: str = Query("medium"),
    height: Optional[int] = Query(None),
    audio_only: bool = Query(False),
    video_format: str = Query("mp4"),
    audio_format: str = Query("mp3"),
    audio_bitrate: Optional[str] = Query(None),
):
    """GET download — convenient for simple links / chat intents."""
    return await _do_download(
        request,
        url=url,
        format_id=format_id,
        quality=quality,
        height=height,
        audio_only=audio_only,
        video_format=video_format,
        audio_format=audio_format,
        audio_bitrate=audio_bitrate,
    )


@router.post("/download", response_model=DownloadResponse)
async def download_media_post(request: Request, body: DownloadRequest):
    """POST download with full options body."""
    return await _do_download(
        request,
        url=body.url,
        format_id=body.format_id,
        quality=body.quality,
        height=body.height,
        audio_only=body.audio_only,
        video_format=body.video_format,
        audio_format=body.audio_format,
        audio_bitrate=body.audio_bitrate,
    )


async def _do_download(
    request: Request,
    *,
    url: str,
    format_id: Optional[str],
    quality: str,
    height: Optional[int],
    audio_only: bool,
    video_format: str,
    audio_format: str,
    audio_bitrate: Optional[str],
) -> DownloadResponse:
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")
    if not is_valid_youtube_url(url) and not extract_video_id(url):
        raise HTTPException(status_code=400, detail="Only YouTube URLs are supported")

    video_format = (video_format or "mp4").lower()
    audio_format = (audio_format or "mp3").lower()
    if not audio_only and video_format not in VIDEO_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported video format. Use: {list(VIDEO_FORMATS)}")
    if audio_only and audio_format not in AUDIO_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format. Use: {list(AUDIO_FORMATS)}")

    # Resolve height from quality preset if not explicit
    resolved_height = height
    if resolved_height is None:
        resolved_height = QUALITY_HEIGHT.get((quality or "medium").lower())
    if resolved_height is None:
        resolved_height = 720

    logger.info(
        f"Download: url={url[:80]} quality={quality} height={resolved_height} "
        f"audio_only={audio_only} vfmt={video_format} afmt={audio_format}"
    )

    try:
        result = await download_video(
            url,
            height=resolved_height,
            audio_only=audio_only,
            quality=quality or "medium",
            video_format=video_format,
            audio_format=audio_format,
            audio_bitrate=audio_bitrate,
            format_id=format_id,
        )
        if result.get("status") != "success":
            return DownloadResponse(
                status="error",
                error=result.get("error", "Download failed"),
            )

        base_url = str(request.base_url).rstrip("/")
        download_url = f"{base_url}/upload/downloads/{result['filename']}"
        return DownloadResponse(
            status="success",
            filename=result["filename"],
            file_size_mb=result.get("file_size_mb", 0),
            download_url=download_url,
            video_id=result.get("video_id", ""),
            quality=quality or "medium",
            audio_only=audio_only,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")


@router.get("/estimate")
async def estimate_size(
    request: Request,
    url: str = Query(...),
    quality: str = Query("medium"),
    height: int = Query(720),
    audio_only: bool = Query(False),
):
    """Estimate download size without downloading."""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")
    if not is_valid_youtube_url(url) and not extract_video_id(url):
        raise HTTPException(status_code=400, detail="Only YouTube URLs are supported")
    return await estimate_download_size(url, audio_only=audio_only, height=height, quality=quality)


@router.get("/info", response_model=VideoInfoResponse)
async def get_video_info_endpoint(
    request: Request,
    url: str = Query(...),
    with_timestamps: bool = Query(False),
):
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")
    if not is_valid_youtube_url(url) and not extract_video_id(url):
        raise HTTPException(status_code=400, detail="Only YouTube URLs are supported")

    logger.info(f"Info fetch: {url}")
    try:
        info = await get_video_info(url)
        detailed = await get_video_transcript_detailed(url, with_timestamps=with_timestamps)
        return VideoInfoResponse(
            status="success",
            title=info.get("title", "Unknown"),
            duration=info.get("duration", 0),
            uploader=info.get("uploader", "Unknown"),
            upload_date=info.get("upload_date", "Unknown"),
            view_count=info.get("view_count", 0),
            thumbnail=info.get("thumbnail", ""),
            description=(info.get("description") or "")[:800],
            transcript=detailed.get("text"),
            transcript_language=detailed.get("language"),
            transcript_generated=detailed.get("is_generated"),
            has_transcript=bool(detailed.get("has_transcript")),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transcript")
async def get_transcript_endpoint(
    request: Request,
    url: str = Query(...),
    with_timestamps: bool = Query(False),
    lang: Optional[str] = Query(None, description="Preferred language code e.g. en, ur, hi"),
):
    """Dedicated transcript endpoint with language preference and timestamps."""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")
    if not is_valid_youtube_url(url) and not extract_video_id(url):
        raise HTTPException(status_code=400, detail="Only YouTube URLs are supported")
    languages = [lang] + ["en", "en-US"] if lang else None
    detailed = await get_video_transcript_detailed(url, with_timestamps=with_timestamps, languages=languages)
    if not detailed.get("has_transcript"):
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": "Transcript unavailable (captions disabled, restricted, or not generated).",
                "video_id": detailed.get("video_id"),
            },
        )
    return {
        "status": "success",
        "video_id": detailed.get("video_id"),
        "text": detailed.get("text"),
        "language": detailed.get("language"),
        "is_generated": detailed.get("is_generated"),
        "method": detailed.get("method"),
        "char_count": detailed.get("char_count"),
        "with_timestamps": with_timestamps,
    }


@router.get("/history")
async def download_history(
    request: Request,
    current_user: dict = Depends(get_current_active_user),
    limit: int = Query(30, ge=1, le=100),
):
    """Recent download history (server-side)."""
    return {"status": "success", "items": get_download_history(limit=limit)}



@router.get("/direct-options")
async def direct_options(request: Request, url: str = Query(..., min_length=8)):
    """List direct CDN links for video/audio (no server storage)."""
    from services.youtube import list_direct_download_options
    return await list_direct_download_options(url)

@router.get("/health")
async def upload_health():
    ytdlp_ok = False
    version = None
    try:
        r = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=5)
        ytdlp_ok = r.returncode == 0
        version = (r.stdout or "").strip()
    except Exception:
        pass
    ffmpeg_ok = False
    try:
        from services.youtube import _ffmpeg_available
        ffmpeg_ok = _ffmpeg_available()
    except Exception:
        try:
            r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            ffmpeg_ok = r.returncode == 0
        except Exception:
            ffmpeg_ok = False
    return {
        "status": "healthy",
        "download_dir_exists": DOWNLOAD_DIR.exists(),
        "ytdlp_available": ytdlp_ok,
        "ytdlp_version": version,
        "ffmpeg_available": ffmpeg_ok,
        "supported_video": list(VIDEO_FORMATS.keys()),
        "supported_audio": list(AUDIO_FORMATS.keys()),
        "timestamp": time.time(),
        "hint": None if ffmpeg_ok else "Install ffmpeg for MP3 conversion: sudo apt install -y ffmpeg",
    }


@router.get("/downloads/{filename}")
async def serve_downloaded_file(
    filename: str,
    dl: int = Query(0, description="1 = force attachment/octet-stream for mobile save"),
):
    """Serve downloaded media with mobile-friendly attachment headers.

    Mobile browsers often open video/audio inline instead of downloading.
    Use ?dl=1 (or any truthy dl) to force application/octet-stream + attachment.
    """
    import re as _re
    from urllib.parse import quote

    # Path traversal guard
    safe = Path(filename).name
    if safe != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not _re.match(r"^[A-Za-z0-9._\-]+$", safe):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = DOWNLOAD_DIR / safe
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    ext = file_path.suffix.lower().lstrip(".")
    mime_map = {
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "wav": "audio/wav",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
        "opus": "audio/opus",
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "avi": "video/x-msvideo",
    }
    # Always force download (attachment). Mobile browsers inline-play video/mp4 unless
    # Content-Type is generic binary. ?dl=1 is the explicit mobile path; default is also attachment.
    force_save = True  # always save; change only if you need inline preview endpoints
    media_type = "application/octet-stream" if (dl or force_save) else mime_map.get(ext, "application/octet-stream")

    ascii_name = safe.encode("ascii", "ignore").decode("ascii") or f"download.{ext}"
    disp = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(safe)}'

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=safe,
        headers={
            "Content-Disposition": disp,
            "Content-Type": media_type,
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
            "Accept-Ranges": "bytes",
            "X-Download-Options": "noopen",
        },
    )



@router.delete("/cleanup")
async def cleanup_old_files(
    current_user: dict = Depends(get_current_active_user),
    days: int = Query(7, ge=1, le=90),
):
    cutoff = time.time() - (days * 24 * 60 * 60)
    deleted = 0
    for file_path in DOWNLOAD_DIR.glob("media_*"):
        try:
            if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                file_path.unlink()
                deleted += 1
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
    return {"message": f"Cleaned up {deleted} files older than {days} days", "deleted_count": deleted}
