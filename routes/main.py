"""
Vision AI v2.0 - Production-Grade Multi-Modal AI Assistant
============================================================
Enterprise-ready FastAPI application with:
- Multi-provider AI routing (Gemini, DeepSeek, Groq, OpenRouter)
- Real-time Agentic RAG with document processing
- Diagram & image generation
- Self-learning optimizer
- YouTube tools
- JWT + OAuth2 authentication
- Rate limiting & security middleware

Version: 2.0.0
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
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field

# ==========================================================
# PATH RESOLUTION (Works from any directory)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent

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
    ALLOWED_HOSTS: List[str] = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",")]

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
        """Validate critical configuration and return warnings."""
        warnings = []
        if cls.SECRET_KEY in ("change-me-in-production", "your-secret-key-here", ""):
            warnings.append("WARNING: Using default SECRET_KEY. Change in production!")
        if not any([cls.GOOGLE_API_KEY, cls.GROQ_API_KEY, cls.DEEPSEEK_API_KEY, cls.OPENROUTER_API_KEY]):
            warnings.append("WARNING: No AI provider API keys configured. Chat will not work.")
        return warnings

# ==========================================================
# LIFESPAN MANAGEMENT
# ==========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
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

    # Validate config
    warnings = AppConfig.validate()
    for warning in warnings:
        logger.warning(warning)

    # Initialize optimizer
    try:
        from services.self_optimizer import optimizer
        app.state.optimizer = optimizer
        health = optimizer.get_health_status()

        logger.info("=" * 70)
        logger.info("Vision AI v2.0 Starting...")
        logger.info("=" * 70)
        logger.info(f"Version: 2.0.0 (Production Ready)")
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
app = FastAPI(
    title="Vision AI",
    description="Production-grade multi-modal AI assistant with document processing, diagram generation, and multi-model support.",
    version="2.6.0",
    docs_url="/docs" if AppConfig.DEBUG else None,
    redoc_url="/redoc" if AppConfig.DEBUG else None,
    lifespan=lifespan,
)

# ==========================================================
# RATE LIMITER
# ==========================================================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# ==========================================================
# SECURITY MIDDLEWARE
# ==========================================================
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=(self)"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
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
    max_age=3600,
    same_site="lax",
    https_only=not AppConfig.DEBUG,
)

# When allow_credentials=True, origins cannot be "*". Use explicit origins in production.
_cors_origins = ["*"] if AppConfig.DEBUG else [h for h in AppConfig.ALLOWED_HOSTS if h != "*"]
if not _cors_origins:
    _cors_origins = ["http://localhost:5050", "http://127.0.0.1:5050"]
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

# Load each router independently. If chat fails, login still loads!
_load_router("login", lambda: __import__("routes.login", fromlist=["router"]).router)
_load_router("chat", lambda: __import__("routes.chat", fromlist=["router"]).router)
_load_router("upload", lambda: __import__("routes.upload", fromlist=["router"]).router)
_load_router("upgrade", lambda: __import__("routes.upgrade", fromlist=["router"]).router)

if _loaded:
    logger.info(f"✅ Routers loaded: {', '.join(_loaded)}")
if _failed:
    logger.error(f"⚠️ Routers NOT loaded: {', '.join(n for n, _ in _failed)} — check errors above")

app.include_router(main_router)

# Health check to debug router issues
@app.get("/health/routers", tags=["System"])
async def router_health():
    return {"loaded": _loaded, "failed": [{"router": n, "error": e} for n, e in _failed]}

# ==========================================================
# HEALTH CHECK
# ==========================================================
@app.get("/health", tags=["System"])
async def health_check():
    """Comprehensive system health check."""
    from services.llm import GEMINI_AVAILABLE, GROQ_AVAILABLE

    uptime_seconds = int(time.time() - getattr(app.state, "start_time", time.time()))
    uptime_human = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m"

    return {
        "status": "healthy",
        "uptime": uptime_human,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.6.0",
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
        "middlewares": [
            "CORS", "GZip", "TrustedHosts", "RateLimiting", "SecurityHeaders",
            "CorrelationID", "ContentValidation", "RequestLogging", "SessionManagement"
        ],
    }

@app.get("/health/detailed", tags=["System"])
async def health_check_detailed():
    """Detailed health check with optimizer stats."""
    health_data = await health_check()
    if hasattr(app.state, "optimizer") and app.state.optimizer:
        health_data["optimizer"] = app.state.optimizer.get_health_status()
    return health_data

# ==========================================================
# STATIC FILES & FRONTEND ROUTING
# ==========================================================

# 1. Mount the entire frontend folder so CSS/JS/Images load properly
app.mount("/frontend", StaticFiles(directory=str(AppConfig.FRONTEND_DIR)), name="frontend")

# 2. Serve index.html
@app.get("/")
async def root_redirect():
    """Serve main chat application."""
    index_path = AppConfig.FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Frontend not found")

# 3. Serve upgrade.html
@app.get("/upgrade.html")
async def serve_upgrade_html():
    """Serve the pricing page correctly."""
    upgrade_path = AppConfig.FRONTEND_DIR / "upgrade.html"
    if upgrade_path.exists():
        return FileResponse(str(upgrade_path))
    raise HTTPException(status_code=404, detail="Upgrade page not found")

# 4. Serve settings.html
@app.get("/settings.html")
async def serve_settings_html():
    """Serve the settings page correctly."""
    settings_path = AppConfig.FRONTEND_DIR / "settings.html"
    if settings_path.exists():
        return FileResponse(str(settings_path))
    raise HTTPException(status_code=404, detail="Settings page not found")

# 5. 🟢 CRITICAL FIX: Serve login.html with raw HTML, NOT JSON
@app.get("/login.html")
async def serve_login_html(request: Request):
    """Serve the login page correctly."""
    login_path = AppConfig.FRONTEND_DIR / "login.html"
    if login_path.exists() and login_path.is_file():
        # ✅ Force the browser to treat it as raw HTML, not JSON
        return FileResponse(str(login_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Login page not found")

# 6. Serve favicon.ico
@app.get("/favicon.ico")
async def serve_favicon():
    """Serve favicon."""
    # Your favicon files are in /frontend/static/favicon/
    favicon_path = AppConfig.FRONTEND_DIR / "static" / "favicon" / "favicon-32x32.png"
    
    if favicon_path.exists() and favicon_path.is_file():
        return FileResponse(str(favicon_path), media_type="image/png")
    
    favicon_path_16 = AppConfig.FRONTEND_DIR / "static" / "favicon" / "favicon-16x16.png"
    if favicon_path_16.exists() and favicon_path_16.is_file():
        return FileResponse(str(favicon_path_16), media_type="image/png")
    
    return JSONResponse(content={"detail": "Favicon not found"}, status_code=404)

# 7. 🟢 Serve the Search Dashboard HTML (REPLACED THE JSON ROUTE)
@app.get("/admin/search/stats")
async def serve_search_dashboard():
    """Serve the search cache dashboard HTML."""
    dashboard_path = AppConfig.FRONTEND_DIR / "admin" / "search-dashboard.html"
    if dashboard_path.exists() and dashboard_path.is_file():
        return FileResponse(str(dashboard_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Search dashboard not found")

# ==========================================================
# CATCH-ALL ROUTE FOR SPA (Keep this at the BOTTOM!)
# ==========================================================
@app.get("/{path:path}")
async def catch_all(path: str):
    """Catch-all route for SPA frontends."""
    if path.startswith("api/") or path.startswith("auth/") or path.startswith("upgrade/") or path.startswith("upload/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    index_path = AppConfig.FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
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

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# ==========================================================
# MAIN ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(
            "main:app",
            host=AppConfig.HOST,
            port=AppConfig.PORT,
            reload=AppConfig.DEBUG,
            log_config=None,
            access_log=True,
        )
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