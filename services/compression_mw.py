"""Response compression: prefer Brotli, fall back to identity (GZip handled by Starlette).

Order of effectiveness for HTTP (typical web):
  Zstd (where supported) > Brotli > Gzip > uncompressed

Browsers send Accept-Encoding: br, gzip, deflate. We negotiate Brotli when
the `brotli` package is installed; otherwise GZipMiddleware covers gzip.
"""
from __future__ import annotations

import io
from typing import Callable

try:
    import brotli
    _HAS_BR = True
except Exception:
    _HAS_BR = False


class BrotliMiddleware:
    """ASGI middleware: compress text responses with Brotli when client accepts br."""

    def __init__(self, app, minimum_size: int = 500, quality: int = 4):
        self.app = app
        self.minimum_size = minimum_size
        self.quality = quality

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not _HAS_BR:
            return await self.app(scope, receive, send)

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers") or []}
        accept = headers.get("accept-encoding", "")
        if "br" not in accept:
            return await self.app(scope, receive, send)

        start_message = {}
        body = bytearray()

        async def send_wrapper(message):
            nonlocal start_message, body
            if message["type"] == "http.response.start":
                start_message = message
                return
            if message["type"] == "http.response.body":
                body.extend(message.get("body") or b"")
                if message.get("more_body"):
                    return
                # final body
                raw = bytes(body)
                hdrs = list(start_message.get("headers") or [])
                # skip if already encoded
                for k, v in hdrs:
                    if k.lower() == b"content-encoding":
                        await send(start_message)
                        await send({"type": "http.response.body", "body": raw})
                        return
                ctype = b""
                for k, v in hdrs:
                    if k.lower() == b"content-type":
                        ctype = v.lower()
                        break
                compressible = (
                    b"text/" in ctype
                    or b"json" in ctype
                    or b"javascript" in ctype
                    or b"xml" in ctype
                    or b"svg" in ctype
                    or b"wasm" in ctype
                )
                if compressible and len(raw) >= self.minimum_size:
                    try:
                        compressed = brotli.compress(raw, quality=self.quality)
                        if len(compressed) < len(raw):
                            new_headers = [
                                (k, v)
                                for k, v in hdrs
                                if k.lower() not in (b"content-length", b"content-encoding")
                            ]
                            new_headers.append((b"content-encoding", b"br"))
                            new_headers.append((b"content-length", str(len(compressed)).encode()))
                            new_headers.append((b"vary", b"Accept-Encoding"))
                            start_message = {**start_message, "headers": new_headers}
                            await send(start_message)
                            await send({"type": "http.response.body", "body": compressed})
                            return
                    except Exception:
                        pass
                await send(start_message)
                await send({"type": "http.response.body", "body": raw})

        await self.app(scope, receive, send_wrapper)


def mount_compression(app) -> list:
    """Register GZip + optional Brotli. Returns list of enabled labels."""
    from fastapi.middleware.gzip import GZipMiddleware

    enabled = []
    # Gzip: smaller minimum so CSS/JS/JSON compress more often
    app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=6)
    enabled.append("gzip")
    if _HAS_BR:
        app.add_middleware(BrotliMiddleware, minimum_size=400, quality=4)
        enabled.append("brotli")
    return enabled
