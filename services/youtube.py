"""
Vision AI v2.0 - YouTube Service (Production Enhanced)
=======================================================
Metadata + multi-method transcript extraction + robust media download.
Supports: auto-captions, manual captions, multilingual, long videos,
quality/resolution selection, multiple container formats, error recovery.
"""

from __future__ import annotations

import os
import re
import json
import logging
import asyncio
import subprocess
import tempfile
import time
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timezone

from dotenv import load_dotenv
import shutil

load_dotenv()

def _ytdlp_ok() -> bool:
    if shutil.which("yt-dlp"):
        return True
    try:
        import yt_dlp  # noqa: F401
        return True
    except Exception:
        return False

YT_DLP_AVAILABLE = True  # resolved at call time via _ytdlp_ok()
logger = logging.getLogger("vision-ai.youtube")


def _ytdlp_cmd() -> list:
    """
    Prefer system yt-dlp binary; fall back to python -m yt_dlp. Uses official yt-dlp only (PyPI/system) — sample source zips are not bundled.
    (works on Railway/Render when only the pip package is installed).
    """
    import sys
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]



YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
API_BASE = "https://www.googleapis.com/youtube/v3"

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)
HISTORY_FILE = DOWNLOAD_DIR / "download_history.json"

# Preferred languages for transcripts (ordered)
TRANSCRIPT_LANGS = [
    "en", "en-US", "en-GB", "en-IN",
    "ur", "hi", "ar", "es", "fr", "de", "pt", "id", "tr", "ru", "ja", "ko", "zh-Hans", "zh-Hant",
]

_VIDEO_ID_PATTERNS = [
    r"(?:youtube\.com/watch\?[^\"'\s]*?[?&]v=|youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})",
    r"youtu\.be/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/live/([a-zA-Z0-9_-]{11})",
    r"m\.youtube\.com/watch\?[^\"'\s]*?[?&]v=([a-zA-Z0-9_-]{11})",
]

# Format maps for download system
VIDEO_FORMATS = {
    "mp4": {"ext": "mp4", "merge": "mp4"},
    "mkv": {"ext": "mkv", "merge": "mkv"},
    "webm": {"ext": "webm", "merge": "webm"},
    "avi": {"ext": "avi", "merge": "avi"},
}

AUDIO_FORMATS = {
    "mp3": {"ext": "mp3", "codec": "mp3"},
    "m4a": {"ext": "m4a", "codec": "m4a"},
    "aac": {"ext": "m4a", "codec": "aac"},
    "wav": {"ext": "wav", "codec": "wav"},
    "flac": {"ext": "flac", "codec": "flac"},
    "ogg": {"ext": "ogg", "codec": "vorbis"},
}

QUALITY_HEIGHT = {
    "best": None,
    "high": 1080,
    "medium": 720,
    "low": 480,
    "360p": 360,
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
}



def canonicalize_youtube_url(url: str) -> str:
    """Strip tracking params; normalize to watch?v= for yt-dlp stability."""
    if not url:
        return url
    vid = extract_video_id(url)
    if vid:
        return f"https://www.youtube.com/watch?v={vid}"
    # strip common junk
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        u = urlparse(url)
        q = parse_qs(u.query)
        for k in list(q.keys()):
            if k.lower() in ("si", "feature", "pp", "fbclid", "utm_source", "utm_medium", "utm_campaign"):
                q.pop(k, None)
        return urlunparse((u.scheme or "https", u.netloc, u.path, "", urlencode({k: v[0] for k, v in q.items()}), ""))
    except Exception:
        return url

def extract_video_id(url: str) -> Optional[str]:
    if not url:
        return None
    for pattern in _VIDEO_ID_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url.strip()):
        return url.strip()
    return None


_extract_video_id = extract_video_id


def _parse_duration(iso_duration: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or "")
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


def _parse_srt_to_text(srt_content: str, with_timestamps: bool = False) -> str:
    """Parse SRT/VTT into plain text or timestamped lines."""
    text_lines: List[str] = []
    blocks = re.split(r"\n\s*\n", srt_content.strip())
    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        # Skip numeric index
        if re.match(r"^\d+$", lines[0]):
            lines = lines[1:]
        if not lines:
            continue
        ts_line = None
        if "-->" in lines[0]:
            ts_line = lines[0]
            lines = lines[1:]
        text = re.sub(r"<[^>]+>", "", " ".join(lines)).strip()
        if not text:
            continue
        if with_timestamps and ts_line:
            # Extract start time HH:MM:SS
            m = re.match(r"(\d{1,2}:\d{2}:\d{2})", ts_line.replace(",", "."))
            stamp = m.group(1) if m else ""
            line = f"[{stamp}] {text}" if stamp else text
        else:
            line = text
        if not text_lines or text_lines[-1] != line:
            text_lines.append(line)
    return "\n".join(text_lines)


def _parse_vtt_to_text(vtt_content: str, with_timestamps: bool = False) -> str:
    """Parse WebVTT into plain or timestamped text."""
    # Strip WEBVTT header and NOTE blocks
    content = re.sub(r"^WEBVTT[^\n]*\n", "", vtt_content, flags=re.IGNORECASE)
    content = re.sub(r"NOTE[^\n]*\n(?:[^\n]+\n)*", "", content)
    return _parse_srt_to_text(content, with_timestamps=with_timestamps)


# ==========================================================
# METADATA
# ==========================================================
async def _info_via_api(video_id: str) -> Dict[str, Any]:
    if not YOUTUBE_API_KEY:
        return {}
    try:
        import httpx
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id,
            "key": YOUTUBE_API_KEY,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/videos", params=params, timeout=15.0)
            data = resp.json()
        if not data.get("items"):
            return {}
        item = data["items"][0]
        sn, cd, st = item.get("snippet", {}), item.get("contentDetails", {}), item.get("statistics", {})
        return {
            "title": sn.get("title", "Unknown"),
            "description": sn.get("description") or "",
            "uploader": sn.get("channelTitle", "Unknown"),
            "upload_date": sn.get("publishedAt", ""),
            "duration": _parse_duration(cd.get("duration", "PT0S")),
            "view_count": int(st.get("viewCount") or 0),
            "like_count": int(st.get("likeCount") or 0),
            "thumbnail": (sn.get("thumbnails") or {}).get("high", {}).get("url", ""),
            "channel_id": sn.get("channelId", ""),
            "video_id": video_id,
            "source": "youtube_api",
        }
    except Exception as e:
        logger.warning(f"YouTube API metadata failed: {e}")
        return {}


