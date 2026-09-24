"""Device tier + arithmetic fallback APIs."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.device_profile import profile_runtime, simple_arithmetic_fallback

router = APIRouter(prefix="/api/device", tags=["Device"])


@router.get("/profile")
async def device_profile():
    return profile_runtime()


class MathIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


@router.post("/math")
async def device_math(body: MathIn):
    return simple_arithmetic_fallback(body.text)
