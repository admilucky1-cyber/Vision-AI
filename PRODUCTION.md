# Vision AI v2.0 — Production Guide

## Checklist before going public

1. **Secrets**
   - Set `SECRET_KEY` to a long random string (≥32 chars). App **refuses to start** in production (`DEBUG=false`) with a weak/default key.
   - Set `SESSION_SECRET` independently if possible.
   - Never commit `.env`.

2. **Admin bootstrap** (optional)
   ```bash
   ADMIN_USERNAME=you
   ADMIN_PASSWORD='long-random-password'
   ADMIN_EMAIL=you@example.com
   ```
   First start creates that user once (persisted in `data/users.json`).

3. **AI keys** — at least one of: `GOOGLE_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`.

4. **Hosts**
   - `DEBUG=false`
   - `ALLOWED_HOSTS=your.domain.com,www.your.domain.com`

5. **Plan limits** — Free plan enforces `messages_per_month` (default 1000). Usage is stored per user.

6. **Disk** — Persist `data/`, `chroma_db/`, `uploads/`, `downloads/`, `logs/` (Docker volumes or Render disk).

---

## Deploy options

### Docker (recommended on a VPS)

```bash
cp .env.example .env   # fill secrets
docker compose up -d --build
curl https://your-host/health
```

### Render

1. Connect the GitHub repo.
2. Use `render.yaml` or set build/start commands from it.
3. Attach a disk mounted at the project `data/` path.
4. Set env vars in the dashboard.

### Bare metal / VPS

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DEBUG=false SECRET_KEY=... 
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

Put Nginx/Caddy in front with HTTPS.

---

## Security notes

| Item | Status |
|------|--------|
| JWT + bcrypt | Yes |
| Default admin in code | Removed — seed via env only |
| Docs (`/docs`) | Disabled when `DEBUG=false` |
| Rate limits | Chat / auth / upload |
| CORS | Tight when not DEBUG |
| Persistent users | `data/users.json` (single instance) |
| Multi-instance users | Use Postgres (next step) |

---

## Operational limits (free hosting)

- Cold starts on free PaaS
- yt-dlp / embedding models need RAM — prefer a small VPS for full features
- Cap free-tier messages so API bills stay controlled

---

## Post-deploy smoke test

```bash
curl -s https://YOUR_HOST/health
curl -s -X POST https://YOUR_HOST/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"demo","email":"demo@example.com","password":"secret12","full_name":"Demo"}'
```

Then open `https://YOUR_HOST/login.html` and send a chat message.

---

## Stripe setup (earn money)

1. Create products/prices in [Stripe Dashboard](https://dashboard.stripe.com).
2. Set env:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_PRICE_PRO` / `STRIPE_PRICE_TEAM` / `STRIPE_PRICE_ENTERPRISE`
   - `STRIPE_WEBHOOK_SECRET` (endpoint: `POST /upgrade/webhook/stripe`)
   - `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL`
3. Frontend or API: `POST /upgrade/checkout` with `{"plan":"pro"}` + Bearer token → opens `checkout_url`.
4. Webhook activates the plan after payment.

Without Stripe + `DEBUG=true`, checkout falls back to local upgrade for testing only.
