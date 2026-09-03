# Permanent-as-possible free setup (Vision AI)

## Honest limits

| Goal | Reality |
|------|---------|
| Free **website** 24/7 | Possible with free tiers + keep-alive pings |
| Free **GPU** forever (Colab/Kaggle) | **Not allowed** — sessions idle-kill; ToS forbids abuse bots |
| Better quality when online | Colab + Kaggle workers + API keys failover |

This project is built for the maximum free stack that still works.

---

## A) Permanent free website (pick one)

### 1. Render (easiest free web service)
1. Push repo to GitHub  
2. Render → New Web Service → connect repo  
3. Uses `render.yaml` / `Dockerfile`  
4. Free tier **sleeps** after ~15 min idle → fix with keep-alive below  

### 2. Railway
- `railway.toml` included  
- Free monthly credit; may require card on some accounts  

### 3. Fly.io
```bash
fly launch
fly deploy
```

### 4. Cloudflare
- **Pages**: static frontend only  
- **Workers**: limited CPU for full FastAPI — use as reverse proxy in front of Render  

**Recommended combo:** Render (API) + GitHub Actions keep-alive every 10 min.

---

## B) Keep-alive (free, no credit card)

### Option 1 — GitHub Actions (already in repo)
File: `.github/workflows/keep-alive.yml`

1. GitHub repo → **Settings → Secrets and variables → Actions**  
2. Add secret: `APP_URL` = `https://your-app.onrender.com`  
3. Optional: `WORKER_URLS` = `https://colab-ngrok...,https://kaggle-ngrok...`  
4. Actions tab → enable workflows  

Pings `/api/keep-alive` every 10 minutes.

### Option 2 — UptimeRobot (free)
1. https://uptimerobot.com (free account)  
2. Monitor type HTTP  
3. URL: `https://YOUR-APP/api/keep-alive`  
4. Interval: 5 minutes  

### Option 3 — cron-job.org
Same URL, every 5–10 minutes.

---

## C) Colab + Kaggle workers (better models/images)

Workers are **optional boosters**, not permanent GPUs.

```
.env on website:
COLAB_WORKER_URL=https://xxxx.ngrok-free.app
KAGGLE_WORKER_URL=https://yyyy.ngrok-free.app
WORKER_URLS=https://extra1...,https://extra2...
COLAB_WORKER_SECRET=vision-colab-secret
```

Website tries workers in order → then Groq/Gemini/OpenRouter/HF.

### Colab
1. GPU runtime  
2. Run `Vision_AI_Colab.ipynb` section 6 (worker)  
3. Copy ngrok URL → `COLAB_WORKER_URL`  
4. Keep tab open; re-run when session dies  

### Kaggle
1. New Kaggle Notebook → GPU  
2. Upload `colab_worker_server.py` (same file works)  
3. Install deps + run uvicorn + ngrok (or cloudflared)  
4. Paste URL → `KAGGLE_WORKER_URL`  

Kaggle sessions also end; rotate Colab ↔ Kaggle when one dies.

### Worker keep-alive tips (best-effort only)
- Ping `/worker/health` from GitHub Actions (`WORKER_URLS` secret)  
- Still **cannot** force Colab/Kaggle to stay forever  
- When dead: website continues on normal API keys  

---

## D) Always-on quality without GPU

Put at least one free API key in website `.env`:

```env
GROQ_API_KEY=          # strong free chat
GOOGLE_API_KEY=        # Gemini free tier
OPENROUTER_API_KEY=    # free models
HF_TOKEN=              # images when workers offline
```

This is the real “permanent” brain. Workers only upgrade quality while alive.

---

## E) Checklist

- [ ] App deployed (Render/Railway/Fly)  
- [ ] `APP_URL` secret for GitHub Actions **or** UptimeRobot monitor  
- [ ] At least one of: GROQ / GOOGLE / OPENROUTER key  
- [ ] Optional: Colab worker URL while you need GPU images  
- [ ] Optional: Kaggle worker as backup  
- [ ] Telegram notify for payments (`TELEGRAM_BOT_TOKEN` + `CHAT_ID`)  
- [ ] Never commit `.env`  

Status endpoints:
- `GET /api/keep-alive`  
- `GET /api/colab-status`  
- `GET /health`  

---

## F) What we will not claim

- Unlimited free GPU 24/7  
- Colab/Kaggle “never disconnect” (against their rules and technically unreliable)  
- Same quality as paid GPT-4o every time on free tiers  

We **do** claim: free host + free keep-alive + multi-worker failover + free API keys = usable permanent product for individuals.

---

## G) Auto-integrate Colab/Kaggle (no manual URL paste)

1. Deploy Vision AI (Render/Railway/Docker) — note public URL  
2. On website `.env` set once:
   ```env
   COLAB_WORKER_SECRET=vision-colab-secret
   ```
3. In Colab notebook **section 8**:
   - Set `MAIN_APP_URL=https://your-app.onrender.com`
   - Set same `WORKER_SECRET`
   - Run cell → ngrok starts → **auto-registers** with your app  
4. Website uses worker for chat + images automatically  
5. Check: `https://your-app/api/workers`

When Colab dies, app falls back to GROQ/Gemini/OpenRouter keys. Re-run section 8 to reconnect.
