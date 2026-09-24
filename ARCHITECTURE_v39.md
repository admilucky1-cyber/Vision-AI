# Vision AI v3.9 — Architecture

## Preserved
- Chat LLM cascade (Groq → Gemini → OpenRouter → DeepSeek)
- Auth / quota / workers registration
- Colab/Kaggle as **compute only**
- Existing image_gen + flux_image fallbacks

## Added
- `services/model_registry.py` — models, LoRAs, datasets, jobs
- `services/studio_engine.py` — generate / queue train / queue video
- `routes/studio.py` — `/api/studio/*` (auth + paid gates)
- `frontend/studio.html` — Model Studio UI

## Storage map (3 Drive accounts)
- A: `VISION-AI-STORAGE/IMAGE_MODELS`
- B: `VISION-AI-STORAGE/VIDEO_MODELS`
- C: `VISION-AI-STORAGE/DATASETS`

Env overrides: `DRIVE_IMAGE_MODELS`, `DRIVE_VIDEO_MODELS`, `DRIVE_DATASETS`

## Security
- Generate images: paid plans only (`can_generate_images`)
- Train / video: paid + not guest
- Jobs filtered by username unless admin
- Workers still require `WORKER_SECRET`

## Lifecycle
Train once on Colab → save LoRA to Drive → register in registry → reuse forever
