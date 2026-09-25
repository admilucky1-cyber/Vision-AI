# Vision AI v5.6.0 — Full workspace polish

## What "Route" and context mean
- **Route**: which model path handles the reply (`Auto (smart)` = free cascade).
- **Context meter**: estimated tokens used vs ~128k window for this thread.

## What this release does
- Single Nova design system on chat + secondary pages
- Shared `pages-shell.css` for Skills, Studio, Boost, Usage, Versions, Settings
- Real content cards on Skills / Boost / Usage / Versions
- Composer meta row styled (Route + Context)
- Fixed-width content containers app-wide

## Deploy
Push to Railway-linked repo. `ALLOWED_HOSTS=*` · Start: `python run.py`
