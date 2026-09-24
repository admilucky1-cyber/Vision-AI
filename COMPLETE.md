# Vision AI — Complete release checklist

**Version:** see `VERSION`  
**Package:** `VISION-AI-v3.2.0-FINAL.zip` (or matching VERSION)

## Exam PDF solve (done)

- [x] Full ordered context on “solve” (no top-k invent)
- [x] Follow-up “solve this pdf” reuses last upload
- [x] Disk cache across uvicorn workers (`data/rag_cache/`)
- [x] Stable `X-Vision-Client-Id` session
- [x] Guest IP + guest JWT refresh
- [x] Long timeouts (client / provider / server)
- [x] UI shows document context used
- [x] Larger completions for full papers

## Deploy

1. Unzip or push tree to GitHub `main` (`admilucky1-cyber/Vision-AI-v2`)
2. Never commit `.env` or `cookies.txt`
3. Railway: Dockerfile + secrets from `.env.example`
4. Hard-refresh browser after deploy
5. Test: upload past paper → **solve this pdf**
6. Logs should show `RAG skip (full-document intent)` and/or `Reusing previous upload`

## Local verify

```bash
pip install -r requirements.txt
cp .env.example .env   # add at least one LLM key
python scripts/smoke_test.py
python main.py
```

## Optional

- Colab Boost for images: `colab_one_click_boost.py`
- Custom keys / Ollama in Settings
- `IMAGE_ALLOW_CLOUD=0` (default) keeps images on Colab models only
