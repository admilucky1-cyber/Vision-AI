
"""Shared request validation (Pydantic)."""
from __future__ import annotations
from typing import Optional
try:
    from pydantic import BaseModel, Field, field_validator
except ImportError:  # pragma: no cover
    BaseModel = object  # type: ignore
    Field = lambda *a, **k: None  # type: ignore
    field_validator = lambda *a, **k: (lambda f: f)  # type: ignore


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=20000)
    model: str = "auto"
    generate_images: bool = True

    @field_validator("message")
    @classmethod
    def strip_msg(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("message required")
        return v
