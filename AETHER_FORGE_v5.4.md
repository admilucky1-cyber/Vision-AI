# Vision AI v5.4.0 — Aether Forge

## Implemented

| Feature | Detail |
|--------|--------|
| **Plugin API** | Hooks: `pre_ingest`, `tokenize`, `ocr_parse`, `post_chunk`, `pre_search` — `GET /api/forge/plugins` |
| **Vector compaction** | Dedup + LRU prune — `POST /api/forge/compact` |
| **Query expansion** | Synonyms + sub-questions before hybrid search — `/api/forge/expand`, `/api/forge/search` |
| **PII redactor** | Scrubs keys, emails, paths, IPs in chat path + `POST /api/forge/redact` |
| **Token cost tracker** | Local simulator per thread/profile — `GET /api/forge/cost` |
| **Math CAS** | sympy simplify/solve when installed — `POST /api/forge/math` · UI **∑** |
| **Memory graph** | SQLite entities/edges + canvas map — `/api/forge/graph` · **Graph** |
| **Exec history API** | JSONL timeline — `/api/forge/exec-history` |
| **Web fallback** | Optional DDG/html or `services.search` — `POST /api/forge/web-fallback` |
| **Diagnostics** | Sandbox, expand, PII, RAG health, routing checks — `GET /api/forge/diagnostics` |
| **Profiler** | Local embed+sandbox microbench — `GET /api/forge/profiler` |
| **Workbench** | Side markdown editor + save — **WB** / `Ctrl+Shift+W` |
| **Prompt variables** | `{date}`, `{time}`, `{code}`, `{file}` auto-inject on blur |

## Partial / not full

- **mDNS LAN sync** — not implemented (security + platform complexity); use vault backup + config pack instead
- **Full pytest suite runner** — diagnostics endpoint is a lightweight harness, not a CI matrix
- **OCR plugins** — hook exists; ship your own `ocr_parse` callable via `plugin_api.register`

## Run
```bash
unzip VISION_AI_v5.4.0_AETHER_FORGE.zip -d vision-ai
cd vision-ai
python -m pip install -r requirements.txt
# optional CAS:
python -m pip install sympy
python run.py
```
