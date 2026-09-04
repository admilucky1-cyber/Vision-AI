# Production fixes applied on top of VISION-AI-v3.2.1

## Applied in this package

### 🔴 Critical / high impact
1. **WEB_WORKERS default = 1** (Dockerfile + main.py) — avoids multi-process races on JSON user store
2. **CORS_ORIGINS** separate env var; production no longer derives origins incorrectly from hostnames
3. **ALLOWED_HOSTS=*** is now a **fatal error** in production (not just a warning)
4. **Password minimum length** raised 6 → 10
5. **Refresh token** endpoint rate-limited (`20/minute`)
6. **Payment plan validation** — only `pro`/`team` for manual payments; server-side price is authoritative
7. **Chat errors** no longer leak raw exception text to clients
8. **YouTube endpoints** reject non-YouTube URLs (SSRF surface reduced)
9. **Public `/health`** simplified to `{status, version}`; details moved to `/health/detailed`
10. **Version test** fixed for 3.x series

### 🟠 UX / security polish
11. **KaTeX** math rendering in chat (formulas display correctly)
12. **API key form** assigns values via DOM `.value` instead of interpolating into `innerHTML`
13. **Railway healthcheckTimeout** raised 30 → 120s
14. **.env.example** updated with CORS_ORIGINS, WEB_WORKERS=1, clearer production guidance

### Still recommended before heavy paid traffic
- Move users / payments / usage from JSON files → PostgreSQL
- Add Redis for shared rate limits / token blacklist across workers
- Refresh-token rotation with server-side jti store
- Total upload size / file-count limits before reading bodies
- Optional: sessionStorage (or non-persistent) for custom API keys

