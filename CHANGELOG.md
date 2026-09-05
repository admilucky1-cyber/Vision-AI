# Vision AI Changelog

## 5.7.1 — 2026-09-05
- Stabilized the Sketch Shell package as the canonical 5.7.1 release.
- Synchronized frontend version metadata and asset cache-busting to `571`.
- Fixed missing canonical CSS wiring on the main chat page.
- Removed duplicate HTML attributes and stale version references.
- Aligned the version registry with the `VERSION` file.
- Updated the automated UI tests to validate the current Nova architecture rather than retired CSS layers.
- Verified Python AST/bytecode compilation and JavaScript syntax; full pytest suite passes after the fixes.

## 4.9.4 — 2026-08-21
- Fix Appearance/theme presets: map `--accent` → `--color-accent` (themes were not visibly applying)
- applyTheme / applyThemePreset always update data-theme + force accent sync
- Composer: hide Stop unless generating; single-shell flex layout
- Theme picker panel z-index + selected states
- Production hard-refresh cache bust v=494

## 4.9.3 — 2026-08-21
- Cross-platform responsive hardening (desktop / tablet / phone / Android / iOS)
- Safe-area insets for notched devices and gesture bars
- 16px inputs on ≤900px to prevent iOS zoom-on-focus
- 100dvh + touch overflow; landscape phone denser layout
- Coarse-pointer 44px targets; 360px / 1440px / 1920px refinements
- Sidebar JS boundary unchanged (≤900 drawer / ≥901 desktop)

## 4.9.2 — 2026-08-21
- Chat shell precision: header, stream max-width, composer bounds, touch targets
- Profile dropdown sizing + menu item hit areas
- Settings: tokenized cards (remove inline glass), two-column layout + nav, responsive stack ≤900
- New `ui-refine.css` loaded last (does not change 900/901 sidebar JS)
- Token aliases complete for workspace-ui variables
- Demote Clear caches control density

## 4.9.1 — 2026-08-21
- Fix token drift for workspace-ui.css without replacing tokens.css
- Aliases: --color-bg-secondary/tertiary, --color-text-secondary/tertiary, --color-accent-light/text
- Preserve full token scale (space, radius, type, motion, legacy style.css aliases)
- Do **not** overwrite tokens.css with a minimal palette-only file

## 4.9.0 — 2026-08-21
- **Modern Workspace UI**: new workspace-ui.css layer for premium chat interface
- **Hero Composer**: focused, centered input with multimodal attachment support
- **Workspace-Style Messages**: professional message rendering (not bubbles) with code, formulas, media
- **Modern Sidebar**: simplified navigation with brand, recent chats, workspace shortcuts
- **Profile Menu**: premium account/workspace dropdown interface
- **Settings UI**: modern preferences layout with organized sections and toggles
- Sidebar controller architecture consolidated (removed redundant function exports)
- All 23 tests passing; 100% backward compatible
- Version meta tags updated; workspace-ui.css loaded in CSS cascade

## 4.8.3 — 2026-08-21
- Design system cleanup (no backend changes)
- Self-host Marked, DOMPurify, KaTeX under `frontend/static/vendor/`
- Migrate modern-ui component rules → components.css / chat.css / layout.css
- Slim modern-ui.css to residual bridge only
- tokens.css remains authoritative (+ temporary legacy aliases)
- Keep 900/901 sidebar state machine untouched

## 4.8.2 — 2026-08-20
- tokens.css is canonical design system; legacy CSS variables aliased to tokens
- style.css: removed global `* { transition }`; interactive-only transitions; stop redeclaring color palette
- Runtime HTML version → 4.8.2 (fixed stale 4.7.1 meta/title)
- Demote “Clear caches” visual weight in sidebar
- No backend API changes

## 4.8.1 — 2026-08-20
- Complete modern UI layer on frozen backend
- Chat empty state: Vision AI hero + suggestion chips (wired to composer)
- Composer: `composer-shell` (no glass-composer)
- Settings: two-column layout + section nav (responsive stacks ≤900)
- Studio + Upgrade: tokens + modern-ui, studio-page polish
- Preserves 900/901 sidebar controller and v4.7.6 architecture

## 4.8.0 — 2026-08-20
- Frontend design-system layer (no backend API changes)
- New `tokens.css` scale + semantic surfaces
- New `modern-ui.css`: clean surfaces, restrained glass, button system, composer, profile, empty state
- Preserves sidebar 900/901 controller and all v4.7.6 architecture fixes
- CSS cache-bust `?v=480`

