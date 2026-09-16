# Dependency pins (practical)
Install with: `pip install -r requirements.txt`
Critical runtime packages should stay compatible with Python 3.10–3.12.
Run `pip freeze > requirements.lock.txt` on a known-good deploy for exact pins.
CI runs pytest on each push (see `.github/workflows/ci.yml`).
Smoke: `python scripts/smoke_test.py`
Live health: `SMOKE_BASE_URL=https://your-app.up.railway.app python scripts/smoke_test.py`
