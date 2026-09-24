# Vision AI — Build: Web · App · EXE

## 1) Web (Railway / Docker) — primary
```bash
# Deploy zip root with Dockerfile
# Railway: New Project → Deploy from local / GitHub → set env vars
# Required: SECRET_KEY, SESSION_SECRET, at least one LLM key
# Health: GET /health  and  GET /health/ready
```
Open: `https://YOUR-APP.up.railway.app`

## 2) Installable App (PWA — phones & desktop)
1. Open site in Chrome / Edge / Safari
2. Menu → **Install app** / Add to Home Screen
3. `manifest.webmanifest` already has `display: standalone`
Works offline for shell; chat needs network.

## 3) Windows EXE (optional packaging)
Not a native compiled binary in-repo. Practical options:
- **PWA** (recommended): install from browser — no separate EXE build
- **Tauri / Electron wrapper** (advanced): point WebView at production URL or local `run.py`
- Local server:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
# open http://127.0.0.1:8080
```

## Cross-device
CSS: device-fit, browser-safe-layout, column-structure, fluid `clamp()` type.
Touch: gestures + 44px targets + safe-area insets.

## Data Lab formats
| Format | Support |
|--------|---------|
| CSV / TSV / TXT | Yes |
| Excel .xlsx / .xls | Yes (all sheets) |
| PDF | Text → table (pypdf) |
| JSON | Yes |
| PPTX | Text + tables → rows (python-pptx) |
| Dashboard JSON | `/api/data-lab/datasets/{id}/dashboard` |
| Clean / query / forecast / train | Yes (in-app, not a full Power BI replacement) |

Honest scope: excellent multi-file **tabular + extract** workflows inside Vision AI.
Power BI remains stronger for enterprise live connectors & advanced viz; Vision AI focuses on AI + multi-file speed in one product.