## 4.7.6 — 2026-08-20
- Stabilization: single sidebar state machine (`window.__vaSidebar` + one controller)
- Removed recursive/duplicate early `toggleSidebar` implementation
- Desktop collapse logic lives only inside visionSidebarController
- Canonical auth tokens via VisionAuth (`vision_ai_access_token` / refresh); legacy keys migrated
- Settings logout is VisionAuth-only (no second implementation)
- Tests: sidebar single API + auth canonical keys

## 4.7.5 — 2026-08-20
- Drive/LoRA: `services/drive_state.py` with explicit states (DRIVE_UNAVAILABLE, LORA_MISSING, …)
- Worker validates LoRA path/extension/size; resolves under `vision_ai_models/loras/`
- Studio payload uses validated `lora_path`; rejects path traversal
- Worker `GET /worker/drive` readiness endpoint
- Smoke tests: imports, VERSION 4.x, path traversal rejection

## 4.7.4 — 2026-08-20
- P1: ProfileController — no inline onclick; click/keyboard/outside/Escape handled in one place
- P1: Mobile sidebar toggle/close/forceOpenSearch route through openSidebar/closeSidebar/toggleSidebar
- P1: Model migrations prefer `/api/models` (local map is fallback only)
- a11y: aria-expanded on profile trigger

## 4.7.3 — 2026-08-20
- P1: Shared `frontend/static/js/auth.js` — single logout/token-clear path for index + settings
- P1: Sidebar controller exposes `openSidebar` / `closeSidebar` / `toggleSidebar`; `forceOpenSearch` uses controller
- P1: `/api/models` includes `migrations` + `shutdown` (backend authoritative)
- Cache-bust auth/index/settings scripts

## 4.7.2 — 2026-08-20
- P0: Fix `routes/upload.py` — `__future__` import order + duplicate `Depends`
- P0: Align tests with v4.x (VERSION series, theme CSS paths)
- Restore `eye-care.css` / `theme-presets.css` compatibility for theme tests
- Version bump across package to 4.7.2
- Stabilization pass (no broad UI rewrite)

## 3.6.0 — 2026-08-13 SECURITY

- Admin: role-only (username `admin` no longer grants access); reserved usernames on register
- Skills: server-side Python install disabled (501)
- Workers: registration/secret fail-closed; URL SSRF checks
- LLM: custom API keys no longer mutate globals (no cross-user leak)
- OpenAI-compat base URL SSRF blocked by default
- Public `/downloads` mount removed
- Download history auth; cleanup admin-only
- Stripe webhook requires signature secret
- Quota: atomic reserve(); plan expiration via get_effective_plan
- Streaming: DOMPurify + 50ms render throttle
- Clear-cache scoped to user; admin-only global search clear
- WEB_WORKERS default 1; no prompt content in logs

## 3.5.0 — 2026-08-13

- Streaming chat (`POST /chat/stream`) for light text turns
- Progressive token display in the UI (markdown + KaTeX live)
- Automatic fallback to classic `/chat/send` for files/exams/images

## 3.4.0 — 2026-08-13

- Guest: 1 free reply / day (IP ledger) then sign-in required
- Free logged-in: 10 messages then upgrade (server-side, fail-closed)
- Quota ledger in data/quota_ledger.json — not bypassable from browser
- Clear 401/402 chat messages + redirect to login/plans
- Response quality prompt tightened

## 3.3.1 — 2026-08-13

- UI upgrade: Inter typography, depth background, glass composer glow
- Message bubbles refined (user gradient, AI glass cards)
- Sidebar / header / actions visual polish

## 3.3.0 — 2026-08-13

- Performance CSS: app-shell layout, content-visibility, touch targets, safe-area
- Static assets: 7-day immutable Cache-Control
- Chat budgets tightened for light turns (35s default)
- Resize debounce, scrollChatToBottom via rAF, route prefetch

## 3.2.8 — 2026-08-13

- Mobile video download: same-tab `location.assign` + `?dl=1` stamped on links
- Media download: Facebook, Instagram, TikTok, X/Twitter, Vimeo (via yt-dlp)
- Large CSV/Excel/PPT: sample rows/slides so big files don't crash context

## 3.2.7 — 2026-08-13

- **Plugged** YouTube download links in chat with `?dl=1` (mobile save)
- **Plugged** Colab image path: 512x512, 4 steps from Railway → worker
- **Plugged** `generate_images_batch` client for `/worker/batch_image`

## 3.2.6 — 2026-08-12

- Mobile download: synchronous `window.location.assign(?dl=1)` (no blob, keeps user gesture)
- Server always serves downloads as attachment + application/octet-stream
- nixpacks.toml installs ffmpeg when not using Docker
- RAILWAY.md: force Builder = Dockerfile

