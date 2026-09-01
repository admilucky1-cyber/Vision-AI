"""Agent status and skill suggestion API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from routes.login import get_current_active_user
from services.security import require_admin
from services.agent_orchestrator import agent_orchestrator

router = APIRouter(prefix="/agent", tags=["agent"])


class SuggestIn(BaseModel):
    query: str = Field(default="", max_length=4000)


@router.get("/status")
def agent_status(current_user: dict = Depends(get_current_active_user)):
    return agent_orchestrator.get_status()


@router.post("/suggest")
def agent_suggest(
    body: SuggestIn,
    current_user: dict = Depends(get_current_active_user),
):
    skills = agent_orchestrator.suggest_skill(body.query or "")
    return {"skills": skills}


@router.post("/warmup")
def agent_warmup(current_user: dict = Depends(get_current_active_user)):
    require_admin(current_user)
    return agent_orchestrator.warmup_colab()
