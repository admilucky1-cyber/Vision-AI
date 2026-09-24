# Vision AI v5.3.0 — Aether Lab

## Features

### 1. Agentic Execution + Self-Correction
- Restricted Python sandbox (no imports, no file/network, AST-gated)
- Iterative loop: run → catch error → heuristic and optional LLM repair → retry
- API: `POST /api/engine/agentic/run`
- UI: header **Agent** or `Ctrl+Shift+A`

### 2. Traceability Dashboard
- Live overlay: routing profile stats, RAG namespace/chunks, health
- Polls `GET /api/engine/telemetry` every 4s while open
- UI: **Telemetry** or `Ctrl+Shift+Y`

### 3. Context Branching / Versioning
- Fork conversation at any message index (non-destructive)
- Stores under `data/branches/{user}/`
- Message **Fork** button + **Branches** panel
- API: `POST/GET /api/engine/branches`

### 4. Persistent Local Vault Backup
- Snapshot routing analytics, branches, rag namespace data, VERSION
- Configurable target directory
- API: `GET/POST /api/engine/vault/config`, `POST /api/engine/vault/backup`
- UI: **Vault** or `Ctrl+Shift+V`

## Security notes
- Sandbox blocks `__import__`, `open`, `eval`, `exec`, and dunder attributes
- LLM repair is optional and off by default
- Vault copies local app data only to a path you set

## Run
```bash
unzip VISION_AI_v5.3.0_AETHER_LAB.zip -d vision-ai
cd vision-ai
python -m pip install -r requirements.txt
python run.py
```
