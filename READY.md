# Vision AI v2.7.3 — Production ready checklist

## 1. Code
- [x] `services/llm.py` — `__future__` import first (Railway fix)
- [x] RAG re-ranker (`services/rag.py`)
- [x] Colab keep-alive + Drive cache
- [x] PKR plans + free message limits
- [x] Manual Easypaisa / bank upgrade flow

## 2. GitHub
```bash
git add .
# NEVER commit .env or cookies.txt
git commit -m "Vision AI v2.7.3 production ready"
git tag -a v2.7.3 -m "v2.7.3"
git push origin main --tags
```

## 3. Railway
- Redeploy from `main`
- Set env vars (SECRET_KEY, LLM keys, FREE_MESSAGES_*, EASYPAISA_*)
- Confirm `/health` returns 200

## 4. Colab (images)
- Runtime → GPU
- Run `colab_one_click_boost.py`
- Leave tab open for keep-alive

## 5. Smoke test
1. Login / guest chat (under free limit)
2. Upload a short PDF
3. Open `/upgrade.html` — prices in PKR
4. Optional: Boost + one image

## 6. Earn
See `MONETIZE.md`.

- [x] Guest public access + overlay UI fix (v2.7.3)
