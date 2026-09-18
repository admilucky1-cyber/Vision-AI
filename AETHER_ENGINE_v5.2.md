# Vision AI v5.2.0 — Aether Engine

Production-safe engine layer on top of v5.1 Advanced.

## Implemented in this release

### RAG
| Feature | Implementation |
|--------|----------------|
| Async indexing | `asyncio` background queue via `enqueue_index` — uploads don't block chat |
| Namespace isolation | `user:{id}` / `session:{sid}` / `guest:anonymous` stores |
| Semantic chunking | Paragraph + fenced code + `$$` math block preservation |
| Hybrid search | Dense cosine + BM25 sparse (`alpha` blend, default 0.65) |
| Startup health | `GET /api/rag/health` + log on boot |
| LRU pruning | Per-namespace + global `POST /api/rag/prune` |
| Offline fallback | NumPy matrix + hash-bag embeddings if ST/Chroma missing |
| Streaming citations | `/api/rag/search` citation cards + doc viewer pane |

### Routing
| Feature | Implementation |
|--------|----------------|
| Profile analytics | `GET /api/routing/analytics` — counts, avg latency, token est. |
| Profile header | `X-Vision-Routing-Profile` still honored |

### Context & export
| Feature | Implementation |
|--------|----------------|
| Context governor | `services/context_governor.py` priority keep (code/math/system) |
| Export modal | Format + range + exclude system (`Ctrl+Shift+X`) |
| Portable config | Export localStorage theme/routing pack (JSON) |
| Workspace bundle | `python run.py --bundle` → `downloads/vision_workspace_bundle_*.zip` |

### Resilience
| Feature | Implementation |
|--------|----------------|
| Self-healing handler | Global FastAPI exception handler returns safe JSON, no crash |
| Split co-pilot UI | Dual-pane shell toggle (secondary profile workspace) |

## APIs (new/updated)

- `GET /api/rag/status` — namespace + health
- `GET /api/rag/health` — integrity check
- `POST /api/rag/index` — `{async_mode:true}` default
- `POST /api/rag/search` — hybrid + `citations[]`
- `POST /api/rag/prune`
- `GET /api/routing/analytics`

## Explicitly NOT full production yet (roadmap)

These were requested and are **partially prepared or deferred** (honest scope):

- Celery distributed workers (use in-process asyncio queue instead)
- Full WASM multi-language sandbox / PyInstaller single binary
- TensorRT / ONNX bundled quantized embed model binary
- WebSocket multi-tab sync (still SSE/fetch)
- Full agentic write→run→self-fix server loop
- Tesseract/OpenCV offline OCR pipeline
- RAG triad automatic eval harness
- Git-like prompt versioning with diffs

## Run

```bash
unzip VISION_AI_v5.2.0_AETHER_ENGINE.zip -d vision-ai
cd vision-ai
python -m pip install -r requirements.txt
python run.py
# optional portable data pack:
python run.py --bundle
```

Open http://127.0.0.1:5050

## Compatibility

- Additive backend routes/services
- Additive frontend scripts (`aether-engine.js`)
- Existing chat/auth/streaming preserved
