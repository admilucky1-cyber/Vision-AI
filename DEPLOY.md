# Vision AI v2.0 — Deploy: GitHub → Railway → Docker

## 0. Local first

```bash
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill SECRET_KEY + at least one LLM key
# optional: cookies.txt + YTDLP_COOKIES=cookies.txt
python main.py
# http://localhost:5050
```

Never commit `.env` or `cookies.txt`.

---

## 1. GitHub

```bash
git init
git add .
git status   # confirm .env and cookies.txt are NOT listed
git commit -m "Vision AI v2.0 production"
# Create empty repo on github.com, then:
git branch -M main
git remote add origin https://github.com/YOUR_USER/vision-ai.git
git push -u origin main
```

If secrets were committed earlier: rotate keys and purge history.

---

## 2. Railway (recommended cloud)

1. [railway.app](https://railway.app) → New Project → **Deploy from GitHub** → select repo  
2. **Settings → Build**: Builder = **Dockerfile** (required for ffmpeg / YouTube)  
3. Variables (from `.env`, no quotes issues):

```text
SECRET_KEY=<long random>
DEBUG=false
HOST=0.0.0.0
PORT=5050
GOOGLE_API_KEY=...
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
DEEPSEEK_API_KEY=...
YTDLP_COOKIES=/app/cookies.txt
ALLOWED_HOSTS=your-app.up.railway.app
CORS_ORIGINS=https://your-app.up.railway.app
```

4. Upload `cookies.txt` via Railway volume or start command that copies a secret file  
5. Health: `https://YOUR_APP.up.railway.app/health`  
6. Upload health: `/upload/health` → `ytdlp_available` + `ffmpeg_available` true  

`railway.toml` in repo forces Dockerfile.

---

## 3. Docker (local or any VPS)

```bash
cp .env.example .env   # fill secrets
docker compose up --build -d
# http://localhost:5050
```

Image includes ffmpeg, tesseract, graphviz.

---

## 4. YouTube on cloud checklist

| Item | Required |
|------|----------|
| Dockerfile build | Yes |
| ffmpeg in image | Yes (Dockerfile) |
| Netscape cookies.txt | Yes when bot-blocked |
| YTDLP_COOKIES path | `/app/cookies.txt` |
| Direct links first | Default; server fallback if blocked |

---

## 5. Microphone

Only works on **https://** or **http://localhost**.  
Railway HTTPS URLs work; plain IP HTTP will show "permission denied".

---

## 6. Free LLM keys (no unlimited)

Groq → Gemini → OpenRouter `:free` → DeepSeek. See `FREE_AI_NOTES.md`.