def _info_via_ytdlp_sync(url: str) -> Dict[str, Any]:
    try:
        r = subprocess.run(
            [
                *_ytdlp_cmd(),
                "--skip-download",
                "--dump-single-json",
                "--no-warnings",
                "--no-playlist",
                "--extractor-args", "youtube:player_client=android,ios,web,tv_embedded",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return {}
        data = json.loads(r.stdout)
        return {
            "title": data.get("title", "Unknown"),
            "description": data.get("description") or "",
            "uploader": data.get("uploader") or data.get("channel") or "Unknown",
            "upload_date": data.get("upload_date", ""),
            "duration": int(data.get("duration") or 0),
            "view_count": int(data.get("view_count") or 0),
            "like_count": int(data.get("like_count") or 0),
            "thumbnail": data.get("thumbnail", ""),
            "channel_id": data.get("channel_id", ""),
            "video_id": data.get("id", ""),
            "source": "yt-dlp",
            "formats_count": len(data.get("formats") or []),
        }
    except FileNotFoundError:
        logger.warning("yt-dlp not installed")
        return {}
    except Exception as e:
        logger.warning(f"yt-dlp metadata error: {e}")
        return {}


async def get_video_info(url: str) -> Dict[str, Any]:
    video_id = extract_video_id(url)
    if not video_id:
        return {}
    info = await _info_via_api(video_id)
    if info:
        return info
    return await asyncio.to_thread(_info_via_ytdlp_sync, url)


# ==========================================================
# TRANSCRIPT — multi-method with automatic fallback
# ==========================================================
def _segments_to_text(segments, with_timestamps: bool = False) -> str:
    texts = []
    for seg in segments or []:
        if isinstance(seg, dict):
            t = (seg.get("text") or "").replace("\n", " ").strip()
            start = seg.get("start")
        else:
            t = (getattr(seg, "text", "") or "").replace("\n", " ").strip()
            start = getattr(seg, "start", None)
        if not t:
            continue
        if with_timestamps and start is not None:
            try:
                s = float(start)
                h, rem = divmod(int(s), 3600)
                m, sec = divmod(rem, 60)
                stamp = f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"
                texts.append(f"[{stamp}] {t}")
            except Exception:
                texts.append(t)
        else:
            texts.append(t)
    return "\n".join(texts) if with_timestamps else " ".join(texts)


def _transcript_via_api(video_id: str, with_timestamps: bool = False, languages: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Primary method: youtube-transcript-api (no API key)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        logger.debug("youtube-transcript-api not installed")
        return None

    langs = languages or TRANSCRIPT_LANGS
    try:
        # Try modern instance API first (v1.x), fall back to class methods (v0.6)
        api = None
        try:
            api = YouTubeTranscriptApi()
        except Exception:
            api = None

        segments = None
        lang_used = None
        is_generated = False

        if api is not None and hasattr(api, "fetch"):
            for lang in langs:
                try:
                    fetched = api.fetch(video_id, languages=[lang])
                    if fetched:
                        # FetchedTranscript may be iterable of snippets
                        segs = []
                        for item in fetched:
                            if isinstance(item, dict):
                                segs.append(item)
                            else:
                                segs.append({
                                    "text": getattr(item, "text", ""),
                                    "start": getattr(item, "start", 0),
                                    "duration": getattr(item, "duration", 0),
                                })
                        if segs:
                            segments = segs
                            lang_used = lang
                            break
                except Exception:
                    continue
            if segments is None:
                try:
                    listing = api.list(video_id) if hasattr(api, "list") else None
                    if listing:
                        for t in listing:
                            try:
                                fetched = t.fetch()
                                segs = []
                                for item in fetched:
                                    if isinstance(item, dict):
                                        segs.append(item)
                                    else:
                                        segs.append({
                                            "text": getattr(item, "text", ""),
                                            "start": getattr(item, "start", 0),
                                            "duration": getattr(item, "duration", 0),
                                        })
                                if segs:
                                    segments = segs
                                    lang_used = getattr(t, "language_code", "unknown")
                                    is_generated = bool(getattr(t, "is_generated", False))
                                    break
                            except Exception:
                                continue
                except Exception:
                    pass
        else:
            # Legacy class-method API
            try:
                segments = YouTubeTranscriptApi.get_transcript(video_id, languages=langs[:5])
                lang_used = "en"
            except Exception:
                try:
                    tlist = YouTubeTranscriptApi.list_transcripts(video_id)
                    transcript = None
                    try:
                        transcript = tlist.find_transcript(langs[:8])
                    except Exception:
                        try:
                            transcript = tlist.find_generated_transcript(langs[:5])
                            is_generated = True
                        except Exception:
                            for t in tlist:
                                transcript = t
                                is_generated = bool(getattr(t, "is_generated", False))
                                break
                    if transcript is not None:
                        segments = transcript.fetch()
                        lang_used = getattr(transcript, "language_code", None) or "unknown"
                except Exception as e:
                    logger.info(f"youtube-transcript-api list failed: {e}")
                    return None

        if not segments:
            return None

        text = _segments_to_text(segments, with_timestamps=with_timestamps)
        if not text or len(text.strip()) < 20:
            return None
        return {
            "text": text.strip(),
            "language": lang_used or "unknown",
            "is_generated": is_generated,
            "method": "youtube-transcript-api",
            "char_count": len(text),
        }
    except Exception as e:
        logger.info(f"youtube-transcript-api failed: {e}")
        return None


def _transcript_via_ytdlp(video_id: str, with_timestamps: bool = False, languages: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Fallback: download auto/manual subs via yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    langs = languages or ["en.*", "en", "ur.*", "hi.*", ".*"]
    lang_arg = ",".join(langs[:6])
    try:
        with tempfile.TemporaryDirectory() as tmp:
            outtmpl = str(Path(tmp) / "subs")
            subprocess.run(
                [
                    *_ytdlp_cmd(),
                    "--skip-download",
                    "--write-auto-sub",
                    "--write-sub",
                    "--sub-lang", lang_arg,
                    "--sub-format", "vtt/srt/best",
                    "--convert-subs", "srt",
                    "-o", outtmpl,
                    "--no-warnings",
                    "--no-playlist",
                    "--extractor-args", "youtube:player_client=android,ios,web,tv_embedded",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )
            written = sorted(
                list(Path(tmp).glob("*.srt")) + list(Path(tmp).glob("*.vtt")),
                key=lambda p: p.stat().st_size,
                reverse=True,
            )
            if not written:
                return None
            raw = written[0].read_text(encoding="utf-8", errors="ignore")
            if written[0].suffix.lower() == ".vtt":
                text = _parse_vtt_to_text(raw, with_timestamps=with_timestamps)
            else:
                text = _parse_srt_to_text(raw, with_timestamps=with_timestamps)
            if not text or len(text.strip()) < 20:
                return None
            # Infer language from filename (e.g. subs.en.srt)
            lang_used = "unknown"
            name = written[0].name.lower()
            for lang in TRANSCRIPT_LANGS:
                if f".{lang.lower()}" in name or f".{lang.lower().split('-')[0]}." in name:
                    lang_used = lang
                    break
            return {
                "text": text.strip(),
                "language": lang_used,
                "is_generated": "auto" in name or True,
                "method": "yt-dlp-subs",
                "char_count": len(text),
            }
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning(f"yt-dlp subtitle error: {e}")
        return None


async def get_video_transcript(
    url: str,
    with_timestamps: bool = False,
    languages: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Retrieve transcript with automatic fallback chain:
      1. youtube-transcript-api (manual → generated, multi-lang)
      2. yt-dlp subtitle download
    Returns plain text (or timestamped lines if with_timestamps=True).
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None

    result = await asyncio.to_thread(_transcript_via_api, video_id, with_timestamps, languages)
    if result and result.get("text") and len(result["text"]) > 40:
        logger.info(
            f"✅ Transcript via {result['method']} "
            f"({result.get('char_count')} chars, lang={result.get('language')}, "
            f"generated={result.get('is_generated')})"
        )
        return result["text"]

    result = await asyncio.to_thread(_transcript_via_ytdlp, video_id, with_timestamps, languages)
    if result and result.get("text") and len(result["text"]) > 40:
        logger.info(
            f"✅ Transcript via {result['method']} "
            f"({result.get('char_count')} chars, lang={result.get('language')})"
        )
        return result["text"]

    logger.info(f"No transcript available for {video_id}")
    return None


async def get_video_transcript_detailed(
    url: str,
    with_timestamps: bool = False,
    languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Same as get_video_transcript but returns metadata about the retrieval."""
    video_id = extract_video_id(url)
    empty = {
        "text": None,
        "language": None,
        "is_generated": None,
        "method": None,
        "char_count": 0,
        "has_transcript": False,
        "video_id": video_id,
    }
    if not video_id:
        return empty

    for fn in (_transcript_via_api, _transcript_via_ytdlp):
        result = await asyncio.to_thread(fn, video_id, with_timestamps, languages)
        if result and result.get("text") and len(result["text"]) > 40:
            result["has_transcript"] = True
            result["video_id"] = video_id
            return result
    return empty


async def get_video_context(url: str, max_transcript_chars: int = 25000) -> Dict[str, Any]:
    info = await get_video_info(url)
    detailed = await get_video_transcript_detailed(url)
    transcript = detailed.get("text")
    parts: List[str] = []
    if info:
        parts.append(
            "[YOUTUBE VIDEO]\n"
            f"Title: {info.get('title')}\n"
            f"Channel: {info.get('uploader')}\n"
            f"Duration: {info.get('duration')}s\n"
            f"Views: {info.get('view_count')}\n"
            f"Video ID: {info.get('video_id') or extract_video_id(url)}"
        )
        desc = (info.get("description") or "").strip()
        if desc:
            parts.append(f"[Video Description]\n{desc[:2000]}")
    else:
        parts.append(f"[YOUTUBE VIDEO]\nURL: {url}\nVideo ID: {extract_video_id(url)}")
    if transcript:
        trimmed = transcript[:max_transcript_chars]
        if len(transcript) > max_transcript_chars:
            trimmed += "\n...[transcript truncated for length]"
        lang = detailed.get("language") or "unknown"
        gen = "auto-generated" if detailed.get("is_generated") else "manual"
        parts.append(
            f"[VIDEO TRANSCRIPT — PRIMARY SOURCE FOR SUMMARY]\n"
            f"Language: {lang} | Type: {gen} | Method: {detailed.get('method')}\n"
            "Summarize from this transcript. Do not invent content not present here.\n"
            f"{trimmed}"
        )
    else:
        parts.append(
            "[VIDEO TRANSCRIPT]\nTranscript unavailable (captions disabled, restricted region, "
            "or not yet generated). Use title/description only and clearly state that the full "
            "transcript could not be retrieved."
        )
    return {
        "info": info,
        "transcript": transcript,
        "transcript_meta": detailed,
        "context_block": "\n\n".join(parts),
        "has_transcript": bool(transcript),
    }


# ==========================================================
# COOKIES
# ==========================================================
# On servers there is usually no browser profile. Auto-probing Chrome/Edge
# causes "Could not copy Chrome cookie database" and breaks downloads.
# Strategy: use ONLY an explicit cookies file when provided. Never call
# --cookies-from-browser unless YTDLP_COOKIES_FROM_BROWSER is set AND
# YTDLP_ALLOW_BROWSER_COOKIES=1 (opt-in for local desktop use).

def _resolve_cookies_file() -> Optional[str]:
    """Return path to a Netscape cookies.txt if configured, else None."""
    env_cookies = (os.getenv("YTDLP_COOKIES") or os.getenv("YOUTUBE_COOKIES") or "").strip()
    if env_cookies:
        # Relative paths resolve from project root / cwd (Railway: /app)
        cand = Path(env_cookies)
        if not cand.is_file():
            cand = Path.cwd() / env_cookies
        if not cand.is_file():
            cand = Path(__file__).resolve().parent.parent / env_cookies
        if cand.is_file() and cand.stat().st_size > 0:
            logger.info(f"Using cookies file: {cand}")
            return str(cand)
        logger.warning(f"YTDLP_COOKIES set but file not found: {env_cookies}")

    for name in ("cookies.txt", "cookies.txt.txt"):
        static = BASE_DIR / name
        if static.is_file() and static.stat().st_size > 0:
            logger.info(f"Using static cookies: {name}")
            return str(static)
    return None


def _browser_cookies_allowed() -> Optional[str]:
    """Opt-in browser cookie extraction (desktop only). Disabled by default."""
    if os.getenv("YTDLP_ALLOW_BROWSER_COOKIES", "").strip().lower() not in ("1", "true", "yes"):
        return None
    browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER", "").strip()
    return browser or None


def _generate_cookies_file() -> Optional[str]:
    """Backward-compatible name — resolves cookie file only (no browser probe)."""
    return _resolve_cookies_file()


def _cleanup_temp_cookies(cookies_path: Optional[str]) -> None:
    # We no longer create temp cookie files; keep as no-op for callers.
    return


# ==========================================================
# DOWNLOAD HISTORY
# ==========================================================
def _load_history() -> List[dict]:
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_history(entries: List[dict]) -> None:
    try:
        # Keep last 100
        HISTORY_FILE.write_text(json.dumps(entries[-100:], indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not save download history: {e}")


def _append_history(entry: dict) -> None:
    hist = _load_history()
    hist.append(entry)
    _save_history(hist)


def get_download_history(limit: int = 50) -> List[dict]:
    return list(reversed(_load_history()))[:limit]


# ==========================================================
# DOWNLOAD (full format / quality support)
# ==========================================================
_FFMPEG_CACHE: Optional[bool] = None
_FFMPEG_PATH: Optional[str] = None


def _find_ffmpeg() -> Optional[str]:
    """Locate a real ffmpeg binary (not a Windows Store/winget shim)."""
    global _FFMPEG_PATH
    if _FFMPEG_PATH is not None:
        return _FFMPEG_PATH or None

    import shutil
    candidates: List[str] = []

    # Explicit env wins
    for key in ("FFMPEG_LOCATION", "YTDLP_FFMPEG_LOCATION", "FFMPEG_BINARY"):
        v = (os.getenv(key) or "").strip().strip('"')
        if v:
            candidates.append(v)

    # shutil.which (respects PATH)
    which = shutil.which("ffmpeg")
    if which:
        candidates.append(which)
    which_dir = shutil.which("ffmpeg.exe")
    if which_dir:
        candidates.append(which_dir)

    # Common Windows install locations (Gyan full_build via winget)
    home = Path.home()
    windir_candidates = [
        home / "AppData/Local/Microsoft/WinGet/Links",  # winget command aliases
        home / "AppData/Local/Microsoft/WinGet/Packages",
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
        Path("C:/Program Files (x86)/ffmpeg/bin"),
        home / "scoop/apps/ffmpeg/current/bin",
        home / "chocolatey/bin",
    ]
    for base in windir_candidates:
        try:
            if base.is_dir():
                # Winget packages nest version folders
                for p in base.rglob("ffmpeg.exe"):
                    candidates.append(str(p))
                    break
        except Exception:
            pass
        direct = base / "ffmpeg.exe" if base.suffix != ".exe" else base
        if Path(str(direct)).is_file():
            candidates.append(str(direct))

    # Unix
    candidates.extend(["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"])

    seen = set()
    for cmd in candidates:
        if not cmd or cmd in seen:
            continue
        seen.add(cmd)
        # Skip zero-byte Windows app-execution aliases (AppInstaller shims)
        try:
            p = Path(cmd)
            if p.is_file() and p.stat().st_size < 2048 and p.suffix.lower() == ".exe":
                # Windows Store / WinGet app-execution alias shim — skip
                logger.debug(f"Skipping likely shim: {cmd} ({p.stat().st_size} bytes)")
                continue
            r = subprocess.run(
                [cmd, "-version"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if r.returncode == 0 and "ffmpeg version" in (r.stdout or r.stderr or "").lower():
                _FFMPEG_PATH = cmd
                logger.info(f"✅ ffmpeg found: {cmd}")
                return cmd
        except Exception:
            continue

    _FFMPEG_PATH = ""
    logger.warning("ffmpeg not found on PATH — MP3 conversion disabled (native audio still works)")
    return None


def _ffmpeg_available() -> bool:
    global _FFMPEG_CACHE
    if _FFMPEG_CACHE is not None:
        return _FFMPEG_CACHE
    _FFMPEG_CACHE = _find_ffmpeg() is not None
    return _FFMPEG_CACHE


def _ffmpeg_location_args() -> List[str]:
    """Args to pass yt-dlp so it uses the same binary we detected."""
    path = _find_ffmpeg()
    if path:
        # yt-dlp wants the directory OR the binary; directory is more reliable
        p = Path(path)
        loc = str(p.parent if p.name.lower().startswith("ffmpeg") else p)
        return ["--ffmpeg-location", loc]
    return []


def _build_format_selector(
    *,
    audio_only: bool = False,
    height: Optional[int] = None,
    quality: str = "best",
    video_format: str = "mp4",
    audio_format: str = "mp3",
    audio_bitrate: Optional[str] = None,
) -> Tuple[str, List[str], Dict[str, Any]]:
    """Return (format_string, extra_args, meta).

    meta may include:
      - needs_ffmpeg: bool
      - audio_format_effective: str  (may differ from requested if ffmpeg missing)
      - note: optional user-facing note
    """
    extra: List[str] = []
    meta: Dict[str, Any] = {"needs_ffmpeg": False, "note": None}

    if audio_only:
        requested = (audio_format or "mp3").lower()
        # Formats that require ffmpeg post-processing
        convert_needed = requested in ("mp3", "wav", "flac", "ogg", "aac")
        # m4a is often available natively from YouTube (no convert)
        has_ffmpeg = _ffmpeg_available()
        meta["needs_ffmpeg"] = convert_needed and has_ffmpeg

        if convert_needed and not has_ffmpeg:
            # Fall back to native bestaudio (usually m4a/webm) — still usable audio
            fmt = "bestaudio[ext=m4a]/bestaudio/best"
            # Do NOT pass -x / --audio-format (that triggers ffmpeg postprocessing)
            meta["audio_format_effective"] = "m4a"
            meta["note"] = (
                "ffmpeg not installed on server — delivered native audio (usually M4A) "
                "instead of MP3. Install ffmpeg for MP3/WAV/FLAC conversion: "
                "`sudo apt install ffmpeg` or deploy via the project Dockerfile."
            )
            logger.warning("ffmpeg missing — audio download will use native stream (no MP3 convert)")
            return fmt, extra, meta

        af = AUDIO_FORMATS.get(requested, AUDIO_FORMATS["mp3"])
        fmt = "bestaudio/best"
        extra.extend(["-x", "--audio-format", af["ext"]])
        if audio_bitrate:
            br = audio_bitrate if str(audio_bitrate).upper().endswith("K") else f"{audio_bitrate}K"
            extra.extend(["--audio-quality", br])
        else:
            extra.extend(["--audio-quality", "0"])
        meta["audio_format_effective"] = af["ext"]
        extra.extend(_ffmpeg_location_args())
        return fmt, extra, meta

    # Video
    h = height
    if h is None and quality:
        h = QUALITY_HEIGHT.get(quality.lower())

    vf = VIDEO_FORMATS.get(video_format.lower(), VIDEO_FORMATS["mp4"])
    merge_fmt = vf["merge"]
    # Merging video+audio needs ffmpeg; prefer progressive single-file when possible
    has_ffmpeg = _ffmpeg_available()
    if h:
        if has_ffmpeg:
            fmt = (
                f"bestvideo[height<={h}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
                f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={h}]+bestaudio/"
                f"best[height<={h}][ext={vf['ext']}]/"
                f"best[height<={h}]/best"
            )
            extra.extend(["--merge-output-format", merge_fmt])
        else:
            # Progressive formats only (no merge) when ffmpeg absent
            fmt = f"best[height<={h}][ext={vf['ext']}]/best[height<={h}]/best"
            meta["note"] = (
                "ffmpeg not installed — using progressive stream (may be lower quality). "
                "Install ffmpeg for best video+audio merge."
            )
    else:
        if has_ffmpeg:
            fmt = f"best[ext={vf['ext']}]/bestvideo+bestaudio/best"
            extra.extend(["--merge-output-format", merge_fmt])
        else:
            fmt = f"best[ext={vf['ext']}]/best"
            meta["note"] = (
                "ffmpeg not installed — using progressive stream. "
                "Install ffmpeg for best quality merge."
            )
    if has_ffmpeg:
        extra.extend(_ffmpeg_location_args())
    return fmt, extra, meta




async def list_direct_download_options(url: str, max_video: int = 8, max_audio: int = 6) -> Dict[str, Any]:
    """
    List best video/audio formats with *direct CDN URLs* for IDM/FDM/browser.
    Does NOT store files on the server.
    """
    def _dump():
        args = [
            *_ytdlp_cmd(),
            "--skip-download",
            "--dump-single-json",
            "--no-warnings",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=android,ios,web,tv_embedded",
            url,
        ]
        cpath = _resolve_cookies_file() if "_resolve_cookies_file" in dir() else None
        try:
            cpath = _resolve_cookies_file()
        except Exception:
            cpath = None
        if cpath:
            args[1:1] = ["--cookies", cpath]  # after cmd
            # rebuild properly
            args = [
                *_ytdlp_cmd(),
                "--cookies", cpath,
                "--skip-download",
                "--dump-single-json",
                "--no-warnings",
                "--no-playlist",
                "--extractor-args", "youtube:player_client=android,ios,web,tv_embedded",
                url,
            ]
        return subprocess.run(args, capture_output=True, text=True, timeout=90)

    try:
        r = await asyncio.to_thread(_dump)
        if r.returncode != 0 or not (r.stdout or "").strip():
            err = (r.stderr or r.stdout or "yt-dlp failed")[-400:]
            return {"status": "error", "error": err, "mode": "direct"}
        data = json.loads(r.stdout)
        title = data.get("title") or "Video"
        formats = data.get("formats") or []

        video_opts = []
        audio_opts = []
        seen_v = set()
        seen_a = set()

        # Prefer progressive http(s) streams for single-file IDM downloads
        for fmt in sorted(formats, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True):
            u = fmt.get("url")
            if not u or not str(u).startswith("http"):
                continue
            proto = (fmt.get("protocol") or "")
            if "m3u8" in proto or "dash" in proto:
                continue  # skip adaptive playlists for simple IDM one-click
            height = fmt.get("height")
            acodec = fmt.get("acodec") or "none"
            vcodec = fmt.get("vcodec") or "none"
            ext = fmt.get("ext") or "mp4"
            fs = fmt.get("filesize") or fmt.get("filesize_approx")
            size_mb = round(fs / (1024 * 1024), 1) if fs else None
            abr = fmt.get("abr")

            if vcodec != "none" and height:
                key = (height, ext)
                if key in seen_v:
                    continue
                # Prefer streams that include audio (progressive)
                has_audio = acodec != "none"
                if not has_audio and height > 720:
                    continue  # skip video-only high res for one-click (needs merge)
                seen_v.add(key)
                video_opts.append({
                    "label": f"{height}p {ext.upper()}" + (" + audio" if has_audio else " (video only)"),
                    "height": height,
                    "ext": ext,
                    "url": u,
                    "size_mb": size_mb,
                    "format_id": fmt.get("format_id"),
                    "has_audio": has_audio,
                })
                if len(video_opts) >= max_video:
                    break

        for fmt in sorted(formats, key=lambda f: (f.get("abr") or 0), reverse=True):
            u = fmt.get("url")
            if not u or not str(u).startswith("http"):
                continue
            acodec = fmt.get("acodec") or "none"
            vcodec = fmt.get("vcodec") or "none"
            if acodec == "none" or (vcodec and vcodec != "none"):
                continue
            ext = fmt.get("ext") or "m4a"
            abr = int(fmt.get("abr") or 0)
            key = (ext, abr // 16)
            if key in seen_a:
                continue
            seen_a.add(key)
            fs = fmt.get("filesize") or fmt.get("filesize_approx")
            size_mb = round(fs / (1024 * 1024), 1) if fs else None
            audio_opts.append({
                "label": f"{ext.upper()} ~{abr}kbps" if abr else ext.upper(),
                "ext": ext,
                "abr": abr,
                "url": u,
                "size_mb": size_mb,
                "format_id": fmt.get("format_id"),
            })
            if len(audio_opts) >= max_audio:
                break

        return {
            "status": "success",
            "mode": "direct",
            "title": title,
            "video_id": data.get("id"),
            "video": video_opts,
            "audio": audio_opts,
            "note": (
                "Links open/download in your browser or IDM/FDM. "
                "They usually expire in a few hours. Nothing is stored on the server."
            ),
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Timed out listing formats", "mode": "direct"}
    except Exception as e:
        logger.exception("list_direct_download_options failed")
        return {"status": "error", "error": str(e), "mode": "direct"}



async def get_direct_media_urls(
    url: str,
    *,
    height: int = 1080,
    audio_only: bool = False,
    quality: str = "best",
    audio_bitrate: Optional[int] = None,
) -> Dict[str, Any]:
    """Resolve direct CDN stream URL(s) via yt-dlp.

    Audio → audio-only formats (m4a/webm), never video.
    Video → prefer adaptive bestvideo+bestaudio at requested height.
    """
    if not _ytdlp_ok():
        return {"status": "error", "error": "yt-dlp not installed. Run: pip install -U yt-dlp"}

    h = height
    if h is None:
        h = QUALITY_HEIGHT.get((quality or "best").lower())
    if h is None:
        h = 1080

    abr = audio_bitrate
    if abr is None and isinstance(quality, str):
        m_abr = re.search(r"(\d{2,3})\s*k", quality.lower())
        if m_abr:
            abr = int(m_abr.group(1))

    if audio_only:
        # Strict audio-only — never pick a video mux
        if abr:
            fmt = (
                f"bestaudio[abr<={abr}][ext=m4a]/"
                f"bestaudio[abr<={abr}][ext=webm]/"
                f"bestaudio[abr<={abr}]/"
                f"bestaudio[ext=m4a]/bestaudio/best"
            )
        else:
            fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[acodec!=none]/bestaudio/best"
    else:
        # Adaptive high-res first (real 720p/1080p). Progressive last (often 360p).
        fmt = (
            f"bestvideo[height<={h}][height>={min(h,720)}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
            f"bestvideo[height<={h}][height>={min(h,480)}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={h}][vcodec^=avc1]+bestaudio/"
            f"bestvideo[height<={h}]+bestaudio/"
            f"best[height<={h}][height>={min(h,480)}][ext=mp4]/"
            f"best[height<={h}]/best"
        )

    extractor = "youtube:player_client=android,ios,web,tv_embedded"

    def _run_get_url(fmt_str: str, extra: list) -> subprocess.CompletedProcess:
        args = [
            *_ytdlp_cmd(),
            "-f", fmt_str,
            "-g",
            "--no-playlist",
            "--no-warnings",
            "--extractor-args", extractor,
            *extra,
            url,
        ]
        return subprocess.run(args, capture_output=True, text=True, timeout=90)

    def _run_json(fmt_str: str, extra: list) -> dict:
        args = [
            *_ytdlp_cmd(),
            "-f", fmt_str,
            "-j",
            "--no-playlist",
            "--no-warnings",
            "--extractor-args", extractor,
            *extra,
            url,
        ]
        r = subprocess.run(args, capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            return {}
        try:
            lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
            if not lines:
                return {}
            return json.loads(lines[-1])
        except Exception:
            return {}

    try:
        extra: List[str] = []
        r = await asyncio.to_thread(_run_get_url, fmt, extra)
        if r.returncode != 0 or not (r.stdout or "").strip():
            cpath = _resolve_cookies_file()
            if cpath:
                extra = ["--cookies", cpath]
                r = await asyncio.to_thread(_run_get_url, fmt, extra)

        urls = [u.strip() for u in (r.stdout or "").splitlines() if u.strip().startswith("http")]
        if not urls:
            err = (r.stderr or r.stdout or "Could not resolve stream URL")[-500:]
            return {"status": "error", "error": err}

        info = await asyncio.to_thread(_run_json, fmt, extra)

        # If multiple JSON lines for merge formats, yt-dlp -j may only print one
        # Validate audio_only didn't get a video stream
        vcodec = (info.get("vcodec") or "none")
        acodec = (info.get("acodec") or "none")
        if audio_only and vcodec not in ("none", "None", None) and vcodec != "none":
            # Force audio-only retry with stricter format
            fmt2 = "bestaudio/best"
            r2 = await asyncio.to_thread(_run_get_url, fmt2, extra)
            urls2 = [u.strip() for u in (r2.stdout or "").splitlines() if u.strip().startswith("http")]
            if urls2:
                urls = urls2[:1]
                info = await asyncio.to_thread(_run_json, fmt2, extra)
                vcodec = info.get("vcodec") or "none"
                acodec = info.get("acodec") or "none"

        title = info.get("title") or ""
        ext = info.get("ext") or ("m4a" if audio_only else "mp4")
        if audio_only:
            # Never claim mp4 video as audio
            if ext in ("mp4", "webm") and (vcodec not in ("none", None, "None") and str(vcodec) != "none"):
                ext = "m4a"
            res = "audio"
            # filesize for audio tracks is much smaller; if huge, metadata is from video
            filesize = info.get("filesize") or info.get("filesize_approx")
            if filesize and filesize > 80 * 1024 * 1024:
                filesize = info.get("filesize")  # keep but label carefully
        else:
            res = info.get("resolution") or info.get("format_note") or f"{h}p"
            filesize = info.get("filesize") or info.get("filesize_approx")

        size_mb = round(filesize / (1024 * 1024), 2) if filesize else None
        height_got = info.get("height")
        abr_got = info.get("abr")

        primary = urls[0]
        audio_url = urls[1] if (not audio_only and len(urls) > 1) else None
        # For adaptive, first URL is usually video, second audio
        if not audio_only and len(urls) > 1:
            # confirm via formats if needed
            audio_url = urls[1]

        return {
            "status": "success",
            "mode": "direct",
            "title": title,
            "ext": ext if not audio_only else (ext if ext in ("m4a", "webm", "opus", "mp3", "ogg") else "m4a"),
            "resolution": res if not audio_only else "audio",
            "height": height_got,
            "abr": abr_got,
            "requested_quality": f"{h}p" if not audio_only else f"audio{f' ≤{abr}k' if abr else ''}",
            "audio_only": audio_only,
            "fps": info.get("fps"),
            "vcodec": vcodec if not audio_only else "none",
            "acodec": acodec,
            "size_mb": size_mb,
            "urls": urls,
            "primary_url": primary,
            "audio_url": audio_url,
            "expires_note": "Direct links usually expire within a few hours.",
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Timed out resolving stream URL"}
    except Exception as e:
        logger.exception("get_direct_media_urls failed")
        return {"status": "error", "error": str(e)}


async def download_video(
    url: str,
    height: int = 720,
    audio_only: bool = False,
    *,
    quality: str = "medium",
    video_format: str = "mp4",
    audio_format: str = "mp3",
    audio_bitrate: Optional[str] = None,
    format_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Download YouTube (or other yt-dlp-supported) media into downloads/.

    Supports video containers: mp4, mkv, webm, avi
    Supports audio: mp3, m4a, aac, wav, flac, ogg
    Quality: best | high | medium | low | 360p | 480p | 720p | 1080p
    """
    url = canonicalize_youtube_url(url)
    video_id = extract_video_id(url) or hashlib.md5(url.encode()).hexdigest()[:11]
    import uuid as _uuid
    download_id = _uuid.uuid4().hex[:12]
    outtmpl = str(DOWNLOAD_DIR / f"media_{download_id}_{video_id}.%(ext)s")

    format_meta: Dict[str, Any] = {}
    if format_id:
        fmt = format_id
        extra: List[str] = []
        if audio_only:
            if _ffmpeg_available():
                extra = ["-x", "--audio-format", audio_format or "mp3", "--audio-quality", "0"]
                format_meta["audio_format_effective"] = audio_format or "mp3"
            else:
                # No convert — keep native stream selected by format_id
                format_meta["audio_format_effective"] = "native"
                format_meta["note"] = (
                    "ffmpeg not installed — cannot convert to MP3. "
                    "Install: sudo apt install ffmpeg (or use Docker image)."
                )
        else:
            if _ffmpeg_available():
                extra = ["--merge-output-format", "mp4"]
    else:
        fmt, extra, format_meta = _build_format_selector(
            audio_only=audio_only,
            height=height if height else None,
            quality=quality,
            video_format=video_format,
            audio_format=audio_format,
            audio_bitrate=audio_bitrate,
        )

    def _build_args(
        use_cookies: bool = False,
        use_browser: bool = False,
        player_client: str = "android",
        format_override: Optional[str] = None,
        use_proxy: bool = False,
    ) -> list:
        # --no-config: never load yt-dlp.conf that may force --cookies-from-browser
        ua = {
            "android": "com.google.android.youtube/19.09.37 (Linux; U; Android 14) gzip",
            "ios": "com.google.ios.youtube/19.09.3 (iPhone16,2; U; CPU iOS 17_4 like Mac OS X)",
            "mweb": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "tv_embedded": "Mozilla/5.0 (ChromiumStylePrivetCast) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "web": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }.get(player_client, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        a = [
            *_ytdlp_cmd(),
            "--no-config",
            "--ignore-config",
            "-f", format_override or fmt,
            "-o", outtmpl,
            "--no-playlist",
            "--no-warnings",
            "--newline",
            "--concurrent-fragments", "1",
            "--retries", "5",
            "--fragment-retries", "5",
            "--retry-sleep", "http:2",
            "--geo-bypass",
            "--no-check-certificates",
            "--extractor-args", f"youtube:player_client={player_client}",
            "--user-agent", ua,
            *extra,
        ]
        if use_proxy:
            try:
                from services.ytdlp_proxy import get_working_proxy
                proxy = get_working_proxy()
            except Exception:
                proxy = None
            if proxy:
                a.extend(["--proxy", proxy])
        if use_cookies:
            cpath = _resolve_cookies_file()
            if cpath:
                a.extend(["--cookies", cpath])
        if use_browser:
            browser = _browser_cookies_allowed()
            if browser:
                a.extend(["--cookies-from-browser", browser])
        a.append(url)
        return a

    def _run(args_list):
        return subprocess.run(args_list, capture_output=True, text=True, timeout=600)

    def _is_bot_block(err: str) -> bool:
        e = (err or "").lower()
        return any(
            s in e
            for s in (
                "sign in to confirm",
                "not a bot",
                "confirm you're not a bot",
                "login required",
                "http error 403",
                "http error 429",
            )
        )

    def _is_cookie_db_error(err: str) -> bool:
        e = (err or "").lower()
        return "cookie database" in e or "could not copy" in e and "cookie" in e

    # Multi-strategy: rotate player clients + progressive formats (Railway datacenter IPs often blocked)
    progressive_v = "best[height<=480][ext=mp4]/best[height<=360][ext=mp4]/best[ext=mp4]/best"
    progressive_a = "bestaudio[ext=m4a]/bestaudio/best"
    strategies = [
        # Direct first (no proxy) — local Tor socks5://127.0.0.1:9050 is refused on Railway
        {"player_client": "android", "format_override": None, "cookies": False, "proxy": False},
        {"player_client": "ios", "format_override": None, "cookies": False, "proxy": False},
        {"player_client": "mweb", "format_override": None, "cookies": False, "proxy": False},
        {"player_client": "tv_embedded", "format_override": None, "cookies": False, "proxy": False},
        {"player_client": "web", "format_override": None, "cookies": False, "proxy": False},
        {
            "player_client": "android",
            "format_override": progressive_a if audio_only else progressive_v,
            "cookies": False,
            "proxy": False,
        },
        {
            "player_client": "ios",
            "format_override": progressive_a if audio_only else progressive_v,
            "cookies": False,
            "proxy": False,
        },
        {"player_client": "android", "format_override": progressive_v if not audio_only else progressive_a, "cookies": True, "proxy": False},
        {"player_client": "web", "format_override": progressive_v if not audio_only else progressive_a, "cookies": True, "proxy": False},
        # Optional proxy only after direct failures (YTDLP_PROXY or YTDLP_AUTO_PROXY=1)
        {"player_client": "android", "format_override": progressive_v if not audio_only else progressive_a, "cookies": False, "proxy": True},
        {"player_client": "android", "format_override": progressive_v if not audio_only else progressive_a, "cookies": True, "proxy": True},
    ]
    result = None
    last_err = ""
    try:
        for i, strat in enumerate(strategies):
            use_c = bool(strat.get("cookies")) and bool(_resolve_cookies_file())
            if strat.get("cookies") and not use_c:
                continue
            use_p = bool(strat.get("proxy"))
            args = _build_args(
                use_cookies=use_c,
                use_browser=False,
                player_client=strat["player_client"],
                format_override=strat.get("format_override"),
                use_proxy=use_p,
            )
            logger.info(
                f"yt-dlp attempt {i+1}/{len(strategies)} client={strat['player_client']} cookies={use_c} proxy={use_p}"
            )
            result = await asyncio.to_thread(_run, args)
            if result.returncode == 0:
                break
            last_err = (result.stderr or result.stdout or "").strip()
            if _is_bot_block(last_err) or "connection refused" in last_err.lower() or "socks" in last_err.lower():
                try:
                    from services.ytdlp_proxy import invalidate_proxy
                    invalidate_proxy()
                except Exception:
                    pass
            if _is_cookie_db_error(last_err):
                logger.warning("Ignoring cookie-database noise; trying next client")
                continue
            # brief pause between attempts to reduce 429 stacking
            try:
                await asyncio.sleep(0.6)
            except Exception:
                pass
    except FileNotFoundError:
        return {"status": "error", "error": "yt-dlp is not installed on the server. Run: pip install -U yt-dlp"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Download timed out after 10 minutes."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

    if result is None or result.returncode != 0:
        err = (result.stderr or result.stdout or last_err or "Download failed").strip() if result else last_err
        logger.error(f"yt-dlp download failed: {err[:500]}")
        if "connection refused" in err.lower() or "socks" in err.lower() and "failed" in err.lower():
            err_short = (
                "Download proxy is unreachable (e.g. socks5://127.0.0.1:9050 with no Tor on Railway). "
                "Remove YTDLP_PROXY or set a working remote proxy. "
                "Local Tor only works with YTDLP_ALLOW_LOCAL_PROXY=1 on a machine that runs Tor. "
                "Prefer YTDLP_COOKIES=cookies.txt on Railway."
            )
        elif _is_bot_block(err):
            err_short = (
                "YouTube blocked this server IP (bot check). "
                "Fixes: (1) Export cookies.txt (Get cookies.txt LOCALLY), set YTDLP_COOKIES=cookies.txt, redeploy. "
                "(2) Optional remote proxy: YTDLP_PROXY=http://user:pass@host:port — not 127.0.0.1. "
                "(3) Retry later. Do not use socks5://127.0.0.1:9050 on Railway."
            )
        elif "ffmpeg" in err.lower() or "ffprobe" in err.lower() or "postprocessing" in err.lower():
            err_short = (
                "ffmpeg is required for merge/convert. Deploy the project Dockerfile (includes ffmpeg) "
                "or install: apt install -y ffmpeg"
            )
        elif "private" in err.lower() or "unavailable" in err.lower():
            err_short = "This video is private, region-locked, or unavailable."
        else:
            lines = [ln.strip() for ln in err.splitlines() if ln.strip()]
            useful = [ln for ln in lines if not ln.startswith("[")]
            err_short = (useful[-1] if useful else err)[:350]
            # Never show misleading "no browser cookies" for generic failures
            if "cookie" in err_short.lower() and not _resolve_cookies_file():
                err_short = (
                    "YouTube download failed after multiple clients. "
                    "Video may be restricted. Try again later or set YTDLP_COOKIES."
                )
        return {"status": "error", "error": err_short}

    matches = sorted(
        DOWNLOAD_DIR.glob(f"media_{download_id}_{video_id}.*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        matches = sorted(
            DOWNLOAD_DIR.glob(f"media_{download_id}*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    if not matches:
        return {"status": "error", "error": "Download finished but file was not found."}

    file_path = matches[0]
    size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
    entry = {
        "status": "success",
        "filename": file_path.name,
        "path": str(file_path),
        "file_size_mb": size_mb,
        "height": height,
        "audio_only": audio_only,
        "video_format": video_format if not audio_only else None,
        "audio_format": (
            format_meta.get("audio_format_effective") or audio_format
        ) if audio_only else None,
        "quality": quality,
        "video_id": video_id,
        "url": url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "note": format_meta.get("note"),
        "ffmpeg_available": _ffmpeg_available(),
    }
    _append_history(entry)
    return entry


async def estimate_download_size(
    url: str,
    *,
    audio_only: bool = False,
    height: int = 720,
    quality: str = "medium",
) -> Dict[str, Any]:
    """Estimate file size without downloading (best-effort from format list)."""
    try:
        r = await asyncio.to_thread(
            subprocess.run,
            [
                *_ytdlp_cmd(),
                "--skip-download",
                "--dump-single-json",
                "--no-warnings",
                "--no-playlist",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
        if r.returncode != 0:
            return {"status": "error", "error": "Could not fetch format info"}
        data = json.loads(r.stdout)
        formats = data.get("formats") or []
        h = height or QUALITY_HEIGHT.get(quality, 720) or 720
        best = None
        for fmt in formats:
            fs = fmt.get("filesize") or fmt.get("filesize_approx") or 0
            if not fs:
                continue
            if audio_only:
                if fmt.get("acodec") and fmt.get("acodec") != "none" and (not fmt.get("vcodec") or fmt.get("vcodec") == "none"):
                    if best is None or fs > (best.get("filesize") or 0):
                        best = {**fmt, "filesize": fs}
            else:
                fh = fmt.get("height") or 0
                if fh and fh <= h and fmt.get("vcodec") not in (None, "none"):
                    if best is None or (fh >= (best.get("height") or 0) and fs >= (best.get("filesize") or 0)):
                        best = {**fmt, "filesize": fs}
        if not best:
            return {
                "status": "success",
                "estimated_mb": None,
                "title": data.get("title"),
                "note": "Size unavailable for selected quality",
            }
        return {
            "status": "success",
            "estimated_mb": round(best["filesize"] / (1024 * 1024), 2),
            "height": best.get("height"),
            "ext": best.get("ext"),
            "title": data.get("title"),
            "format_id": best.get("format_id"),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


logger.info("👁️ Vision AI YouTube Service v2.0 (enhanced) - Ready")

__all__ = [
    "get_video_info",
    "get_video_transcript",
    "get_video_transcript_detailed",
    "get_video_context",
    "extract_video_id",
    "download_video", "get_direct_media_urls", "list_direct_download_options",
    "estimate_download_size",
    "get_download_history",
    "VIDEO_FORMATS",
    "AUDIO_FORMATS",
    "QUALITY_HEIGHT",
]
