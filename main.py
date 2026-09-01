"""
Vision AI v3.5.1 - Production-Grade Multi-Modal AI Assistant
============================================================
Enterprise-ready FastAPI application with:
- Multi-provider AI routing (Gemini, DeepSeek, Groq, OpenRouter)
- Real-time Agentic RAG with document processing
- Diagram & image generation
- Self-learning optimizer
- YouTube tools
- JWT + OAuth2 authentication
- Rate limiting & security middleware

Version: 3.5.1
Author: Vision AI Team
License: MIT
"""

import os
import sys
import io
import time
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from dotenv import load_dotenv
from services.security import require_admin
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from services.rate_limit import limiter as shared_limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field

# ==========================================================
# PATH RESOLUTION (Works from any directory)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent
APP_VERSION = (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip() if (BASE_DIR / "VERSION").exists() else "5.4.0"

# ==========================================================
# WINDOWS CONSOLE ENCODING FIX
# ==========================================================
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ==========================================================
# ENVIRONMENT VARIABLES
# ==========================================================
load_dotenv(BASE_DIR / ".env")

# ==========================================================
# LOGGING CONFIGURATION
# ==========================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"

# Create logs directory BEFORE configuring logging
(BASE_DIR / "logs").mkdir(exist_ok=True)

handlers = [
    logging.FileHandler(str(BASE_DIR / "logs" / "app.log"), encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=handlers
)
logger = logging.getLogger("vision-ai")

def _worker_health_summary() -> dict:
    """Best-effort Colab/Kaggle worker status for /health."""
    try:
        from services.colab_worker import health as wh, is_enabled
        h = wh() if callable(wh) else {}
        return {
            "enabled": bool(is_enabled()) if callable(is_enabled) else False,
            "detail": h if isinstance(h, dict) else {"raw": str(h)[:200]},
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)[:120]}


# Ensure all handlers use UTF-8
for handler in logging.root.handlers:
    if isinstance(handler, logging.FileHandler) and not handler.encoding:
        handler.encoding = "utf-8"
    if isinstance(handler, logging.StreamHandler):
        handler.encoding = "utf-8"

# ==========================================================
# CONFIGURATION MODELS
# ==========================================================
class AppConfig:
    """Centralized application configuration."""
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "5050"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALLOWED_HOSTS: List[str] = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
    # Full origins for CORS (e.g. https://vision-ai.example.com) — separate from hostnames
    CORS_ORIGINS: List[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
    ]

    # Session
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", os.getenv("SECRET_KEY", "change-me"))

    # AI Providers
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")

    # Search
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")

    # Image Generation
    HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN")

    # OAuth
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5050/auth/google/callback")

    # Rate Limiting
    RATE_LIMIT_SEARCH: str = os.getenv("RATE_LIMIT_SEARCH", "20/minute")
    RATE_LIMIT_DOWNLOAD: str = os.getenv("RATE_LIMIT_DOWNLOAD", "10/minute")
    RATE_LIMIT_CHAT: str = os.getenv("RATE_LIMIT_CHAT", "60/minute")

    # Paths
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    CACHE_DIR: Path = BASE_DIR / "cache"
    LOG_DIR: Path = BASE_DIR / "logs"
    DOWNLOAD_DIR: Path = BASE_DIR / "downloads"
    FRONTEND_DIR: Path = BASE_DIR / "frontend"

    @classmethod
    def validate(cls) -> List[str]:
        """Validate critical configuration. Raises only on truly fatal misconfig."""
        warnings: List[str] = []
        errors: List[str] = []
        weak_secrets = {
            "change-me-in-production",
            "your-secret-key-here",
            "change-me",
            "secret",
            "changeme",
            "",
        }
        on_railway = bool(
            os.getenv("RAILWAY_ENVIRONMENT")
            or os.getenv("RAILWAY_PUBLIC_DOMAIN")
            or os.getenv("RAILWAY_PROJECT_ID")
        )
        if cls.SECRET_KEY in weak_secrets or len(cls.SECRET_KEY) < 32:
            msg = (
                "SECRET_KEY is missing, weak, or default. "
                "Set a long random SECRET_KEY (32+ chars) in Railway Variables."
            )
            if not cls.DEBUG:
                errors.append(msg)
            else:
                warnings.append("WARNING: " + msg)
        if not any([cls.GOOGLE_API_KEY, cls.GROQ_API_KEY, cls.DEEPSEEK_API_KEY, cls.OPENROUTER_API_KEY]):
            warnings.append("WARNING: No AI provider API keys configured. Chat will not work.")
        # ALLOWED_HOSTS: on Railway, * is common until custom domain is set — warn, do not crash
        if not cls.DEBUG and (not cls.ALLOWED_HOSTS or cls.ALLOWED_HOSTS == ["*"]):
            if on_railway:
                warnings.append(
                    "ALLOWED_HOSTS is * — OK on Railway. "
                    "For a custom domain set ALLOWED_HOSTS=your.domain,your-app.up.railway.app"
                )
            else:
                errors.append(
                    "ALLOWED_HOSTS must be explicitly configured in production (do not use *)."
                )
        if errors:
            for e in errors:
                logger.error(e)
            raise RuntimeError("Fatal configuration error: " + "; ".join(errors))
        return warnings

# ==========================================================
# LIFESPAN MANAGEMENT
# ==========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from services.agent_orchestrator import agent_orchestrator
        agent_orchestrator.start_agents()
    except Exception as _agent_err:
        logging.getLogger("vision-ai").warning("Agent orchestrator not started: %s", _agent_err)

    """Application lifespan: startup and shutdown events."""
    global_start_time = time.time()
    app.state.start_time = global_start_time

    # Create directories
    for dir_path in [
        AppConfig.UPLOAD_DIR, 
        AppConfig.CACHE_DIR, 
        AppConfig.LOG_DIR, 
        AppConfig.DOWNLOAD_DIR
    ]:
        dir_path.mkdir(exist_ok=True, parents=True)

    # Validate config (must not take down healthcheck with opaque failures)
    try:
        warnings = AppConfig.validate()
        for warning in warnings:
            logger.warning(warning)
    except RuntimeError as cfg_err:
        logger.error("CONFIG ERROR: %s", cfg_err)
        # Re-raise so operator sees it in logs — fix SECRET_KEY in Railway Variables
        raise

    # Initialize optimizer
    try:
        from services.self_optimizer import optimizer
        app.state.optimizer = optimizer
        health = optimizer.get_health_status()

        logger.info("=" * 70)
        logger.info(f"Vision AI v{APP_VERSION} Starting...")
        logger.info("=" * 70)
        logger.info(f"Version: {APP_VERSION} (Production Ready)")
        logger.info(f"Debug Mode: {AppConfig.DEBUG}")
        logger.info(f"Uploads: {AppConfig.UPLOAD_DIR.absolute()}")
        logger.info(f"Cache: {AppConfig.CACHE_DIR.absolute()}")
        logger.info(f"Logs: {AppConfig.LOG_DIR.absolute()}")
        logger.info(f"Downloads: {AppConfig.DOWNLOAD_DIR.absolute()}")
        logger.info("-" * 70)
        logger.info("AI Providers:")
        logger.info(f"  Gemini:    {'Active (Primary)' if AppConfig.GOOGLE_API_KEY else 'Not Configured'}")
        logger.info(f"  DeepSeek:  {'Active' if AppConfig.DEEPSEEK_API_KEY else 'Not Configured'}")
        logger.info(f"  Groq:      {'Active (Backup)' if AppConfig.GROQ_API_KEY else 'Not Configured'}")
        logger.info(f"  OpenRouter: {'Active (Fallback)' if AppConfig.OPENROUTER_API_KEY else 'Not Configured'}")
        logger.info("-" * 70)
        logger.info("Services:")
        logger.info(f"  Tavily Search: {'Active' if AppConfig.TAVILY_API_KEY else 'Not Configured'}")
        logger.info(f"  HF Image Gen:  {'Active' if AppConfig.HF_TOKEN else 'Not Configured'}")
        logger.info(f"  Google OAuth:  {'Active' if (AppConfig.GOOGLE_CLIENT_ID and AppConfig.GOOGLE_CLIENT_SECRET) else 'Not Configured'}")
        logger.info("-" * 70)
        logger.info("Self-Learning System:")
        logger.info(f"  Status: {'Active' if health.get('learning_database') == 'active' else 'New Session'}")
        logger.info(f"  Total Interactions: {health.get('total_interactions', 0)}")
        logger.info(f"  Knowledge Graph: {health.get('knowledge_graph_size', 0)} concepts")
        if hasattr(optimizer, '_get_evolution_stage'):
            logger.info(f"  Evolution Stage: {optimizer._get_evolution_stage()}")
        logger.info("-" * 70)
        logger.info(f"Startup completed in {time.time() - global_start_time:.2f}s")
        logger.info("=" * 70)

    except ImportError as e:
        logger.warning(f"Self-learning system not available: {e}")
        app.state.optimizer = None

    yield

    # ==========================================================
    # ✅ SHUTDOWN SAFETY
    # ==========================================================
    try:
        if hasattr(app.state, "optimizer") and app.state.optimizer is not None:
            report = app.state.optimizer.get_session_report()
            logger.info("=" * 70)
            logger.info("SESSION SUMMARY")
            logger.info("=" * 70)
            logger.info(f"Duration: {report.get('session_duration', 'N/A')}")
            logger.info(f"Diagrams Requested: {report.get('diagrams_requested', 0)}")
            logger.info(f"Diagrams Generated: {report.get('diagrams_generated', 0)}")
            logger.info(f"Success Rate: {report.get('success_rate', 'N/A')}")
            logger.info(f"Providers Used: {report.get('providers_used', 'None')}")
            logger.info(f"Subjects Covered: {', '.join(report.get('subjects_covered', [])) or 'None'}")
            logger.info(f"Failed Attempts: {report.get('failed_attempts', 0)}")
            logger.info(f"Learning Events: {report.get('learning_events', 0)}")
            suggestions = report.get('suggestions', [])
            if suggestions:
                logger.info("Improvement Suggestions:")
                for s in suggestions[:5]:
                    logger.info(f"  - {s}")
            logger.info("=" * 70)
        else:
            logger.info("Optimizer not available — skipping session report.")
    except Exception as e:
        logger.debug(f"Could not generate session report: {e}")

    logger.info("Vision AI Shutting Down...")

# ==========================================================
# FASTAPI APPLICATION
# ==========================================================
# OpenAPI: on in DEBUG, or when ENABLE_DOCS=1 (recommended for your own ops only)
_enable_docs = bool(getattr(AppConfig, "DEBUG", False)) or (
    (os.getenv("ENABLE_DOCS", "0") or "0").strip().lower() in ("1", "true", "yes")
)
app = FastAPI(
    title="Vision AI",
    description="Production-grade multi-modal AI assistant with document processing, diagram generation, and multi-model support.",
    version=APP_VERSION,
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    lifespan=lifespan,
)

# ==========================================================
# RATE LIMITER
# ==========================================================
limiter = shared_limiter
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# ==========================================================
# SECURITY MIDDLEWARE
# ==========================================================

# Max request body (55 MB) — protects upload endpoints
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", str(55 * 1024 * 1024)))

@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "Payload too large", "max_bytes": MAX_BODY_BYTES},
        )
    return await call_next(request)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses + long-cache static assets."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=(self)"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["X-Vision-AI-Version"] = APP_VERSION
    response.headers["X-App-Version"] = APP_VERSION
    # Fast repeat visits: immutable cache for versioned static files
    path = request.url.path or ""
    if path.startswith("/frontend/static/") and any(
        path.endswith(ext) for ext in (".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".woff2", ".ico")
    ):
        response.headers["Cache-Control"] = "public, max-age=604800, immutable"
    elif path.endswith((".html", "/")) or path in ("/", "/index.html"):
        response.headers["Cache-Control"] = "no-cache"
    return response

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID for request tracking and logging."""
    correlation_id = request.headers.get("X-Correlation-ID", f"req_{int(time.time())}_{os.urandom(4).hex()}")
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

@app.middleware("http")
async def validate_content_type(request: Request, call_next):
    """Validate content type for POST requests."""
    if request.method == "POST" and request.headers.get("content-type"):
        content_type = request.headers["content-type"].lower()
        valid_types = ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]
        if not any(vt in content_type for vt in valid_types):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid content type",
                    "detail": f"Received: {content_type}",
                    "allowed": valid_types
                }
            )
    return await call_next(request)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Duration: {duration:.3f}s | "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    return response

# ==========================================================
# BUILT-IN MIDDLEWARE
# ==========================================================
app.add_middleware(
    SessionMiddleware,
    secret_key=AppConfig.SESSION_SECRET,
    max_age=86400,  # 24h — OAuth state must survive Google redirect
    same_site="lax",  # required for top-level OAuth return
    https_only=not AppConfig.DEBUG,  # True on Railway (HTTPS)
)

# When allow_credentials=True, origins cannot be "*". Prefer CORS_ORIGINS env (full origins).
# Fallback: derive https:// from ALLOWED_HOSTS hostnames in production.
# Colab may call register/heartbeat from browser tools; Python requests ignore CORS.
if AppConfig.DEBUG:
    _cors_origins = ["*"]
elif AppConfig.CORS_ORIGINS:
    _cors_origins = list(AppConfig.CORS_ORIGINS)
else:
    _cors_origins = []
    for h in AppConfig.ALLOWED_HOSTS:
        if h and h != "*":
            if h.startswith("http://") or h.startswith("https://"):
                _cors_origins.append(h)
            else:
                _cors_origins.append(f"https://{h}")
                _cors_origins.append(f"http://{h}")
if not _cors_origins:
    _cors_origins = ["http://localhost:5050", "http://127.0.0.1:5050"]
for _extra in ("https://colab.research.google.com",):
    if _extra not in _cors_origins and "*" not in _cors_origins:
        _cors_origins.append(_extra)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# TrustedHostMiddleware rejects requests if host not in list; "*" is valid for open deploy
_trusted = AppConfig.ALLOWED_HOSTS if AppConfig.ALLOWED_HOSTS != ["*"] else ["*"]
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=_trusted,
)

# ==========================================================
# ROUTER IMPORTS - ISOLATED LOADING (FIXES LOGIN 404)
# ==========================================================
from fastapi import APIRouter

# 🟢 FIX: Add middleware method to APIRouter for compatibility
def _router_middleware(self, *args, **kwargs):
    """Dummy middleware method for APIRouter compatibility."""
    def decorator(func):
        return func
    return decorator

# 🟢 FIX: Add exception_handler method to APIRouter for compatibility
def _router_exception_handler(self, *args, **kwargs):
    """Dummy exception_handler method for APIRouter compatibility."""
    def decorator(func):
        return func
    return decorator

# Patch APIRouter to have middleware and exception_handler methods
APIRouter.middleware = _router_middleware
APIRouter.exception_handler = _router_exception_handler

main_router = APIRouter()
_loaded = []
_failed = []

def _load_router(name: str, import_fn):
    try:
        r = import_fn()
        main_router.include_router(r)
        _loaded.append(name)
    except Exception as e:
        _failed.append((name, str(e)))
        logger.error(f"❌ Failed to load '{name}' router: {e}")

# Load routers (chat mounted with prefix so POST /chat/send always exists)
_load_router("upload", lambda: __import__("routes.upload", fromlist=["router"]).router)
_load_router("upgrade", lambda: __import__("routes.upgrade", fromlist=["router"]).router)

if _loaded:
    logger.info(f"✅ Routers loaded: {', '.join(_loaded)}")
if _failed:
    logger.error(f"⚠️ Routers NOT loaded: {', '.join(n for n, _ in _failed)} — check errors above")

app.include_router(main_router)

# Chat: explicit dual mount — /chat/send and /api/chat/send
try:
    from routes.chat import router as chat_router
    app.include_router(chat_router, prefix="/chat", tags=["Chat"])
    app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
    if "chat" not in _loaded:
        _loaded.append("chat")
    logger.info("✅ Chat router mounted: POST /chat/send /api/chat/send")
except Exception as _ce:
    _failed.append(("chat", str(_ce)))
    logger.exception("❌ CRITICAL: Chat router failed to load: %s", _ce)

# Always-on ping so we can verify POST works even if chat module is broken
@app.post("/chat/ping")
@app.get("/chat/ping")
async def chat_ping():
    return {"ok": True, "version": APP_VERSION, "post_chat_send": "POST /chat/send"}

# Absolute POST handlers bound via add_api_route (cannot be skipped by import side-effects)
async def _bind_chat_send():
    pass

try:
    from routes.login import router as login_router
    app.include_router(login_router)
    logger.info("Login router mounted (/auth/me, /auth/google, ...)")
except Exception as _le:
    logger.error("Login router mount failed: %s", _le)

try:
    from routes import studio as studio_routes
    app.include_router(studio_routes.router)
    logger.info("✅ Studio API mounted at /api/studio")
except Exception as _st_err:
    logging.getLogger("vision-ai").warning("studio router skipped: %s", _st_err)

try:
    from routes import models as models_routes
    app.include_router(models_routes.router)
except Exception as _me:
    logger.error("Models router mount failed: %s", _me)

# RAG Engine + routing profiles
try:
    from routes.rag_engine import router as rag_engine_router
    app.include_router(rag_engine_router)
    logger.info("✅ RAG Engine mounted at /api/rag")
    try:
        from services.rag_engine_core import health_check as _rag_health
        _rh = _rag_health()
        logger.info("RAG health: ok=%s chroma=%s", _rh.get("ok"), (_rh.get("chroma") or {}).get("available"))
    except Exception as _rhe:
        logger.warning("RAG health check: %s", _rhe)

except Exception as _re:
    logger.error("RAG Engine mount failed: %s", _re)

try:
    from services.routing_profiles import list_profiles
    @app.get("/api/routing/profiles")
    async def api_routing_profiles():
        return {"ok": True, "profiles": list_profiles()}
    logger.info("✅ Routing profiles at /api/routing/profiles")
    @app.get("/api/routing/analytics")
    async def api_routing_analytics():
        from services.routing_analytics import snapshot
        return snapshot()


    logger.info("✅ Models API at /api/models")
except Exception as _me:
    logging.getLogger("vision-ai").warning("models router: %s", _me)


# ==========================================================
# DIRECT AUTH ROUTES (failsafe — guarantee POST /auth/login exists)
# ==========================================================
@app.post("/auth/token")
@app.post("/auth/login")
@app.post("/api/auth/login")
async def direct_auth_login(request: Request):
    """Hard-wired login so SPA never gets 405 if router mount fails."""
    try:
        from routes.login import authenticate_user, create_access_token, create_refresh_token
        from routes.login import ACCESS_TOKEN_EXPIRE_MINUTES, TokenResponse
    except Exception as e:
        logger.exception("auth import failed")
        return JSONResponse(status_code=500, content={"detail": f"Auth module error: {e}"})

    username = ""
    password = ""
    ctype = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in ctype:
            body = await request.json()
            username = str((body or {}).get("username") or "").strip()
            password = str((body or {}).get("password") or "")
        else:
            form = await request.form()
            username = str(form.get("username") or "").strip()
            password = str(form.get("password") or "")
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Could not parse login body"})

    if not username or not password:
        return JSONResponse(status_code=422, content={"detail": "Username and password are required"})

    user = authenticate_user(username, password)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"detail": "Incorrect username or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["username"]})
    refresh_token = create_refresh_token(data={"sub": user["username"]})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "username": user["username"],
    }


@app.get("/auth/health")
@app.get("/api/auth/health")
async def direct_auth_health():
    return {"status": "ok", "login": "POST /auth/login", "version": APP_VERSION}



# Needed for the admin-only search-dashboard routes below. Matches the
# same top-level import already used in routes/chat.py and
# routes/upgrade.py. If routes.login failed to load above, essentially
# nothing in this app works anyway (chat and upgrade already import this
# the same way), so this doesn't introduce a new failure mode.
from routes.login import get_current_active_user

skills_routes = None
try:
    from routes import skills as skills_routes
except Exception as _sk_err:
    logging.getLogger('vision-ai').warning('skills router skipped: %s', _sk_err)

try:
    from routes import workers as workers_routes
    app.include_router(workers_routes.router)
except Exception as _werr:
    logging.getLogger('vision-ai').warning('workers router skipped: %s', _werr)

try:
    from routes import agent as agent_routes
    app.include_router(agent_routes.router)
except Exception as _aerr:
    logging.getLogger('vision-ai').warning('agent router skipped: %s', _aerr)


# Health check to debug router issues
@app.get("/health/routers", tags=["System"])
async def router_health():
    return {"loaded": _loaded, "failed": [{"router": n, "error": e} for n, e in _failed]}

@app.get("/health/routes", tags=["System"])
async def list_routes():
    """Debug: list registered methods+paths (confirm POST /chat/send exists)."""
    out = []
    for r in app.routes:
        methods = sorted(getattr(r, "methods", []) or [])
        path = getattr(r, "path", str(r))
        if methods:
            out.append({"path": path, "methods": methods})
    chat_posts = [x for x in out if "chat" in x["path"] and "POST" in x["methods"]]
    return {"version": APP_VERSION, "chat_post_routes": chat_posts, "count": len(out), "routes": out[:80]}


# ==========================================================
# HEALTH CHECK
# ==========================================================
@app.get("/health", tags=["System"])
async def health_check():
    """Lightweight public health check (Railway / load balancers)."""
    return {"status": "healthy", "version": APP_VERSION}

@app.get("/health/detailed", tags=["System"])
async def health_check_detailed():
    """Detailed health check — prefer restricting this in production (admin-only)."""
    from services.llm import GEMINI_AVAILABLE, GROQ_AVAILABLE

    uptime_seconds = int(time.time() - getattr(app.state, "start_time", time.time()))
    uptime_human = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m"

    health_data = {
        "status": "healthy",
        "uptime": uptime_human,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": APP_VERSION,
        "environment": {
            "debug": AppConfig.DEBUG,
            "python_version": sys.version.split()[0],
        },
        "services": {
            "gemini": bool(AppConfig.GOOGLE_API_KEY),
            "groq": bool(AppConfig.GROQ_API_KEY),
            "deepseek": bool(AppConfig.DEEPSEEK_API_KEY),
            "openrouter": bool(AppConfig.OPENROUTER_API_KEY),
            "tavily": bool(AppConfig.TAVILY_API_KEY),
            "huggingface": bool(AppConfig.HF_TOKEN),
            "google_oauth": bool(AppConfig.GOOGLE_CLIENT_ID and AppConfig.GOOGLE_CLIENT_SECRET),
        },
        "colab_workers": _worker_health_summary(),
        "middlewares": [
            "CORS", "GZip", "TrustedHosts", "RateLimiting", "SecurityHeaders",
            "CorrelationID", "ContentValidation", "RequestLogging", "SessionManagement"
        ],
    }
    if hasattr(app.state, "optimizer") and app.state.optimizer:
        health_data["optimizer"] = app.state.optimizer.get_health_status()
    return health_data

# ==========================================================
# STATIC FILES & FRONTEND ROUTING
# ==========================================================

# 1. Mount the entire frontend folder so CSS/JS/Images load properly
app.mount("/frontend", StaticFiles(directory=str(AppConfig.FRONTEND_DIR)), name="frontend")
# /downloads public mount REMOVED — use /upload/downloads/{filename} only

@app.get("/favicon.ico")
@app.get("/favicon.png")
async def favicon():
    fav_dir = AppConfig.FRONTEND_DIR / "static" / "favicon"
    for name, media in (("favicon.ico", "image/x-icon"), ("favicon.png", "image/png")):
        path = fav_dir / name
        if path.exists() and path.is_file():
            return FileResponse(str(path), media_type=media)
    return JSONResponse(content={"detail": "Favicon not found"}, status_code=404)

# 7. Search Cache Dashboard (HTML) + JSON API
def _require_admin(current_user: dict) -> dict:
    """Same role check already used in routes/upgrade.py."""
    require_admin(current_user)
    return current_user

@app.get("/admin/search")
@app.get("/admin/search/")
async def serve_search_dashboard():
    """Serve the search cache dashboard HTML page.

    Auth is enforced client-side (Bearer token from localStorage) and on
    the JSON APIs below. Browser navigation cannot send Authorization
    headers, so this HTML route must stay public or the page never loads.
    """
    dashboard_path = AppConfig.FRONTEND_DIR / "admin" / "search-dashboard.html"
    if dashboard_path.exists() and dashboard_path.is_file():
        return FileResponse(str(dashboard_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Search dashboard not found")


@app.get("/admin/search/stats")
async def search_stats_api(current_user: dict = Depends(get_current_active_user)):
    """JSON stats for the search-cache dashboard. Previously had no auth at
    all -- reachable by anyone who knew the URL, no login required."""
    _require_admin(current_user)
    try:
        from services.search import get_search_stats
        return get_search_stats()
    except Exception as e:
        logger.error(f"Search stats error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e), "total_entries": 0, "max_cache_size": 0, "cache_duration_seconds": 0, "recent_queries": []},
        )


@app.post("/admin/search/clear")
async def search_clear_api(current_user: dict = Depends(get_current_active_user)):
    """Clear the search cache. Same admin gate as the other search routes."""
    _require_admin(current_user)
    try:
        from services.search import clear_search_cache
        clear_search_cache()
        return {"status": "ok", "message": "Search cache cleared"}
    except Exception as e:
        logger.error(f"Search clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 8. Admin payment verification dashboard (manual Easypaisa/bank reviews)
@app.get("/admin/payments")
@app.get("/admin/payments/")
async def serve_payments_dashboard():
    """Admin payment verification UI (HTML).

    Same pattern as /admin/search: page is public HTML; /upgrade/admin/*
    JSON APIs enforce admin JWT. Client redirects to login if no token.
    """
    path = AppConfig.FRONTEND_DIR / "admin" / "payments.html"
    if path.exists() and path.is_file():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Payments dashboard not found")

# ==========================================================
# CATCH-ALL — serve real frontend HTML files; only fall back to index for unknown paths
# ==========================================================
@app.get("/")
@app.get("/index.html")
async def page_home():
    path = AppConfig.FRONTEND_DIR / "index.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="index.html missing")

@app.get("/login")
@app.get("/login.html")
async def page_login():
    path = AppConfig.FRONTEND_DIR / "login.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="login.html missing")

@app.get("/settings")
@app.get("/settings.html")
async def page_settings():
    path = AppConfig.FRONTEND_DIR / "settings.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="settings.html missing")

@app.get("/upgrade")
@app.get("/upgrade.html")
async def page_upgrade():
    path = AppConfig.FRONTEND_DIR / "upgrade.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="upgrade.html missing")

@app.get("/boost")
@app.get("/boost.html")
async def page_boost():
    path = AppConfig.FRONTEND_DIR / "boost.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="boost.html missing")

@app.get("/skills")
@app.get("/skills.html")
async def page_skills():
    path = AppConfig.FRONTEND_DIR / "skills.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="skills.html missing")

@app.get("/usage")
@app.get("/usage.html")
async def page_usage():
    path = AppConfig.FRONTEND_DIR / "usage.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="usage.html missing")

@app.get("/studio")
@app.get("/studio.html")
async def page_studio():
    path = AppConfig.FRONTEND_DIR / "studio.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="studio.html missing")

@app.get("/versions")
@app.get("/versions.html")
async def page_versions():

    path = AppConfig.FRONTEND_DIR / "versions.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    raise HTTPException(status_code=404, detail="versions.html missing")


@app.api_route("/{path:path}", methods=["POST", "PUT", "DELETE", "PATCH"])
async def catch_all_api_methods(path: str):
    """Prevent 405 from GET-only SPA catch-all when an API route is missing."""
    raise HTTPException(status_code=404, detail=f"No endpoint for /{path} (check /health/routes)")

@app.get("/{path:path}")
async def catch_all(path: str):
    """Serve real static HTML when present; API prefixes 404; else index."""
    if path.startswith(("api/", "auth/", "upgrade/", "upload/", "admin/", "chat/", "health", "worker")):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    # Prevent path traversal
    safe = Path(path).name if path else ""
    # Allow nested admin paths already handled above; for generic files:
    candidate = (AppConfig.FRONTEND_DIR / path).resolve()
    frontend_root = AppConfig.FRONTEND_DIR.resolve()
    try:
        candidate.relative_to(frontend_root)
        if candidate.is_file() and candidate.suffix.lower() in {".html", ".htm"}:
            return FileResponse(str(candidate), media_type="text/html")
        if candidate.is_file() and candidate.suffix.lower() in {".js", ".css", ".png", ".jpg", ".svg", ".ico", ".woff", ".woff2", ".json", ".map", ".txt", ".webp"}:
            return FileResponse(str(candidate))
    except (ValueError, OSError):
        pass

    # SPA fallback for client routes only
    index_path = AppConfig.FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Page not found")

# ==========================================================
# GRACEFUL SHUTDOWN HANDLER (FIXED FOR POWERSHELL)
# ==========================================================
import signal
import sys

def shutdown_handler(signum, frame):
    """Handle Ctrl+C gracefully for Linux/Mac."""
    print("\n\n🛑 Shutting down gracefully...")
    try:
        if hasattr(app.state, "optimizer") and app.state.optimizer is not None:
            if hasattr(app.state.optimizer, 'save_and_shutdown'):
                result = app.state.optimizer.save_and_shutdown()
                print(f"✅ {result.get('message', 'Data saved')}")
        print("👋 Goodbye!")
    except Exception as e:
        print(f"⚠️ Error during shutdown: {e}")
    sys.exit(0)

# Signals only work in the main thread (Colab/background threads must skip this)
import threading
if threading.current_thread() is threading.main_thread():
    try:
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
    except ValueError:
        pass  # e.g. non-main thread or restricted environment

# ==========================================================
# MAIN ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    try:
        run_kwargs = dict(
            app="main:app",
            host=AppConfig.HOST,
            port=AppConfig.PORT,
            log_config=None,
            access_log=True,
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
        if AppConfig.DEBUG:
            run_kwargs["reload"] = True
            # Critical: do NOT reload when yt-dlp writes into downloads/ (kills active downloads)
            run_kwargs["reload_excludes"] = [
                "downloads/*",
                "downloads/**",
                "uploads/*",
                "uploads/**",
                "cache/*",
                "cache/**",
                "data/*",
                "data/**",
                "logs/*",
                "logs/**",
                "*/__pycache__/*",
                "*.pyc",
            ]
        else:
            run_kwargs["workers"] = int(os.getenv("WEB_WORKERS", "1"))
        uvicorn.run(**run_kwargs)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down gracefully...")
        try:
            if hasattr(app.state, "optimizer") and app.state.optimizer is not None:
                if hasattr(app.state.optimizer, 'save_and_shutdown'):
                    result = app.state.optimizer.save_and_shutdown()
                    print(f"✅ {result.get('message', 'Data saved')}")
            print("👋 Goodbye!")
        except Exception as e:
            print(f"⚠️ Error during shutdown: {e}")
try:
    app.include_router(skills_routes.router)
except Exception:
    pass

try:
    from routes import agent as agent_routes
    app.include_router(agent_routes.router)
except Exception as _e:
    logging.getLogger("vision-ai").warning("agent router skipped: %s", _e)

try:
    from routes import workers as workers_routes
    app.include_router(workers_routes.router)
except Exception as _werr:
    logging.getLogger("vision-ai").warning("workers router skipped: %s", _werr)



try:
    from routes.engine_v53 import router as engine_v53_router
    app.include_router(engine_v53_router)
    logging.getLogger("vision-ai").info("✅ Engine v5.3 mounted at /api/engine")
except Exception as _e53:
    logging.getLogger("vision-ai").error("Engine v5.3 mount failed: %s", _e53)


try:
    from routes.forge_v54 import router as forge_v54_router
    app.include_router(forge_v54_router)
    logging.getLogger("vision-ai").info("✅ Forge v5.4 mounted at /api/forge")
except Exception as _f54:
    logging.getLogger("vision-ai").error("Forge v5.4 mount failed: %s", _f54)

@app.exception_handler(Exception)
async def vision_self_heal(request: Request, exc: Exception):
    """Self-healing: never crash session UI on unhandled errors."""
    import logging as _logging
    _logging.getLogger("vision-ai.selfheal").exception("Unhandled: %s %s", request.url.path, exc)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "internal_error",
            "message": "Something went wrong. Your session is safe — retry or simplify the request.",
            "path": str(request.url.path),
            "hint": "Check /health and /api/rag/health. Large uploads index in the background.",
        },
    )

