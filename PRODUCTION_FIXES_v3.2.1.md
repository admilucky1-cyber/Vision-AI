# Vision AI v3.2.1 — Production & UI fixes

## Version
All primary sources now read **3.2.1** from `VERSION`:
- VERSION, main.py, pyproject.toml, requirements.txt header
- frontend titles / meta app-version
- versions.json, CHANGELOG, README, PROJECT_STATUS
- colab_worker_server.py, tests/test_version.py

## Prompt Studio (blurred / empty page) — FIXED
**Root cause:** CSS from `unified-v300.css` set `.ps-panel { transform: translateX(100%) }`.  
When Prompt Studio opened via `#helpModal`, the panel stayed off-screen; users only saw a blurred overlay.

**Fix:**
- High-specificity overrides in `prod-polish-v304.css` force the panel visible, centered, no transform
- `toggleHelpModal` / `closePromptStudio` explicitly clear transform and leftover overlays
- Closing never leaves a permanent dim on the page

## Production hardening (from 3.2.0 review)
- WEB_WORKERS default **1**
- CORS_ORIGINS separate env; ALLOWED_HOSTS=* **fatal** in production
- Password min length **10**
- Refresh endpoint rate-limited
- Payment plan/amount server-authoritative
- Chat errors do not leak exception text
- YouTube URLs restricted to YouTube domains
- Public `/health` simplified
- KaTeX math rendering
- Safer API-key form (DOM `.value` assignment)

## Deploy
```env
ALLOWED_HOSTS=your-domain.com,healthcheck.railway.app
CORS_ORIGINS=https://your-domain.com
WEB_WORKERS=1
SECRET_KEY=<32+ random chars>
```
Hard-refresh browser after deploy (`Ctrl+Shift+R`).
