"""
Unified Multi-Modal Plugin API — secure hooks into ingestion pipeline.
Plugins are pure callables registered in-process (no arbitrary pickle).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("vision-ai.plugins")

# Hook names
HOOKS = (
    "pre_ingest",       # text -> text
    "tokenize",         # text -> List[str]
    "ocr_parse",        # bytes, filename -> str
    "post_chunk",       # List[str] -> List[str]
    "pre_search",       # query -> query
)

_REGISTRY: Dict[str, List[Callable]] = {h: [] for h in HOOKS}


def register(hook: str, fn: Callable, name: str = "") -> None:
    if hook not in _REGISTRY:
        raise ValueError(f"Unknown hook: {hook}")
    fn.__plugin_name__ = name or getattr(fn, "__name__", "plugin")
    _REGISTRY[hook].append(fn)
    logger.info("Plugin registered: %s → %s", hook, fn.__plugin_name__)


def list_plugins() -> Dict[str, List[str]]:
    return {h: [getattr(f, "__plugin_name__", f.__name__) for f in fns] for h, fns in _REGISTRY.items()}


def run_hook(hook: str, *args, **kwargs):
    if hook not in _REGISTRY:
        return args[0] if args else None
    value = args[0] if args else None
    rest = args[1:]
    for fn in _REGISTRY[hook]:
        try:
            value = fn(value, *rest, **kwargs)
        except Exception as e:
            logger.warning("Plugin %s failed on %s: %s", getattr(fn, "__plugin_name__", "?"), hook, e)
    return value


# Built-in example: simple domain tokenizer for snake_case / camelCase
def _code_tokenizer(text: str, *a, **k) -> List[str]:
    if not isinstance(text, str):
        return []
    parts = re.findall(r"[A-Za-z]+(?:[A-Z][a-z]+)*|[a-z]+(?:_[a-z]+)+|\d+|[^\s]", text)
    return [p for p in parts if p.strip()]


register("tokenize", _code_tokenizer, "builtin_code_tokenizer")
