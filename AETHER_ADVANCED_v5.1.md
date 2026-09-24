# Vision AI v5.1.0 — Aether Advanced

## Features

### 1. Local Data Embedding Engine (Private RAG)
- Uses existing **ChromaDB + sentence-transformers** when available
- **FAISS-lite** (numpy cosine) fallback if Chroma fails to load
- Uploaded chat files are auto-indexed into the vector store
- API: `GET /api/rag/status`, `POST /api/rag/index`, `POST /api/rag/search`, `GET /api/rag/documents`, `DELETE /api/rag/clear`
- Header badge shows backend (RAG / RAG·lite)

### 2. Model Routing Profiles
- Profiles: auto, coding, fast, reasoning, rag_docs, creative, data_science
- `GET /api/routing/profiles`
- Composer **Route** selector + `X-Vision-Routing-Profile` header on chat requests
- Server maps profile → provider chain in `services/llm.py`

### 3. Prompt Template Library
- Searchable blueprints: data science, debugging, curriculum, coding
- Button **⌘** in header or `Ctrl+Shift+L`
- Injects into hero composer

### 4. Persistent Session Export
- Export menu (download icon): **Markdown · JSON · CSV · PDF report**
- Shortcut: `Ctrl+Shift+E`
- PDF via print-ready window (Save as PDF)

### 5. Multi-Modal Asset Inspector
- Collects images from chat automatically
- Zoom controls + metadata panel
- Shortcut: `Ctrl+Shift+I`

## Compatibility
- Backend routes additive
- Frontend scripts additive (`aether-advanced.js`)
- No breaking changes to existing chat/auth/streaming

## Run
```bash
unzip VISION_AI_v5.1.0_AETHER_ADVANCED.zip -d vision-ai
cd vision-ai
python -m pip install -r requirements.txt
python run.py
```
Open http://127.0.0.1:5050

Optional heavy RAG: chromadb + sentence-transformers already listed in requirements.txt.
First embedding model download may take time on first index.
