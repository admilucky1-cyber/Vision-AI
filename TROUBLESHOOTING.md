# Troubleshooting flowchart

## Chat timeout
1. Select **Groq** in model menu (faster free tier)
2. Shorten message / split PDF questions
3. If image/graph: wait for Colab Boost warm (`[status] Ready`)
4. Retry once after 10s

## Graph not appearing (I–V / plot)
1. Phrase: `create graph between current and voltage`
2. Confirm matplotlib on server (`pip show matplotlib`)
3. Check response `images[]` not empty in Network tab
4. Hard refresh (`Ctrl+Shift+R`)

## Image empty / vague
1. Boost tab open + GPU runtime
2. HF_TOKEN / worker registered on `/boost`
3. Prefer photo prompts for mosques; graph prompts for plots

## Drive mount
1. Same Google account as Colab
2. Allow popup → `/content/drive/MyDrive/vision_ai_models`
3. Restart runtime after adding Secrets

## Theme / UI
1. Hard refresh
2. `localStorage` theme: dark/light
3. Preset: `applyThemePreset('nord')` in console

## Colab SyntaxError `__future__`
- File must start: docstring → `from __future__ import annotations` → imports
- Pull latest `colab_one_click_boost.py` and Restart runtime

## 403 YouTube download
- Use server download path; add cookies.txt only privately (never commit)


## Exam PDF invents questions / ignores the paper

0. Prefer **attach PDF + type solve in the same message**, or follow with `solve this pdf` / `solve` within ~1 hour (same login/guest session).
1. Confirm version **3.1.0+** (Settings → About or `/api/version`)
2. Logs should show: `RAG skip (full-document intent) → keeping N chars` with N ≫ 12000
3. Filename tags help: `-que-`, `_qp_`, `question` → QUESTION PAPER
4. Message: `solve this pdf` or `answer all` (not only a vague “help”)
5. Docker image already has tesseract + poppler; local Windows needs Tesseract on PATH
6. If extract is cover-only, check logs for `PDF extract quality` score and OCR fallback
7. Never rely on older builds before 3.1.0 for full-paper solve

## Guest “Could not validate credentials”
- Fixed in 3.0.9+: guests are not looked up in user_db
- Hard refresh / clear site data if an old JWT remains


## Follow-up solve lost the PDF (multi-worker)
- v3.1.3+ stores uploads under `data/rag_cache/` (shared across workers)
- Ensure the Railway volume/container keeps `/app/data` writable
- Same user/guest session within 1 hour


## Cache still empty after upload
- Hard refresh once so `vision_ai_client_id` is set in localStorage
- Stay on the same browser profile; do not clear site data between upload and solve
- v3.1.4+ sends `X-Vision-Client-Id` on every chat request
