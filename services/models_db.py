"""ORM models: User + UserPreferences."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), default=_uuid, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_id: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    messages_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_month: Mapped[str] = mapped_column(String(7), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    preferences: Mapped["UserPreferences"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    PREFERENCES_VERSION = 1

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferences_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Appearance
    theme_mode: Mapped[str] = mapped_column(String(16), default="dark", nullable=False)
    theme_preset: Mapped[str] = mapped_column(String(32), default="default", nullable=False)
    density: Mapped[str] = mapped_column(String(16), default="comfortable", nullable=False)
    reduced_motion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    high_contrast: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    text_scale: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Chat
    chat_language: Mapped[str] = mapped_column(String(16), default="auto", nullable=False)
    enter_to_send: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_timestamps: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_scroll: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    response_style: Mapped[str] = mapped_column(String(16), default="balanced", nullable=False)
    reasoning_level: Mapped[str] = mapped_column(String(16), default="balanced", nullable=False)
    default_model: Mapped[str] = mapped_column(String(64), default="auto", nullable=False)
    auto_model_routing: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    web_search_mode: Mapped[str] = mapped_column(String(16), default="auto", nullable=False)
    vision_mode: Mapped[str] = mapped_column(String(16), default="auto", nullable=False)

    # Voice
    stt_language: Mapped[str] = mapped_column(String(16), default="en-US", nullable=False)
    tts_language: Mapped[str] = mapped_column(String(16), default="en-US", nullable=False)
    auto_speak: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voice_speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    voice_volume: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Notifications
    browser_notifications: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    task_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Privacy
    history_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="preferences")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
