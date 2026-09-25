# Short video models (14–60s) — free download & use

## Honest limits
- **14–60 second** video is heavy. Free Colab/Kaggle T4 can do **short** clips; full 60s HD is slow or fails.
- Prefer **5–15s** on free GPU; 30–60s only with patience or paid GPU.

## Recommended open models (download to Drive)

| Model | Use | Approx size | Notes |
|-------|-----|-------------|--------|
| **Wan2.1 / Wan T2V small** | Text→video | Large (10GB+) | Community checkpoints on Hugging Face |
| **CogVideoX-2b** | Text→video | ~10GB+ | Better on 16GB+ VRAM; tight on T4 15GB |
| **AnimateDiff** (+ SD1.5) | Image/motion | Smaller | Short loops, easier on free GPU |
| **Stable Video Diffusion (SVD)** | Image→video | ~7GB | Good for short I2V from a still |

Search Hugging Face: `CogVideoX`, `AnimateDiff`, `stable-video-diffusion`, `Wan2.1`.

## One-time download to Google Drive (Colab)

```python
from google.colab import drive
drive.mount('/content/drive')

from huggingface_hub import snapshot_download
import os

os.makedirs('/content/drive/MyDrive/vision_ai_models', exist_ok=True)

# Example: Stable Video Diffusion (image-to-video, short clips)
snapshot_download(
    repo_id="stabilityai/stable-video-diffusion-img2vid-xt",
    local_dir="/content/drive/MyDrive/vision_ai_models/svd-xt",
    local_dir_use_symlinks=False,
)
```

For gated repos, accept the license on the model page and set `HF_TOKEN`.

## Each Colab session

```python
import shutil, os
src = '/content/drive/MyDrive/vision_ai_models/svd-xt'
dst = '/content/svd-xt'
if not os.path.exists(dst):
    shutil.copytree(src, dst)
# then load with diffusers / model-specific code on CUDA
```

## Kaggle alternative
1. Download model once (local or Colab).
2. Upload as a **Kaggle Dataset**.
3. Add dataset to notebook — no Google Drive mount required.

## Alternatives without local video models
| Option | Length | Cost |
|--------|--------|------|
| HF Inference + fal-ai (MiniMax etc.) | Short | Quota / paid |
| CapCut / free editors | Any | Free (manual) |
| Still images only (SDXL Colab) | N/A | Free |

## Vision AI product stance
- **Default:** still images via Colab SDXL Boost.
- **Optional:** short video only when weights + GPU session allow.
- Do not promise unlimited 60s HD on free tier.
