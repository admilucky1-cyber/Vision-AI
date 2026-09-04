# Push Vision AI to GitHub

## 1. Prepare (never commit secrets)

```bash
# Confirm these are ignored
cat .gitignore | grep -E "env|cookies"

# Create repo on github.com, then:
git init
git add .
git status   # .env and cookies.txt must NOT appear
git commit -m "Vision AI v2.0 production"
git branch -M main
git remote add origin https://github.com/YOUR_USER/vision-ai.git
git push -u origin main
```

## 2. Local run

```bash
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SECRET_KEY + GOOGLE_API_KEY or GROQ_API_KEY
python main.py
```

## 3. Railway

- New project → Deploy from GitHub
- Builder: **Dockerfile**
- Set env vars in Railway UI (not in git)

## 4. Health checks

- `/health`
- `/upload/health`