## 3.2.5 — 2026-08-12

- KaTeX: pre-render $$ math before markdown (fixes raw LaTeX in chat)
- yt-dlp: --no-config so Railway never hits Chrome cookie DB errors
- Admin-only Cache/Pay chips; desktop tool chips hidden on mobile
- Message bubbles: no nested vertical scrollbar

## 3.2.4 — 2026-08-12

- Mobile composer: cleaner bottom bar; free-tier strip hidden on small screens
- Sidebar width capped (~240–280px); response max-width 850px + RTL support
- Prompt Studio expanded (Study, Image, more exam/code/writing prompts)
- English forced for mostly-Latin STEM questions (e.g. quantum tunneling…)
- Simple Urdu vocabulary guidance (طریقہ not پدھتی); no foreign scripts

## 3.2.3 — 2026-08-12

- **Mobile YouTube download fix**: no longer loads 70MB into JS memory; uses direct attachment download
- Multi-key support: `GROQ_API_KEY_1`, `_2`, … or comma-separated keys with round-robin rotation
- Stronger anti-hallucination / no false wording; no mixed foreign scripts in Urdu answers
- Mobile shell polish (header, composer, touch targets, safe-area)

## 3.2.2 — 2026-08-12

- **Language default English** — no more random Urdu on English STEM questions
- Stricter Urdu detection (explicit request or clear Roman-Urdu phrases only)
- **Mobile YouTube download** — `?dl=1` + blob/octet-stream force save
- Math fences ````math` normalized to `$$` for KaTeX
- Professional chat typography (headings, lists, tables, KaTeX spacing)
- Mobile responsive polish for bubbles, actions, safe-area

## 3.2.1 — 2026-08-12

- Production hardening (workers=1, CORS_ORIGINS, ALLOWED_HOSTS fatal in prod)
- Password min length 10; refresh rate limit; payment plan/amount hardening
- KaTeX math rendering in chat
- **Prompt Studio fix**: panel no longer stays off-screen / blurred empty page
- Version alignment across VERSION, main.py, pyproject, frontend, tests
- Safer API-key form (DOM assignment, not HTML interpolation)
- YouTube URL domain restriction; simplified public /health

## 3.2.0 — 2026-08-12 (production hardening patch)

- **Complete exam-solve release** (consolidates 3.1.0–3.1.6)
- `services/rag_cache.py`: shared disk cache module (clean imports, multi-worker)
- Expanded smoke tests: full-doc intent, disk cache, session key, doc timeouts
- `COMPLETE.md` deploy checklist
- Env: `DOC_PROVIDER_TIMEOUT`, `DOC_MAX_TOKENS`, `PDF_OCR_MAX_PAGES`
- **Production fixes applied** (see `PRODUCTION_FIXES_v3.2.0.md`):
  - WEB_WORKERS default 1; CORS_ORIGINS; ALLOWED_HOSTS=* fatal in prod
  - Password min 10; refresh rate limit; payment plan/amount hardening
  - KaTeX math rendering; safer API-key form; YouTube domain checks
  - Public /health simplified; version test fixed for 3.x

### Included reliability stack
- Full ordered paper context (no invent)
- Follow-up solve reuses upload
- Multi-worker disk cache + stable client id
- Guest IP / refresh fixes
- Long client & provider timeouts
- Document-used toast + larger completions

## 3.1.6 — 2026-08-12

- **Best-of-bests exam reliability polish**
  - `rag_files_loaded` counts **reused cache papers** (was always 0 on follow-up solve)
  - Larger completion size on document context (`DOC_MAX_TOKENS`, default 8192)
  - Toast shows **document context used** when paper is in the request
  - Solve inject: never invent questions; quote real Q numbers from context
- Builds on 3.1.0–3.1.5: full context, follow-up reuse, disk multi-worker cache, stable client id, long timeouts

## 3.1.5 — 2026-08-12

- **Client timeout:** follow-up `solve this pdf` / exam phrases use 5‑minute browser timeout (was 90s without files)
- **Provider timeouts:** document context uses up to 120s per model (was 24–28s — too short for full papers)
- Server document budget 180s; clearer timeout guidance (solve by question range if needed)
- Prior: stable client id (3.1.4), disk multi-worker cache (3.1.3)

## 3.1.4 — 2026-08-12

- **Stable exam session:** browser `X-Vision-Client-Id` (localStorage UUID) keys the RAG cache so upload → solve works even when guest JWT/IP varies
- Guest IP uses `X-Forwarded-For` / `X-Real-IP` behind Railway
- Guest token **refresh** no longer fails (guests are not in user_db)
- Prior: disk multi-worker cache (3.1.3), follow-up solve phrases (3.1.2), full-doc RAG skip (3.1.0)

## 3.1.3 — 2026-08-12

- **Multi-worker exam fix:** RAG upload cache is **disk-backed** (`data/rag_cache/`) so Railway/uvicorn with 2+ workers still reuses the paper on follow-up “solve this pdf”
- Per-user isolation + 1h TTL preserved
- Prior: follow-up solve intents (3.1.2), full-document RAG skip (3.1.0)

## 3.1.2 — 2026-08-12

- **Best-fit exam flow:** follow-up messages (`solve this pdf`, `solve`, `answer all`, `this paper`…) **reuse the last uploaded document** for that user
- **Per-user RAG cache** (TTL 1h) so multi-tenant deploys do not mix papers
- Reused files keep QUESTION PAPER / MARK SCHEME tags from filename
- Bare `except` cleaned in upgrade plan expiry
- Prior 3.1.1 polish + 3.1.0 full-document RAG skip (no invented questions)

## 3.1.1 — 2026-08-12

- **Package polish:** README + TROUBLESHOOTING for exam PDF; clean `.env.example` (no duplicate OAuth keys; PDF/RAG notes)
- Smoke test covers full-document RAG skip intent
- Dockerfile label v3.1.1; frontend version strings aligned
- Prior 3.1.0: skip top-k RAG on “solve this pdf” so real questions are used

## 3.1.0 — 2026-08-11

- **CRITICAL fix — exam PDF hallucination:** "solve this pdf" no longer runs top-k RAG that collapsed ~50k-char papers to ~12k random chunks (model then invented generic questions).
- Full-document intent (`solve`, `answer all`, question-paper tags) keeps the ordered extract intact (up to ~100k chars) with smart question-body preference.
- System prompt: must quote real question numbers/stems from context; forbid inventing unrelated physics problems.
- Prior: guest JWT (3.0.9), exam extract quality (3.0.8), Colab-only images (3.0.7)

## 3.0.9 — 2026-08-11

- **CRITICAL:** Guest JWT no longer fails with "Could not validate credentials" (guests are not in user_db)
- **Chat reliability:** if Groq/OpenRouter/DeepSeek alone fails, soft-fallback to other free keys
- **Groq:** prefer `llama-3.1-8b-instant` first; better empty/HTTP logging
- Prior: exam PDF full context (3.0.8), Colab-only images (3.0.7), Prompt Studio unfreeze (3.0.6)

## 3.0.8 — 2026-08-11

- **Exam PDF solve:** context no longer truncated to cover page (~16k chars)
- **Smart truncate:** prioritizes pages with Q1/Q2… over front-matter
- **PDF extract:** PyMuPDF + best-of methods; quality gate triggers OCR when extract is cover-only
- **Auto route:** long question papers use Gemini first (1M context)
- **Solve mode:** explicit instruction to work through every question present

## 3.0.7 — 2026-08-11

- **Chat speed:** auto cascade is light/free first (Groq → OpenRouter free → DeepSeek → Gemini Flash); optional **Light / fast** menu item
- **Image gen:** Colab **downloaded models only** by default — never uses Gemini/Groq/OpenRouter chat keys for images; `IMAGE_ALLOW_CLOUD=1` to re-enable HF/Pollinations
- **Latency:** fewer free-model tries, tighter chat timeout (45s light / 90s heavy), skip Colab local LLM on auto chat
- **Roman Urdu:** electrical slang (e.g. current bund) interpreted correctly; blank model replies handled better

## 3.0.6 — 2026-08-11

- **Prompt Studio:** close always clears overlay, body overflow, and drawer classes (fixes frozen/dimmed chat)
- **No more CDN highlight.js:** self-hosted `hljs-lite.js` + `hljs-atom-one-dark.css` (fixes Tracking Prevention block)
- **prompt_studio.js:** no longer overwrites `closePromptStudio`; Escape + backdrop close reliably
- **CSS safety:** closed drawers have pointer-events:none so they cannot trap clicks

## 3.0.5 — 2026-08-11

- **Custom API keys:** Settings keys with override are sent on every chat (`X-Vision-Key-*`); server applies them for that request only (never logged)
- **Local LLM:** Ollama, LM Studio, and generic OpenAI-compatible base URL + model (env + Settings)
- **Model menu:** Auto / Groq / Gemini / OpenRouter / DeepSeek / Ollama / LM Studio / OpenAI-compat / Colab
- **Version headers:** every response includes `X-Vision-AI-Version` and `X-App-Version`
