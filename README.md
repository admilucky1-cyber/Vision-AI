# Vision AI

Multi-provider AI chat, document search, and a Model Studio with optional GPU workers.
The running version comes from `VERSION`; check `/api/version` after deployment.

## Run

Use Python 3.12. Copy `.env.example` to `.env`, set a random `SECRET_KEY`, and
configure at least one provider key. Keep keys out of Git.

```sh
python -m pip install -r requirements-railway.txt
python run.py
```

This installs the API without local embedding models. For document vector search,
install the CPU PyTorch wheel, `sentence-transformers`, and `chromadb`. The
Dockerfile installs the full dependencies. GPU Studio jobs require a connected worker.

## Verify

```sh
python -m pip install pytest matplotlib 'chromadb>=1,<2'
python -m pytest -q
```

The suite covers login, settings, short replies, file context, optimizer autosave,
health probes, and real Chroma insert/query/reopen with a deterministic test encoder.
It uses a temporary database and needs no production credentials or model download.
GitHub Actions runs the suite on pull requests and pushes to `main`.

## Railway

- Deploy the Dockerfile with `python run.py`; the process binds Railway's `PORT`.
- Use `/health` for startup probes and `/health/ready` for database readiness.
- `/api/version` must match `VERSION`; HTTP 200 alone does not prove AI providers work.
- Set `GEMINI_MODEL` to a model enabled for your Google account. The default is
  `gemini-3.6-flash`, which replaced a rejected model in this deployment.
- Provider HTTP 401 means the key must be replaced; 402 usually needs account credit.
  Another model cannot repair expired credentials or missing funds.
- Preserve databases, uploads, and vector data with persistent storage before
  relying on them across redeploys. Review the paths in your deployment settings.

## v8.1.4 repair

Completes the chat, upload, optimizer, shutdown, and health-probe fixes missing
from the partial v8.1.3 deployment. Repairs Chroma's embedding interface and a
long-document chunking loop. Adds configurable Gemini routing, fewer retries on
rejected provider credentials, and an accessible single-column account form.

Provider accounts and GPU availability still require live verification. This
release does not claim a measured uptime, coverage percentage, or security audit.

References: [Chroma embedding functions](https://docs.trychroma.com/docs/embeddings/embedding-functions),
[Gemini 3.6 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash).
