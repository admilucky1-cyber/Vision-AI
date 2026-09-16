# Phase 1 — Google Drive model cache (Vision AI)

## Goal
Download **SDXL-Turbo once**, store on Drive, next Colab sessions load without a full internet re-download.

## One-time in Colab
```python
from google.colab import drive
import os
drive.mount("/content/drive")
os.makedirs("/content/drive/MyDrive/vision_ai_models", exist_ok=True)
```

Or run `colab_one_click_boost.py` (auto-mounts when possible).

## How the worker uses it
1. `HF_HOME` → `/content/drive/MyDrive/vision_ai_models/hf`
2. Model snapshots → `.../snapshots/stabilityai__sdxl-turbo`
3. Copy snapshot → `/content/vision_ai_cache/...` for **faster** load than Drive I/O
4. Prefer **sdxl-turbo** on free T4 (`PREFER_FLUX=1` only if you accepted FLUX gate + have VRAM)

## Sessions
| Session | What happens |
|---------|----------------|
| First | Download ~6–7GB to Drive (slow once) |
| Later | Copy Drive → `/content` then load (minutes, not full re-download) |
| Same runtime | Instant (model already in memory) |

## Limits (honest)
- Free Colab still **disconnects**; you must re-run Boost
- Drive is **persistent storage**, not unlimited GPU time
- Do not load FLUX + large LLM together on one T4

## Env overrides
```text
VISION_DRIVE_CACHE=/content/drive/MyDrive/vision_ai_models
VISION_LOCAL_CACHE=/content/vision_ai_cache
PREFER_FLUX=0
LOW_VRAM=1
```
