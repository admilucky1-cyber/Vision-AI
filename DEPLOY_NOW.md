# Vision AI v5.6.4 — Deploy now

## Railway
1. **Start command:** `python run.py`
2. **Health path:** `/health`
3. **Variables (required):**
   - `SECRET_KEY` = random 32+ characters
   - `ALLOWED_HOSTS=*`
4. **Optional:**
   - `DATABASE_URL=postgresql://...` (else SQLite file)
   - Provider keys: `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, etc.

## After deploy
1. Hard refresh (Ctrl+Shift+R)
2. Open `/health` → version **5.6.4**
3. Guest → profile → Sign in
4. Login → profile shows **Log out**
5. Settings → change theme → refresh → should stick if logged in
6. Chat send one message

## Local
```bash
pip install -r requirements.txt
python run.py
```
Open http://127.0.0.1:8080
