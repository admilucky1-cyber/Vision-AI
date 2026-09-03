"""
Vision AI — Usage & analytics API
GET  /api/usage/summary
POST /api/usage/ping
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services.usage_tracker import get_summary, record_message, record_session

router = APIRouter()


class PingIn(BaseModel):
    user_id: Optional[str] = Field(None, max_length=64)
    event: str = "session"


@router.get("/summary")
async def usage_summary(days: int = Query(14, ge=1, le=90)):
    return {"ok": True, **get_summary(days=days)}


@router.post("/ping")
async def usage_ping(body: PingIn):
    if body.event == "message":
        record_message(user_id=body.user_id or "anon", provider="frontend")
    else:
        record_session(user_id=body.user_id or "anon")
    return {"ok": True}


@router.get("/health")
async def usage_health():
    return {"ok": True, "service": "usage"}
