"""
Vision AI v2.0 - API Router
============================
Aggregates all sub‑routers (chat, login, upgrade, upload) under the `/api` prefix.
Provides health checks, version info, and centralized error handling.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from .chat import router as chat_router
from .login import router as login_router
from .upgrade import router as upgrade_router
from .upload import router as upload_router
from .usage import router as usage_router
import time

# ============================================================
# GLOBAL START TIME (for uptime tracking)
# ============================================================
START_TIME = time.time()

# ============================================================
# API ROUTER
# ============================================================
router = APIRouter(
    prefix="/api",
    tags=["Vision AI API"],
    responses={
        404: {"description": "Endpoint not found"},
        500: {"description": "Internal server error"},
    }
)

# ============================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================

@router.get(
    "/",
    summary="API Health Check",
    description="Returns the current status of the Vision AI API.",
    response_model=Dict[str, str],
    tags=["Health"]
)
async def api_root() -> Dict[str, str]:
    """Health check endpoint for the Vision AI API."""
    return {
        "message": "Vision AI API v2.0",
        "status": "healthy",
        "version": "3.0.5"
    }

@router.get(
    "/status",
    summary="Detailed API Status",
    description="Returns detailed status information about all API services.",
    tags=["Health"]
)
async def api_status() -> Dict[str, Any]:
    """Detailed status check endpoint."""
    uptime_seconds = int(time.time() - START_TIME)
    uptime_human = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m"

    return {
        "status": "operational",
        "version": "3.0.5",
        "uptime": uptime_human,
        "services": {
            "chat": "available",
            "authentication": "available",
            "upgrade": "available",
            "upload": "available"
        },
        "timestamp": "2026-07-28T12:00:00Z"
    }

@router.get(
    "/version",
    summary="API Version",
    description="Returns the current API version.",
    tags=["Health"]
)
async def api_version() -> Dict[str, str]:
    """Version information endpoint."""
    return {
        "version": "3.0.5",
        "api_version": "v3",
        "build_date": "2026-07-28"
    }

# ============================================================
# ROUTER INCLUSIONS
# ============================================================

router.include_router(
    chat_router,
    prefix="/chat",
    tags=["Chat"]
)

router.include_router(
    login_router,
    prefix="/auth",
    tags=["Authentication"]
)

router.include_router(
    upgrade_router,
    prefix="/upgrade",
    tags=["Upgrade"]
)

router.include_router(
    upload_router,
    prefix="/upload",
    tags=["Upload"]
)

router.include_router(
    usage_router,
    prefix="/usage",
    tags=["Usage"]
)

# ============================================================
# ERROR HANDLING
# ============================================================

class RouterVerificationError(Exception):
    """Raised when a router is missing routes or not properly configured."""
    pass

@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException) -> Dict[str, Any]:
    """Custom HTTP exception handler for consistent error responses."""
    return {
        "error": True,
        "status_code": exc.status_code,
        "detail": exc.detail
    }

@router.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception) -> Dict[str, Any]:
    """Generic exception handler for unexpected errors."""
    return {
        "error": True,
        "status_code": 500,
        "detail": "An unexpected error occurred. Please try again later."
    }

# ============================================================
# ROUTER VERIFICATION
# ============================================================

def verify_routers() -> bool:
    """
    Verify that all required routers are properly initialized and have routes.
    
    Returns:
        bool: True if all routers are properly configured, False otherwise.
    """
    router_checks = {
        "chat": chat_router,
        "login": login_router,
        "upgrade": upgrade_router,
        "upload": upload_router,
        "usage": usage_router,
    }

    all_passed = True
    for name, r in router_checks.items():
        try:
            assert r.routes, f"{name} router has no routes"
        except AssertionError as e:
            print(f"❌ Router verification failed: {e}")
            all_passed = False
            raise RouterVerificationError(str(e))

    if all_passed:
        print("✅ All routers verified successfully.")
    return all_passed

# ============================================================
# STARTUP VERIFICATION
# ============================================================

try:
    verify_routers()
except RouterVerificationError as e:
    print(f"⚠️ Critical router error: {e}")
    # In production, you might want to exit or alert here.

