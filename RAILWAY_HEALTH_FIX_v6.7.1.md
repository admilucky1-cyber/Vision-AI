# Railway healthcheck fix v6.7.1

## What failed
Docker **build succeeded**, but **`/health` never answered** within the retry window → `1/1 replicas never became healthy`.

## Why
1. `requirements.txt` pulls **torch + CUDA** stacks (huge RAM)
2. `vector_store.py` imported `sentence_transformers` / `chromadb` at **module import time**
3. Process could **OOM or hang** before uvicorn bound the port

## Fixes in this package
- Lazy-load vector/embedding deps
- Dockerfile installs **CPU torch** (no CUDA wheels)
- `railway.toml` healthcheckTimeout **600s**
- `run.py` forces **1 worker** on Railway + logs import errors
- `requirements-railway.txt` slim optional file

## Railway variables (required)
```
SECRET_KEY=<32+ random chars>
HOST=0.0.0.0
DEBUG=false
```
Plus at least one LLM key: `GOOGLE_API_KEY` or `GROQ_API_KEY` etc.

## After redeploy
Open: `https://YOUR-APP.up.railway.app/health`  
Expect: `{"status":"healthy","version":"6.7.1"}`
