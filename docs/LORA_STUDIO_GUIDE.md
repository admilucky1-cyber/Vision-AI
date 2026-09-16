# Vision AI — Models, LoRA, Image/Video/Audio

## 1. Chat models (already in app)
- Groq GPT-OSS 20B / 120B via model catalog
- Gemini 2.5, OpenRouter, DeepSeek, Ollama, LM Studio
- `GET /api/models` for live list

## 2. Image / Video / Audio generation (Studio)
1. Open **Studio** in the app (`/studio.html`) or API `/api/studio`
2. Register a **Colab / Kaggle worker** with GPU (Boost flow)
3. Models are registered in `services/model_registry.py`:
   - Image: SDXL Turbo, Flux Schnell, Pollinations fallback
   - Video: SVD-XT (I2V)
4. **Train once → save LoRA → reuse**
   - Dataset upload → training job → checkpoint on Google Drive
   - Register LoRA in model registry with `type=image` + `lora_path`
   - Later generations load base model + LoRA weights (no full retrain)

## 3. Download / cache models
### Colab worker
```python
# In colab_worker_server / boost notebook
from huggingface_hub import snapshot_download
snapshot_download("black-forest-labs/FLUX.1-schnell", local_dir="/content/models/flux")
# optional Drive mount for persistence
```

### Google Drive (recommended)
1. Mount Drive in Colab
2. Save checkpoints under `Drive/VisionAI/loras/<name>/`
3. Worker heartbeat reports available LoRAs to `/api/workers`

### Hugging Face
- Set `HF_TOKEN` in Railway / Colab secrets
- Pull with `huggingface_hub`; never commit weights to git

## 4. API sketch
```
POST /api/studio/jobs          # create train or generate job
POST /api/workers/claim        # GPU worker claims job
POST /api/workers/complete     # upload artifact URL + register
GET  /api/studio/models        # list base + LoRA adapters
```

## 5. YouTube downloads (ops)
On Railway set **only**:
- `YTDLP_COOKIES=cookies.txt` (Netscape export)
- Optional remote `YTDLP_PROXY=http://...` (never 127.0.0.1:9050)
