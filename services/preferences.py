"""User preferences service — server is source of truth."""
from __future__ import annotations

from typing import Any, Dict, Optional

# Session type used only in annotations via string

try:
    from services.models_db import User, UserPreferences
except Exception:  # SQLAlchemy not installed in minimal test envs
    User = None  # type: ignore
    UserPreferences = None  # type: ignore

ALLOWED = {
    "appearance": {
        "theme_mode": {"system", "light", "dark"},
        "theme_preset": {"default", "humanly", "nord", "ocean", "forest", "violet", "high-contrast"},
        "density": {"comfortable", "compact"},
        "reduced_motion": bool,
        "high_contrast": bool,
        "text_scale": {0.9, 1.0, 1.1, 1.2, 1.3},
    },
    "chat": {
        "chat_language": str,
        "enter_to_send": bool,
        "show_timestamps": bool,
        "auto_scroll": bool,
        "response_style": {"concise", "balanced", "detailed"},
        "reasoning_level": {"fast", "balanced", "deep"},
        "default_model": str,
        "auto_model_routing": bool,
        "web_search_mode": {"auto", "on", "off"},
        "vision_mode": {"auto", "on", "off"},
    },
    "voice": {
        "stt_language": str,
        "tts_language": str,
        "auto_speak": bool,
        "voice_speed": (0.5, 2.0),
        "voice_volume": (0.0, 1.0),
    },
    "notifications": {
        "browser_notifications": bool,
        "task_notifications": bool,
        "error_notifications": bool,
    },
    "privacy": {
        "history_enabled": bool,
    },
}

FIELD_MAP = {
    "theme_mode": "theme_mode",
    "theme_preset": "theme_preset",
    "density": "density",
    "reduced_motion": "reduced_motion",
    "high_contrast": "high_contrast",
    "text_scale": "text_scale",
    "chat_language": "chat_language",
    "enter_to_send": "enter_to_send",
    "show_timestamps": "show_timestamps",
    "auto_scroll": "auto_scroll",
    "response_style": "response_style",
    "reasoning_level": "reasoning_level",
    "default_model": "default_model",
    "auto_model_routing": "auto_model_routing",
    "web_search_mode": "web_search_mode",
    "vision_mode": "vision_mode",
    "stt_language": "stt_language",
    "tts_language": "tts_language",
    "auto_speak": "auto_speak",
    "voice_speed": "voice_speed",
    "voice_volume": "voice_volume",
    "browser_notifications": "browser_notifications",
    "task_notifications": "task_notifications",
    "error_notifications": "error_notifications",
    "history_enabled": "history_enabled",
}


def defaults_dict() -> Dict[str, Any]:
    return {
        "appearance": {
            "theme_mode": "dark",
            "theme_preset": "default",
            "density": "comfortable",
            "reduced_motion": False,
            "high_contrast": False,
            "text_scale": 1.0,
        },
        "chat": {
            "chat_language": "auto",
            "enter_to_send": True,
            "show_timestamps": False,
            "auto_scroll": True,
            "response_style": "balanced",
            "reasoning_level": "balanced",
            "default_model": "auto",
            "auto_model_routing": True,
            "web_search_mode": "auto",
            "vision_mode": "auto",
        },
        "voice": {
            "stt_language": "en-US",
            "tts_language": "en-US",
            "auto_speak": False,
            "voice_speed": 1.0,
            "voice_volume": 1.0,
        },
        "notifications": {
            "browser_notifications": False,
            "task_notifications": True,
            "error_notifications": True,
        },
        "privacy": {
            "history_enabled": True,
        },
        "meta": {"preferences_version": getattr(UserPreferences, "PREFERENCES_VERSION", 1) if UserPreferences else 1},
    }


