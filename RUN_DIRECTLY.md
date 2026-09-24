# Vision AI v5.0.0 — Run Directly (No IDE / No Editor Required)

## Requirements
- Python 3.10+ (3.11 or 3.12 recommended)
- Internet (first time only, to install packages)

---

## Option 1 — Fastest (recommended)

```bash
# 1. Unzip
unzip VISION_AI_v5.0.0_AETHER_WORKSPACE.zip -d vision-ai
cd vision-ai

# 2. Install dependencies (once)
python -m pip install -r requirements.txt

# 3. Run
python run.py
```

Open browser: **http://127.0.0.1:5050**

Stop with `Ctrl + C`.

---

## Option 2 — Using start.sh

```bash
unzip VISION_AI_v5.0.0_AETHER_WORKSPACE.zip -d vision-ai
cd vision-ai
python -m pip install -r requirements.txt
chmod +x start.sh
./start.sh
```

---

## Option 3 — Custom port

```bash
PORT=8080 python run.py
```

Then open: **http://127.0.0.1:8080**

---

## Optional .env (API keys)

Copy example and edit only if you want your own keys:

```bash
cp .env.example .env
# then open .env in any text editor and add keys
```

Without keys the app still starts; some models may be limited.

---

## Health check

After start, open:
- http://127.0.0.1:5050/health
- http://127.0.0.1:5050/chat/ping

You should see `"version": "5.0.0"`.

---

## Notes
- No VS Code, Cursor, or any editor is required.
- Backend (FastAPI) serves the frontend automatically.
- Frontend + backend stay connected via the same process.
