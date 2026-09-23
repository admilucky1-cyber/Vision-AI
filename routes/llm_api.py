"""Vision AI LLM API — status, models, complete, stream."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services import llm_service as llm

logger = logging.getLogger("vision-ai.llm-api")
router = APIRouter(prefix="/api/llm", tags=["LLM"])


class CompleteIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=100_000)
    context: str = Field(default="", max_length=500_000)
    backend: str = Field(default="auto", max_length=64)
    username: Optional[str] = Field(default=None, max_length=128)


class CompleteOut(BaseModel):
    ok: bool
    text: str
    provider: str = "unknown"
    latency_ms: int = 0
    backend: str = "auto"
    error: Optional[str] = None


@router.get("/health")
def llm_health():
    return {"ok": True, "service": "llm", "product": "Vision AI", **llm.provider_status()}


@router.get("/providers")
def providers():
    return llm.provider_status()


@router.get("/models")
def models():
    return {"ok": True, "models": llm.list_models()}


@router.post("/complete", response_model=CompleteOut)
def complete(body: CompleteIn):
    result = llm.complete_detailed(
        body.message,
        context=body.context,
        backend=body.backend,
        username=body.username,
    )
    return CompleteOut(
        ok=result.ok,
        text=result.text,
        provider=result.provider,
        latency_ms=result.latency_ms,
        backend=result.backend_requested,
        error=result.error,
    )


@router.post("/stream")
def stream(body: CompleteIn):
    def event_gen():
        try:
            for ev in llm.stream_tokens(body.message, context=body.context, backend=body.backend):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        yield "data: {\"event\": \"end\"}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/test")
def test_providers():
    return llm.test_all()
