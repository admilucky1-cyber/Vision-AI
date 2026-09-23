"""
Vision AI v2.0 - Web Search Service
====================================
Multi-engine real-time search with free unlimited fallbacks.

Engine order (first success wins):
1. Tavily          — if TAVILY_API_KEY set (paid/free quota)
2. ddgs            — DuckDuckGo text search (FREE, no key)
3. DuckDuckGo IA   — Instant Answer API (FREE, no key)
4. Wikipedia       — FREE facts
5. Open-Meteo      — FREE weather (auto for weather queries)

No engine is "truly unlimited" under abuse, but free backends have no API quota.
Results are cached to reduce load.
"""

from __future__ import annotations

import os
import json
import time
import hashlib
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("vision-ai.search")

# ==========================================================
# CONFIGURATION
# ==========================================================
TAVILY_API_KEY = (os.getenv("TAVILY_API_KEY") or "").strip()
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "search_cache.json"
CACHE_DURATION = 3600
MAX_CACHE_SIZE = 200
REQUEST_TIMEOUT = 18

REDIS_URL = os.getenv("REDIS_URL", "")
USE_REDIS = bool(REDIS_URL)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

# ==========================================================
# REDIS (optional)
# ==========================================================
redis_client = None
if USE_REDIS:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis cache initialized")
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable: {e}")
        USE_REDIS = False
        redis_client = None

# ==========================================================
# TAVILY (optional)
# ==========================================================
tavily = None
if TAVILY_API_KEY:
    try:
        from tavily import TavilyClient
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        logger.info("✅ Tavily API initialized")
    except Exception as e:
        tavily = None
        logger.warning(f"⚠️ Tavily init failed: {e}")

# ==========================================================
# ddgs (FREE primary)
# ==========================================================
_DDGS = None
try:
    from ddgs import DDGS
    _DDGS = DDGS
    logger.info("✅ ddgs (DuckDuckGo) available — free search enabled")
except ImportError:
    try:
        from duckduckgo_search import DDGS  # older package name
        _DDGS = DDGS
        logger.info("✅ duckduckgo_search available — free search enabled")
    except ImportError:
        logger.warning(
            "⚠️ ddgs not installed — run: pip install -U ddgs  "
            "(free unlimited DuckDuckGo search)"
        )


# ==========================================================
# CACHE
# ==========================================================
def get_cache_ttl(query: str) -> int:
    q = query.lower()
    if any(k in q for k in (
        "news", "weather", "stock", "price", "today", "latest",
        "current", "forecast", "live", "score",
    )):
        return 300
    if any(k in q for k in ("who is", "what is", "define", "meaning")):
        return 86400
    return CACHE_DURATION


class SearchCache:
    def __init__(self):
        self.mem: Dict[str, Any] = {}
        self._load()

    def _key(self, query: str) -> str:
        return hashlib.md5(query.strip().lower().encode()).hexdigest()

    def _load(self):
        if USE_REDIS:
            return
        try:
            if CACHE_FILE.exists():
                self.mem = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            self.mem = {}

    def _save(self):
        if USE_REDIS:
            return
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            # prune
            if len(self.mem) > MAX_CACHE_SIZE:
                items = sorted(self.mem.items(), key=lambda x: x[1].get("ts", 0))
                self.mem = dict(items[-MAX_CACHE_SIZE:])
            CACHE_FILE.write_text(json.dumps(self.mem), encoding="utf-8")
        except Exception as e:
            logger.debug(f"cache save: {e}")

    def get(self, query: str) -> Optional[str]:
        k = self._key(query)
        if USE_REDIS and redis_client:
            try:
                raw = redis_client.get(f"vision_search:{k}")
                if raw:
                    return raw
            except Exception:
                pass
            return None
        item = self.mem.get(k)
        if not item:
            return None
        if time.time() - item.get("ts", 0) > item.get("ttl", CACHE_DURATION):
            self.mem.pop(k, None)
            return None
        return item.get("data")

    def set(self, query: str, data: str, ttl: Optional[int] = None):
        ttl = ttl or get_cache_ttl(query)
        k = self._key(query)
        if USE_REDIS and redis_client:
            try:
                redis_client.setex(f"vision_search:{k}", ttl, data)
            except Exception:
                pass
            return
        self.mem[k] = {"data": data, "ts": time.time(), "ttl": ttl, "query": query}
        self._save()

    def clear(self):
        self.mem = {}
        if USE_REDIS and redis_client:
            try:
                for key in redis_client.scan_iter("vision_search:*"):
                    redis_client.delete(key)
            except Exception:
                pass
        try:
            if CACHE_FILE.exists():
                CACHE_FILE.unlink()
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        # Keep backward-compatible keys + dashboard keys
        return {
            "entries": len(self.mem) if not USE_REDIS else "redis",
            "total_entries": len(self.mem) if not USE_REDIS else 0,
            "max_cache_size": MAX_CACHE_SIZE,
            "cache_duration_seconds": CACHE_DURATION,
            "recent_queries": [],
            "tavily": bool(tavily),
            "ddgs": _DDGS is not None,
            "engines": available_engines(),
        }


