# Production Readiness Pass — Changelog

Full backend + frontend + deployment review. Issues are grouped by severity.
Every fix below was verified against the actual code (not assumed) and the
whole project was syntax-checked (Python `py_compile` + Node `--check`) after
every change.

---

## 🔴 Critical

### 1. Entire server froze during every AI chat response
**Where:** `routes/chat.py`
**What:** `ask_ai`, `search_web`, and `auto_search_context` are synchronous
functions that make real network calls (LLM providers, search engines), but
were called directly inside `async def chat_send` with no `await`/threading.
Under FastAPI + uvicorn, a blocking call inside an async handler freezes the
*entire event loop* — not just that one request. Every other user's request
(even unrelated health checks) would stall for the full duration of each
LLM/search call.
**Fix:** wrapped all three in `asyncio.to_thread(...)`, and added a hard 50s
timeout budget around the LLM call via `asyncio.wait_for` so a degraded
provider fails fast with a clear message instead of blocking indefinitely.

### 2. Diagram generation could freeze the server for minutes
**Where:** `services/image_gen.py`
**What:** `generate_with_hf` (the default diagram-image path whenever
`HF_TOKEN` is set) called `session.post(..., timeout=90)` — a blocking call —
directly inside an `async def`, up to twice per model across 3 fallback
models. Worst case: ~9 minutes of frozen event loop for one diagram request.
`search_real_image` (opt-in via `DIAGRAM_USE_GOOGLE`) had the same issue with
up to ~80s of blocking calls.
**Fix:** wrapped both in `asyncio.to_thread(...)`.

### 3. Any user could self-upgrade to Enterprise for free
**Where:** `routes/upgrade.py`, `frontend/static/js/upgrade.js`
**What:** `POST /upgrade/upgrade` granted *any* plan (Pro/Team/Enterprise)
instantly with no payment check — the code's own comment read *"For now, we
simulate a successful payment."* The frontend's plan-card "Upgrade" buttons
called this endpoint directly, bypassing the real payment system entirely.
**Fix:** the endpoint now rejects paid-plan requests with `402 Payment
Required` in production (allowed only when `DEBUG=true`, for local dev/testing
convenience). The frontend now routes paid-plan clicks to the real Easypaisa/
bank payment form instead of the fake instant-upgrade call.

### 4. The Easypaisa/bank payment form was completely non-functional
**Where:** `frontend/static/js/upgrade.js`, `frontend/upgrade.html`
**What:** `upgrade.html` references `onsubmit="return submitPayment(event)"`
and a `#paymentMethods` display area, but neither `submitPayment()` nor any
loader for payment methods existed anywhere in `upgrade.js`. The form was
dead on arrival — submitting it would throw `ReferenceError`.
**Fix:** implemented `loadPaymentMethods()` (populates Easypaisa/bank details
from `/upgrade/payment-info`) and `submitPayment()` (submits to
`/upgrade/payment-request` with proper validation, loading states, and error
handling), wired into page init.

---

## 🟠 High

### 5. Frontend/backend timeout mismatch caused false "timed out" errors
**Where:** `frontend/static/js/index.js`, `routes/chat.py`
**What:** the frontend hard-aborted chat requests at 60s. The backend's LLM
provider fallback chain (Gemini with no explicit timeout → DeepSeek 45s →
Groq 30s → OpenRouter up to 4 models × 30s) could legitimately exceed that,
so a request that was still genuinely working got cut off client-side and
shown to the user as a connection failure.
**Fix:** backend now enforces a 50s hard budget (see #1) with an honest
timeout message; frontend abort window widened to 75s for comfortable margin.

### 6. Missing system dependencies silently disabled OCR and diagrams
**Where:** `Dockerfile`
**What:** `pytesseract`, `pdf2image`, and `graphviz` (all in
`requirements.txt`) are thin Python wrappers around system binaries
(`tesseract-ocr`, `poppler-utils`, `graphviz`) that were never installed in
the image. Scanned-PDF OCR failed silently (debug-level log only, no error
surfaced), and flowchart/org-chart diagrams silently disabled themselves.
**Fix:** added `tesseract-ocr`, `poppler-utils`, `graphviz` to the Dockerfile's
apt install step. Also documented in `render.yaml` that Render's native
Python runtime *can't* install these — Docker deploy is required for full
OCR/diagram functionality.

---

## 🟡 Medium

### 7. Admin check inconsistency
**Where:** `routes/login.py` — `GET /auth/users`
**What:** checked only `username == "admin"` literally, ignoring the `role`
field. Every other admin-gated route in the app correctly checks
`role == "admin" OR username == "admin"`. An admin seeded via
`ADMIN_USERNAME=something_else` would fail this one check while passing
every other admin check in the app.
**Fix:** aligned with the pattern used everywhere else.

### 8. Wrong plan shown briefly after login
**Where:** `frontend/static/js/login.js`
**What:** every login hardcoded `vision_ai_plan` to `'Free'` regardless of
the user's actual plan (the `/auth/login` response never included plan data).
Paid users would see a flash of "Free"/upgrade UI immediately after logging
in, until `index.js`'s `checkAuth()` corrected it moments later via
`/auth/me`.
**Fix:** removed the incorrect hardcode from the login and Google-OAuth-kickoff
paths (kept it at registration, where "Free" really is correct for new
accounts) so `checkAuth()` is the single source of truth.

### 9. `attempted_models` scoping bug
**Where:** `services/image_gen.py` — `generate_with_hf`
**What:** `attempted_models = []` was re-initialized inside the retry loop,
so the final error response only ever reported the *last* attempted model
instead of all of them, and could raise `NameError` if the loop range were
empty.
**Fix:** moved the initialization outside the loop.

### 10. Deploy config inconsistencies
**Where:** `Procfile`, `Caddyfile`, `.env.example`
**What:** `Procfile`/`Caddyfile` defaulted to port `8000` while every other
config in the repo (`main.py`, `Dockerfile`, `.env.example`) defaults to
`5050` — self-consistent but confusing. `REDIS_URL` (a real, working optional
feature in `services/search.py`) wasn't documented in `.env.example`.
**Fix:** aligned all ports to `5050`; documented `REDIS_URL`.

---

## Already fixed in a prior session (verified still intact, not re-done)
- Admin search-dashboard auth wiring (`/admin/search/*` routes + frontend
  token-aware fetch)
- Theme-switch CSS transition consolidation (42 → ~25 rules, one fast global
  transition)
- Cache-busting version alignment across all pages (`?v=7`)
- Render-blocking CDN scripts deferred on the chat page

## Known, not fixed (flagged for awareness, out of scope for this pass)
- `services/vector_store.py` and `services/flux_image.py` are complete but
  entirely unused — not imported anywhere in the live app. Not a bug, but
  worth knowing they don't currently do anything.
- Some frontend `authedFetch` call sites elsewhere in the app return
  `undefined`/`null` on missing token and the caller doesn't always guard
  before immediately calling `.json()` on the result — caught by surrounding
  `try/catch` so it degrades to a generic error message rather than crashing,
  but the messaging isn't as precise as it could be. Low severity since
  every such page already gates on a valid token at page-init time.
