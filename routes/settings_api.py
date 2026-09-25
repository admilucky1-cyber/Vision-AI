"""Server-authoritative user settings API."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.db import get_db, init_db
from services.models_db import User, UserPreferences
from services import preferences as pref_svc

logger = logging.getLogger("vision-ai.settings")

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class SettingsPatch(BaseModel):
    appearance: Optional[Dict[str, Any]] = None
    chat: Optional[Dict[str, Any]] = None
    voice: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None
    privacy: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"


def _username_from_request(request: Request) -> Optional[str]:
    # Prefer dependency-injected user if middleware set it
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("username"):
        return str(user["username"]).lower()
    return None


async def _current_user_dict(request: Request) -> dict:
    """Reuse login auth without circular imports at module load."""
    try:
        from routes.login import get_current_active_user
        # get_current_active_user is FastAPI Depends-style async
        from fastapi.security import OAuth2PasswordBearer
        from fastapi import Depends as Dep
    except Exception as e:
        raise HTTPException(status_code=500, detail="Auth unavailable") from e

    # Manual call path: extract bearer
    auth = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from routes.login import get_current_user
    # get_current_user expects token via Depends — call internal path
    from jose import JWTError, jwt
    import os
    SECRET = os.getenv("SECRET_KEY", "change-me-in-production")
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        if payload.get("guest"):
            return {"username": "guest", "plan": "free", "guest": True}
        from routes.login import user_db
        user = user_db.get_user(username)
        if not user or user.get("disabled"):
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def _db_user(db: Session, username: str) -> User:
    user = db.query(User).filter(User.username == username.lower()).first()
    if not user:
        # Lazy create from JSON user_db snapshot
        try:
            from routes.login import user_db
            raw = user_db.get_user(username)
        except Exception:
            raw = None
        if not raw:
            raise HTTPException(status_code=404, detail="User not found in database — run migration")
        user = User(
            username=raw["username"].lower(),
            email=(raw.get("email") or f"{username}@local").lower(),
            full_name=raw.get("full_name") or "",
            password_hash=raw.get("hashed_password") or raw.get("password_hash") or "",
            role=raw.get("role") or ("admin" if raw.get("plan") == "admin" else "user"),
            plan=raw.get("plan") or "free",
            disabled=bool(raw.get("disabled")),
            google_id=str(raw.get("google_id") or ""),
            messages_this_month=int(raw.get("messages_this_month") or 0),
            usage_month=str(raw.get("usage_month") or ""),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        pref_svc.ensure_preferences(db, user)
    return user


@router.get("")
async def get_settings(request: Request, db: Session = Depends(get_db)):
    current = await _current_user_dict(request)
    if current.get("guest"):
        return pref_svc.defaults_dict()
    user = _db_user(db, current["username"])
    pref = pref_svc.ensure_preferences(db, user)
    return pref_svc.row_to_dict(pref)


@router.get("/schema")
async def settings_schema():
    return {
        "version": UserPreferences.PREFERENCES_VERSION,
        "sections": list(pref_svc.ALLOWED.keys()),
        "defaults": pref_svc.defaults_dict(),
    }


@router.patch("")
async def patch_settings(body: SettingsPatch, request: Request, db: Session = Depends(get_db)):
    current = await _current_user_dict(request)
    if current.get("guest"):
        raise HTTPException(status_code=401, detail="Sign in to sync settings")
    payload = body.model_dump(exclude_none=True)
    try:
        patch = pref_svc.validate_patch(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "PREFERENCE_INVALID", "message": str(e)}},
        )
    user = _db_user(db, current["username"])
    pref = pref_svc.ensure_preferences(db, user)
    pref_svc.apply_patch(pref, patch)
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref_svc.row_to_dict(pref)


@router.post("/reset")
async def reset_settings(request: Request, db: Session = Depends(get_db)):
    current = await _current_user_dict(request)
    if current.get("guest"):
        raise HTTPException(status_code=401, detail="Sign in to reset settings")
    user = _db_user(db, current["username"])
    pref = pref_svc.ensure_preferences(db, user)
    # Reset by replacing row fields with defaults
    defaults = UserPreferences(user_id=user.id)
    for col in pref_svc.FIELD_MAP.values():
        setattr(pref, col, getattr(defaults, col))
    pref.preferences_version = UserPreferences.PREFERENCES_VERSION
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref_svc.row_to_dict(pref)
