# Vision AI v5.6.5 — Ship checklist

## Railway
- Start: `python run.py`
- Health: `/health`
- Variables: `SECRET_KEY` (32+ chars), `ALLOWED_HOSTS=*`
- Optional: `DATABASE_URL`, AI provider keys

## After deploy
1. Hard refresh
2. `/health` → version 5.6.5
3. Guest profile → Sign in
4. Login → Log out works
5. Settings opens; chat sends

## Local
```bash
pip install -r requirements.txt
python run.py
```
