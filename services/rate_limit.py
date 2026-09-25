"""Single shared SlowAPI limiter — must match app.state.limiter."""
from __future__ import annotations

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, default_limits=[])
except Exception:  # pragma: no cover
    class _NoopLimiter:
        def limit(self, *a, **k):
            def deco(fn):
                return fn
            return deco

    limiter = _NoopLimiter()  # type: ignore