search_cache = SearchCache()


def available_engines() -> List[str]:
    eng = []
    if tavily:
        eng.append("tavily")
    if _DDGS:
        eng.append("ddgs")
    eng.extend(["duckduckgo_ia", "wikipedia", "open_meteo"])
    return eng


# ==========================================================
# ENGINES
# ==========================================================
def search_tavily(query: str, max_results: int = 5) -> Optional[str]:
    if not tavily:
        return None
    try:
        response = tavily.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )
        parts: List[str] = []
        if response.get("answer"):
            parts.append(f"**Answer:** {response['answer']}")
        for i, r in enumerate(response.get("results") or [], 1):
            title = r.get("title") or "Result"
            content = (r.get("content") or "")[:500]
            url = r.get("url") or ""
            parts.append(f"{i}. **{title}**\n{content}\nSource: {url}")
        if not parts:
            return None
        return "🔍 **Web Search (Tavily)**\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"Tavily failed: {e}")
        return None


def search_ddgs(query: str, max_results: int = 5) -> Optional[str]:
    """FREE DuckDuckGo text search via ddgs / duckduckgo_search."""
    if not _DDGS:
        return None
    try:
        rows: List[Dict[str, Any]] = []
        with _DDGS() as ddgs:
            # text search
            for r in ddgs.text(query, max_results=max_results):
                rows.append(r)
        if not rows:
            return None
        parts = []
        for i, r in enumerate(rows, 1):
            title = r.get("title") or r.get("heading") or "Result"
            body = r.get("body") or r.get("snippet") or r.get("description") or ""
            href = r.get("href") or r.get("link") or r.get("url") or ""
            parts.append(f"{i}. **{title}**\n{body[:500]}\nSource: {href}")
        return "🔍 **Web Search (DuckDuckGo / free)**\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"ddgs failed: {e}")
        return None


def search_duckduckgo_ia(query: str, max_results: int = 5) -> Optional[str]:
    """FREE Instant Answer API (often sparse, but no key)."""
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        parts: List[str] = []
        if data.get("AbstractText"):
            parts.append(
                f"**{data.get('Heading') or query}**\n{data['AbstractText']}\n"
                f"Source: {data.get('AbstractURL') or data.get('AbstractSource') or 'DuckDuckGo'}"
            )
        for t in (data.get("RelatedTopics") or [])[:max_results]:
            if isinstance(t, dict) and t.get("Text"):
                parts.append(f"- {t['Text']}" + (f"\n  {t.get('FirstURL','')}" if t.get("FirstURL") else ""))
            elif isinstance(t, dict) and t.get("Topics"):
                for sub in t["Topics"][:2]:
                    if sub.get("Text"):
                        parts.append(f"- {sub['Text']}")
        if not parts:
            return None
        return "🔍 **DuckDuckGo Instant Answer (free)**\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"DuckDuckGo IA failed: {e}")
        return None


