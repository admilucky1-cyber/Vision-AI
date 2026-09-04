"""Vision AI v5.3 — Agentic loop, branches, vault, telemetry APIs."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("vision-ai.engine53")
router = APIRouter(prefix="/api/engine", tags=["Engine v5.3"])

try:
    from routes.login import get_current_active_user
except Exception:
    async def get_current_active_user():  # type: ignore
        return {"id": "guest", "username": "guest"}


def _uk(user: dict, request: Request) -> str:
    if user and user.get("id"):
        return f"user:{user['id']}"
    if user and user.get("username"):
        return f"user:{user['username']}"
    return request.headers.get("X-Vision-Session") or "guest"


# ----- Agentic -----
class AgenticIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=12000)
    max_steps: int = Field(3, ge=1, le=5)
    use_llm_repair: bool = False


@router.post("/agentic/run")
async def agentic_run_api(body: AgenticIn, current_user: dict = Depends(get_current_active_user)):
    from services.agentic_loop import agentic_run

    repair_fn = None
    if body.use_llm_repair:
        def repair_fn(code: str, error: str) -> Optional[str]:
            try:
                from services.llm import ask_ai
                prompt = (
                    "Fix this Python code. Return ONLY the corrected code, no markdown.\n"
                    f"Error: {error}\n\nCode:\n{code}"
                )
                out = ask_ai(prompt, context="", backend="auto")
                if not out:
                    return None
                text = out if isinstance(out, str) else str(out)
                text = text.strip()
                if text.startswith("```"):
                    text = text.strip("`")
                    if text.startswith("python"):
                        text = text[6:]
                return text.strip()
            except Exception:
                return None

    t0 = time.time()
    result = agentic_run(body.code, max_steps=body.max_steps, repair_fn=repair_fn)
    result["latency_ms"] = round((time.time() - t0) * 1000, 1)
    return {"ok": True, **result}


# ----- Branches -----
class BranchIn(BaseModel):
    root_chat_id: str
    from_message_index: int = 0
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    label: str = ""
    routing_profile: str = "auto"
    system_prompt: str = ""


@router.post("/branches")
async def create_branch_api(body: BranchIn, request: Request, current_user: dict = Depends(get_current_active_user)):
    from services.thread_branches import create_branch
    if not body.messages:
        raise HTTPException(400, "messages required to fork")
    rec = create_branch(
        _uk(current_user, request),
        body.root_chat_id,
        body.from_message_index,
        body.messages,
        body.label,
        body.routing_profile,
        body.system_prompt,
    )
    return {"ok": True, "branch": rec}


@router.get("/branches")
async def list_branches_api(request: Request, root_chat_id: Optional[str] = None, current_user: dict = Depends(get_current_active_user)):
    from services.thread_branches import list_branches
    return {"ok": True, "branches": list_branches(_uk(current_user, request), root_chat_id)}


@router.get("/branches/{branch_id}")
async def get_branch_api(branch_id: str, request: Request, root_chat_id: str = "", current_user: dict = Depends(get_current_active_user)):
    from services.thread_branches import get_branch
    rec = get_branch(_uk(current_user, request), root_chat_id, branch_id)
    if not rec:
        raise HTTPException(404, "branch not found")
    return {"ok": True, "branch": rec}


# ----- Vault -----
class VaultConfigIn(BaseModel):
    target_dir: str = Field(..., min_length=1, max_length=500)
    interval_min: int = Field(30, ge=5, le=1440)


@router.get("/vault/config")
async def vault_config(current_user: dict = Depends(get_current_active_user)):
    from services.local_vault import get_config, list_backups
    return {"ok": True, "config": get_config(), "backups": list_backups(10)}


@router.post("/vault/config")
async def vault_set_config(body: VaultConfigIn, current_user: dict = Depends(get_current_active_user)):
    from services.local_vault import set_config
    return {"ok": True, "config": set_config(body.target_dir, body.interval_min)}


@router.post("/vault/backup")
async def vault_backup(current_user: dict = Depends(get_current_active_user)):
    from services.local_vault import run_backup
    return run_backup("manual")


# ----- Telemetry snapshot -----
@router.get("/telemetry")
async def telemetry_snapshot(request: Request, current_user: dict = Depends(get_current_active_user)):
    from services.routing_analytics import snapshot as ra
    from services.rag_engine_core import get_store, resolve_namespace, health_check
    ns = resolve_namespace(current_user, request.headers.get("X-Vision-Session"))
    store = get_store(ns).stats()
    return {
        "ok": True,
        "ts": time.time(),
        "routing": ra(),
        "rag": {"namespace": ns, "store": store, "health": health_check()},
    }
