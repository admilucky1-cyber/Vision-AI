"""Skill market API — list / run only. Server-side code install disabled."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict

from services.skill_router import skill_router
try:
    from routes.login import get_current_active_user
except Exception:
    async def get_current_active_user():
        return {"id": "guest", "username": "guest", "plan": "free"}

router = APIRouter(prefix="/api/skills", tags=["skills"])


class RunIn(BaseModel):
    skill_id: str
    prompt: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_skills(current_user: dict = Depends(get_current_active_user)):
    return {"skills": skill_router.list_skills()}


@router.post("/run")
def run_skill(body: RunIn, current_user: dict = Depends(get_current_active_user)):
    # Only allow built-in skills from the registry (no user-uploaded code)
    return {"result": skill_router.run(body.skill_id, body.prompt, body.context)}


@router.post("/install")
def install_skill(current_user: dict = Depends(get_current_active_user)):
    raise HTTPException(
        status_code=501,
        detail="Custom server-side skills are disabled in production for security.",
    )


@router.delete("/{skill_id}")
def remove_skill(skill_id: str, current_user: dict = Depends(get_current_active_user)):
    raise HTTPException(
        status_code=501,
        detail="Custom server-side skills are disabled in production.",
    )
