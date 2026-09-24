# Vision AI LLM Service & Router v6.5.0

## Architecture (proper way)

```
routes/chat.py          → orchestration (files, YouTube, RAG, search)
        ↓
services/llm_service.py → unified complete / stream / health
        ↓
services/llm.py         → provider implementations + failover chain
```

## New API (`/api/llm`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/llm/health` | Provider config snapshot |
| GET | `/api/llm/providers` | Same as health providers block |
| GET | `/api/llm/models` | List known models |
| POST | `/api/llm/complete` | `{ message, context?, backend?, username? }` |
| POST | `/api/llm/stream` | SSE token stream |
| GET | `/api/llm/test` | Probe configured providers |

## Backends
`auto` | `gemini` | `groq` | `deepseek` | `openrouter` | `ollama` | `lmstudio` | `openai-compat`

Aliases: `google`→gemini, `local`→ollama, `or`→openrouter

## Features
- Failover chain (existing) behind a clean service API
- Latency + ok/error metadata on complete
- Chat route uses `llm_service.complete` when no key overrides
- Streaming SSE endpoint for progressive UI
- Does not break existing `/chat` or Studio flows

## Env keys
`GOOGLE_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`,
`OLLAMA_BASE`, `LMSTUDIO_BASE`, `OPENAI_COMPAT_BASE`, `OPENAI_COMPAT_KEY`, `OPENAI_COMPAT_MODEL`