def search_wikipedia(query: str, max_results: int = 3) -> Optional[str]:
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": max_results,
        }
        resp = requests.get(search_url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        results = (resp.json().get("query") or {}).get("search") or []
        if not results:
            return None
        parts = []
        for r in results:
            title = r.get("title", "")
            snippet = (
                (r.get("snippet") or "")
                .replace('<span class="searchmatch">', "")
                .replace("</span>", "")
            )
            parts.append(
                f"**{title}**\n{snippet}\n"
                f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            )
        return "📚 **Wikipedia (free)**\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"Wikipedia failed: {e}")
        return None


def search_open_meteo_weather(query: str) -> Optional[str]:
    """FREE weather via Open-Meteo (no key) when query looks like weather + place."""
    q = query.lower()
    if not any(w in q for w in ("weather", "temperature", "forecast", "rain", "humidity")):
        return None
    # strip filler words to get location hint
    loc = re.sub(
        r"\b(what|is|the|current|today|now|weather|temperature|forecast|please|tell|me|like|how)\b",
        " ",
        q,
        flags=re.I,
    )
    loc = re.sub(r"\s+", " ", loc).strip(" ?.,")
    # Prefer "Name + district/city + country" patterns
    if len(loc) < 3:
        loc = query
    # Try progressive geocode candidates
    candidates = [loc]
    # e.g. "langay village of gujrat pakistan" → also try "Langay Gujrat Pakistan", "Gujrat Pakistan"
    cleaned = re.sub(r"\b(village|city|town|district|tehsil|of)\b", " ", loc, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned and cleaned not in candidates:
        candidates.append(cleaned)
    parts = [p for p in re.split(r"[,/]|\s+", cleaned) if len(p) > 2]
    if len(parts) >= 2:
        candidates.append(" ".join(parts[-2:]))  # last two tokens: Gujrat Pakistan
    try:
        place = None
        for cand in (candidates if "candidates" in dir() else [loc]):
            geo = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": cand, "count": 3, "language": "en", "format": "json"},
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            if geo.status_code != 200:
                continue
            results = (geo.json() or {}).get("results") or []
            if results:
                # Prefer Pakistan if mentioned
                if "pakistan" in q:
                    pk = [r for r in results if (r.get("country") or "").lower() == "pakistan"]
                    place = pk[0] if pk else results[0]
                else:
                    place = results[0]
                break
        if not place:
            return None
        lat, lon = place["latitude"], place["longitude"]
        name = place.get("name", loc)
        country = place.get("country", "")
        admin = place.get("admin1") or ""
        wx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        wx.raise_for_status()
        cur = (wx.json() or {}).get("current") or {}
        code = cur.get("weather_code")
        code_map = {
            0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 61: "Rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Snow", 80: "Rain showers", 95: "Thunderstorm",
        }
        desc = code_map.get(code, f"Code {code}")
        label = ", ".join(x for x in (name, admin, country) if x)
        return (
            f"🌤️ **Weather (Open-Meteo / free)**\n\n"
            f"**Location:** {label}\n"
            f"**Temperature:** {cur.get('temperature_2m')} °C\n"
            f"**Humidity:** {cur.get('relative_humidity_2m')}%\n"
            f"**Wind:** {cur.get('wind_speed_10m')} km/h\n"
            f"**Conditions:** {desc}\n"
            f"_Source: open-meteo.com — no API key required_"
        )
    except Exception as e:
        logger.warning(f"Open-Meteo failed: {e}")
        return None


# ==========================================================
# QUERY NORMALIZE + ORCHESTRATOR
# ==========================================================
def normalize_search_query(query: str) -> str:
    q = (query or "").strip()
    # light expansions
    replacements = {
        r"\bpm\b": "prime minister",
        r"\bpk\b": "Pakistan",
        r"\busa\b": "United States",
        r"\buk\b": "United Kingdom",
    }
    for pat, rep in replacements.items():
        q = re.sub(pat, rep, q, flags=re.I)
    return q


def search_web(query: str, max_results: int = 5, use_cache: bool = True) -> str:
    if not query or not query.strip():
        return "[Please provide a more specific search query.]"

    query = normalize_search_query(query)
    logger.info(f"Normalized search query: {query}")

    if use_cache:
        cached = search_cache.get(query)
        if cached:
            logger.info("♻️ Search cache hit")
            return cached + "\n\n_(cached)_"

    logger.info(f"🔍 Multi-engine search: {query}")
    ttl = get_cache_ttl(query)

    # Weather shortcut first for weather queries
    weather = search_open_meteo_weather(query)
    if weather:
        search_cache.set(query, weather, ttl=ttl)
        return weather

    engines = [
        ("Tavily", lambda: search_tavily(query, max_results)),
        ("ddgs", lambda: search_ddgs(query, max_results)),
        ("DuckDuckGo IA", lambda: search_duckduckgo_ia(query, max_results)),
        ("Wikipedia", lambda: search_wikipedia(query, max_results)),
    ]

    errors: List[str] = []
    for name, fn in engines:
        try:
            results = fn()
            if results and len(results.strip()) > 40:
                logger.info(f"   ✅ {name} succeeded")
                search_cache.set(query, results, ttl=ttl)
                return results
            logger.info(f"   ⏭️ {name} empty")
        except Exception as e:
            logger.warning(f"   ❌ {name}: {e}")
            errors.append(f"{name}: {e}")

    # Last-ditch: try weather even if keywords weak
    if "village" in query.lower() or "district" in query.lower():
        weather = search_open_meteo_weather("weather " + query)
        if weather:
            search_cache.set(query, weather, ttl=ttl)
            return weather

    logger.warning("   ❌ All search engines failed.")
    tip = (
        "No live results. Free engines need `pip install -U ddgs`. "
        "Optional: set TAVILY_API_KEY for higher quality."
    )
    if errors:
        tip += " Errors: " + "; ".join(errors[:3])
    return f"[Search unavailable] {tip}"


def is_search_needed(message: str) -> bool:
    if not message:
        return False
    msg = message.lower().strip()
    doc_cmds = ("summarize", "explain", "translate", "rewrite", "extract", "read", "mark", "grade")
    if any(msg.startswith(c) for c in doc_cmds) and "http" not in msg:
        return False
    triggers = [
        "news", "latest", "today", "current", "recent", "breaking",
        "this year", "this month", "this week", "happening", "trending",
        "stock", "weather", "price", "cost", "forecast", "temperature",
        "2024", "2025", "2026", "2027", "2028", "2029", "2030",
        "real-time", "live", "ongoing", "look up", "search the web",
        "search online", "who is the pm", "who is pm",
    ]
    if any(x in msg for x in (" pakistan", "pk ")) and any(
        x in msg for x in ("official", "pm", "prime", "president", "minister", "gov", "weather")
    ):
        return True
    return any(t in msg for t in triggers)


def get_current_info() -> str:
    """Server-local + explicit Pakistan Standard Time (UTC+5) for PK users."""
    from datetime import timezone, timedelta
    utc_now = datetime.now(timezone.utc)
    pkt = timezone(timedelta(hours=5))
    pkt_now = utc_now.astimezone(pkt)
    return (
        f"UTC: {utc_now.strftime('%A, %B %d, %Y %H:%M')} | "
        f"Pakistan (PKT, UTC+5): {pkt_now.strftime('%A, %B %d, %Y %I:%M %p')}"
    )


def auto_search_context(message: str, extra_context: str = "") -> Optional[str]:
    if not message or not message.strip():
        return None
    triggers = [
        "latest", "current", "today", "now", "recent", "news", "update",
        "2024", "2025", "2026", "2027", "2028", "2029", "2030",
        "real-time", "live", "happening", "trending",
        "weather", "stock", "price", "score", "forecast", "temperature",
    ]
    msg = message.lower()
    if any(t in msg for t in triggers):
        logger.info("Auto-detected search need, performing web search...")
        return search_web(message, max_results=5, use_cache=True)
    return None


def clear_search_cache():
    search_cache.clear()
    return "Search cache cleared"


def get_search_stats() -> Dict[str, Any]:
    """Shape expected by frontend/admin/search-dashboard.html."""
    now = time.time()
    recent = []
    try:
        items = []
        for k, item in (search_cache.mem or {}).items():
            if not isinstance(item, dict):
                continue
            data = item.get("data") or ""
            ts = float(item.get("ts") or 0)
            ttl = float(item.get("ttl") or CACHE_DURATION)
            age = max(0, now - ts)
            is_stale = age > ttl
            # Try to recover original query from stored data header if present
            query = item.get("query") or k
            if isinstance(data, str) and data.startswith("QUERY:"):
                query = data.split("\n", 1)[0].replace("QUERY:", "", 1).strip() or k
            # Prefer short key display
            display_q = query if len(str(query)) < 80 else (str(query)[:77] + "...")
            # age human
            if age < 60:
                age_h = f"{int(age)}s"
            elif age < 3600:
                age_h = f"{int(age // 60)}m"
            else:
                age_h = f"{int(age // 3600)}h"
            items.append({
                "query": display_q,
                "age_seconds": int(age),
                "age_human": age_h,
                "result_length": len(data) if isinstance(data, str) else 0,
                "is_stale": is_stale,
                "ts": ts,
            })
        items.sort(key=lambda x: x.get("ts", 0), reverse=True)
        recent = items[:30]
    except Exception as e:
        logger.warning(f"search stats recent: {e}")

    return {
        "status": "ok",
        "total_entries": len(search_cache.mem) if not USE_REDIS else 0,
        "max_cache_size": MAX_CACHE_SIZE,
        "cache_duration_seconds": CACHE_DURATION,
        "recent_queries": recent,
        "engines": available_engines(),
        "tavily": bool(tavily),
        "redis": bool(USE_REDIS),
    }


__all__ = [
    "search_web",
    "is_search_needed",
    "auto_search_context",
    "get_current_info",
    "clear_search_cache",
    "get_search_stats",
    "available_engines",
]

logger.info(
    f"👁️ Vision AI Web Search v2.1 — engines: {', '.join(available_engines())}"
)