def row_to_dict(pref: UserPreferences) -> Dict[str, Any]:
    return {
        "appearance": {
            "theme_mode": pref.theme_mode,
            "theme_preset": pref.theme_preset,
            "density": pref.density,
            "reduced_motion": pref.reduced_motion,
            "high_contrast": pref.high_contrast,
            "text_scale": pref.text_scale,
        },
        "chat": {
            "chat_language": pref.chat_language,
            "enter_to_send": pref.enter_to_send,
            "show_timestamps": pref.show_timestamps,
            "auto_scroll": pref.auto_scroll,
            "response_style": pref.response_style,
            "reasoning_level": pref.reasoning_level,
            "default_model": pref.default_model,
            "auto_model_routing": pref.auto_model_routing,
            "web_search_mode": pref.web_search_mode,
            "vision_mode": pref.vision_mode,
        },
        "voice": {
            "stt_language": pref.stt_language,
            "tts_language": pref.tts_language,
            "auto_speak": pref.auto_speak,
            "voice_speed": pref.voice_speed,
            "voice_volume": pref.voice_volume,
        },
        "notifications": {
            "browser_notifications": pref.browser_notifications,
            "task_notifications": pref.task_notifications,
            "error_notifications": pref.error_notifications,
        },
        "privacy": {"history_enabled": pref.history_enabled},
        "meta": {"preferences_version": pref.preferences_version},
    }


def ensure_preferences(db, user: "User") -> UserPreferences:
    if user.preferences:
        return user.preferences
    pref = UserPreferences(user_id=user.id)
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


def get_or_create_user_by_username(db, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username.lower()).first()


def validate_patch(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate nested patch; raise ValueError with field message."""
    if not isinstance(payload, dict):
        raise ValueError("Body must be an object")
    out: Dict[str, Any] = {}
    for section, fields in payload.items():
        if section == "meta":
            continue
        if section not in ALLOWED:
            raise ValueError(f"Unknown section: {section}")
        if not isinstance(fields, dict):
            raise ValueError(f"{section} must be an object")
        allowed_fields = ALLOWED[section]
        section_out: Dict[str, Any] = {}
        for key, value in fields.items():
            if key not in allowed_fields:
                raise ValueError(f"Unknown field: {section}.{key}")
            rule = allowed_fields[key]
            if rule is bool:
                if not isinstance(value, bool):
                    raise ValueError(f"{section}.{key} must be boolean")
            elif isinstance(rule, set):
                if isinstance(next(iter(rule)), float) or any(isinstance(x, float) for x in rule):
                    # text_scale set of floats
                    try:
                        fv = float(value)
                    except (TypeError, ValueError):
                        raise ValueError(f"{section}.{key} invalid")
                    if fv not in rule:
                        raise ValueError(f"{section}.{key} must be one of {sorted(rule)}")
                    value = fv
                else:
                    if value not in rule:
                        raise ValueError(f"{section}.{key} must be one of {sorted(rule)}")
            elif isinstance(rule, tuple) and len(rule) == 2:
                try:
                    fv = float(value)
                except (TypeError, ValueError):
                    raise ValueError(f"{section}.{key} must be a number")
                if not (rule[0] <= fv <= rule[1]):
                    raise ValueError(f"{section}.{key} must be between {rule[0]} and {rule[1]}")
                value = fv
            elif rule is str:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{section}.{key} must be a non-empty string")
                value = value.strip()[:64]
            section_out[key] = value
        if section_out:
            out[section] = section_out
    return out


def apply_patch(pref: UserPreferences, patch: Dict[str, Any]) -> UserPreferences:
    for section, fields in patch.items():
        for key, value in fields.items():
            col = FIELD_MAP.get(key)
            if col:
                setattr(pref, col, value)
    return pref


def response_style_instruction(style: str) -> str:
    return {
        "concise": "Respond concisely. Prefer short paragraphs and bullet points when useful.",
        "balanced": "Respond with a clear, balanced level of detail.",
        "detailed": "Respond in depth with thorough explanations and structured reasoning.",
    }.get(style or "balanced", "Respond with a clear, balanced level of detail.")


def reasoning_instruction(level: str) -> str:
    return {
        "fast": "Prioritize speed and direct answers; skip lengthy deliberation.",
        "balanced": "Balance speed and careful reasoning.",
        "deep": "Think carefully step by step before answering; show key reasoning when helpful.",
    }.get(level or "balanced", "Balance speed and careful reasoning.")


def build_policy_prompt(pref: Optional[UserPreferences]) -> str:
    if not pref:
        return ""
    parts = [
        response_style_instruction(pref.response_style),
        reasoning_instruction(pref.reasoning_level),
    ]
    if pref.chat_language and pref.chat_language != "auto":
        parts.append(f"Prefer answering in language code: {pref.chat_language}.")
    return " ".join(parts)
