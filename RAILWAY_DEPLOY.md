# Railway deploy — Vision AI v3.0.5

**Why production still said v3.0.3:** Railway is connected to GitHub `admilucky1-cyber/Vision-AI-v2` branch **main**. Uploading a zip in chat or elsewhere does **not** change that repo. You must push these files to `main`, then Railway auto-deploys.

```bash
# On your PC, extract VISION-AI-v3.0.5-FINAL.zip into the repo folder
cd Vision-AI-v2   # your local clone of admilucky1-cyber/Vision-AI-v2
# copy extracted files over (or unzip -o into the repo root)
git add -A
git status   # confirm VERSION shows 3.0.5 and frontend/index.html title is v3.0.5
git commit -m "Vision AI v3.0.5 — UI polish, About, free models, identity"
git push origin main
```

After deploy succeeds, hard-refresh the app (Ctrl+Shift+R). Tab title must read **Vision AI v3.0.5 — Chat**. Settings → About shows live `/api/version`.

Quick check: open `https://vision-ai-v2-production.up.railway.app/api/version` — JSON `"version":"3.0.5"`.

---
# Railway deploy — why you still see v2.9.2

## What we verified
- **GitHub `main`**: `VERSION` = **3.0.1**
- **Live Railway** (`/health`): **version 2.9.2**, uptime ~12h
- That means: code may be on GitHub, but Railway **did not replace** the running replica (build failed, or redeploy never ran).

Railway keeps the **last successful** deployment when a new build fails.

## Fix (do this in order)

### 1) Confirm GitHub has the full tree
On your PC, in the project folder that contains `VERSION` = 3.0.1:

```powershell
git status
git add -A
git commit -m "Vision AI v3.0.1 — auth guest fix, agent, deploy harden"
git push origin main
```

If `git status` is clean and remote already has the commit, skip commit.

### 2) Open Railway → your service → **Deployments**
- Click the **latest** deployment (not the green Active v2.9.2).
- Open **Build logs** / **Deploy logs**.
- Look for red errors (`ModuleNotFoundError`, `Healthcheck failed`, `pip`, etc.).

### 3) Force a new deploy
Railway → service → **Settings** → **Redeploy**  
or Deployments → **⋯** → **Redeploy**.

### 4) After success, verify
```text
https://vision-ai-v2-production.up.railway.app/health
```
Must show `"version":"3.0.1"`.

Guest:
```text
POST /auth/guest
```
Must return a JSON token (not 405).

### 5) Hard refresh the browser
`Ctrl+Shift+R` on `/login.html` and `/`.

## Common failure causes
| Symptom | Fix |
|---------|-----|
| Healthcheck failed | App crashed on import — check Deploy logs |
| Build OK, still old version | Wrong service / branch — Source must be `main` |
| Only README changed | Push **all** files, not only docs |
| Out of memory on build | Dockerfile build is heavy; retry or reduce apt packages |

## Required env (Railway Variables)
Keep existing keys. Ensure at least:
- `SECRET_KEY`
- `ALLOW_GUEST=1`
- One LLM key (`GROQ_API_KEY` or `GOOGLE_API_KEY` or `OPENROUTER_API_KEY`)
