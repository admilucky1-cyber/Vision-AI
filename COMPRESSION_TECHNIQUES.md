# Compression techniques (coding)

**Effectiveness order (typical HTTP payloads):**
`Zstd > Brotli > Gzip > uncompressed`

| Codec | Where | Notes |
|-------|--------|------|
| **Zstd** | APIs, internal pipelines, some CDNs | Best ratio/speed balance; not all browsers accept `zstd` yet on every path |
| **Brotli (`br`)** | Static assets + JSON/HTML in modern browsers | Excellent for text; Vision AI enables when `brotli` package is installed |
| **Gzip** | Universal fallback | Every browser; Starlette `GZipMiddleware` |
| **None** | Tiny bodies | Skip if size &lt; threshold (CPU waste) |

**Reel claim (1.5GB → ~300MB):** achievable on **highly compressible text/JSON/logs** with strong codecs + caching + not shipping raw dumps. Binary media (video/images) need different tools (WebP/AVIF, video bitrate), not Gzip alone.

**Vision AI:**
- Gzip always (min ~500 bytes, level 6)
- Brotli when `pip install brotli` / Docker requirements
- Client must send `Accept-Encoding: br, gzip`
