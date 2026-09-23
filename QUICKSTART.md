# Vision AI v2.0 — Quick Deploy

## A) Run on your PC (5 minutes)

```bash
# 1. Unzip and enter folder
cd vision-ai   # or your folder name

# 2. Virtual env
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# 3. Install
pip install -r requirements.txt
pip install -U yt-dlp ddgs

# 4. Config
copy .env.example .env     # Windows
# cp .env.example .env     # Mac/Linux

# Edit .env — MINIMUM:
#   SECRET_KEY=<long random string>
#   GOOGLE_API_KEY=...   OR   GROQ_API_KEY=...
# Optional: OPENROUTER_API_KEY, DEEPSEEK_API_KEY, HF_TOKEN
# Optional YouTube: YTDLP_COOKIES=cookies.txt

# Generate SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 5. Start
python main.py
# Open http://localhost:5050
```

## B) Push to GitHub

```bash
git init
git add .
git status
# Must NOT list: .env  cookies.txt  data/users.json
git commit -m "Vision AI v2.0 production"
git branch -M main
git remote add origin https://github.com/YOUR_USER/vision-ai.git
git push -u origin main
```

## C) Deploy on Railway

1. railway.app → New Project → Deploy from GitHub
2. Settings → Build → **Dockerfile** (required for ffmpeg / YouTube)
3. Variables tab — paste from .env (never commit .env):
   - SECRET_KEY
   - GOOGLE_API_KEY or GROQ_API_KEY
   - HOST=0.0.0.0
   - PORT=5050
   - DEBUG=false
   - ALLOWED_HOSTS=your-app.up.railway.app
   - CORS_ORIGINS=https://your-app.up.railway.app
4. Open the public URL → /health

## D) Docker local

```bash
docker compose up --build -d
# http://localhost:5050
```

## Features included

| Feature | How to use |
|---------|------------|
| Chat (multi-LLM) | Type message, pick model or Auto |
| PDF / exam solve | Attach PDF + "Solve step by step" |
| Image Q&A | Attach image + ask |
| YouTube summary / quiz | Paste link + prompt |
| YouTube download | "download video/mp3 [url]" |
| Prompt Studio | Top bar **Prompts** or Ctrl+K |
| Plans / Easypaisa | Top bar **Plans** |
| Search cache (admin) | Top bar **Cache** |
| Stop generation | ⏹ while loading |
| Speak | 🔊 on a message |
| Voice input | Mic on **localhost** or HTTPS only |
| Theme | Top bar moon/sun |
| Focus / fullscreen | Top bar expand icon |

## Mic & Speak

- Mic: only `http://localhost:5050` or HTTPS → lock → allow Microphone
- Speak: works on message bubbles; Urdu needs OS Urdu voice

## Do not commit

.env, cookies.txt, venv/, data/users.json, downloads/


## YouTube downloads (important)

Use normal download commands — files are saved on **your app domain** and open in the browser:

```
download video 720p https://youtu.be/VIDEO_ID
download audio mp3 https://youtu.be/VIDEO_ID
```

Do **not** rely on googlevideo.com direct links (they return 403 in browsers).
