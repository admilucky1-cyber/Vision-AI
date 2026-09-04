# SDXL LoRAs — Hugging Face only (Civitai blocks Colab)

Civitai returns **HTTP 403** from Colab IPs. Use Hugging Face instead.

## Download to Drive (run in Colab)

```python
from google.colab import drive
drive.mount("/content/drive")

from huggingface_hub import hf_hub_download
from pathlib import Path
import shutil

LORAS = Path("/content/drive/MyDrive/vision_ai_models/loras")
LORAS.mkdir(parents=True, exist_ok=True)

# Verified public files on Hugging Face (not Civitai)
items = [
    # Fast 8-step Lightning LoRA for SDXL (works well with turbo-style speed)
    ("ByteDance/SDXL-Lightning", "sdxl_lightning_8step_lora.safetensors", "lightning_8step.safetensors"),
    # Hyper-SD XL 1-step style LoRA
    ("ByteDance/Hyper-SD", "Hyper-SDXL-1step-lora.safetensors", "hyper_sdxl_1step.safetensors"),
    # Community flash LoRA
    ("sd-community/sdxl-flash-lora", "sdxl-flash-lora.safetensors", "sdxl_flash.safetensors"),
]

for repo, filename, out_name in items:
    try:
        path = hf_hub_download(repo_id=repo, filename=filename)
        dest = LORAS / out_name
        shutil.copy2(path, dest)
        print("OK", dest, dest.stat().st_size / 1e6, "MB")
    except Exception as e:
        print("FAIL", repo, filename, "→", e)

print("LoRAs:")
for f in sorted(LORAS.glob("*.safetensors")):
    print(" ", f.name, f"{f.stat().st_size/1e6:.1f} MB")
```

## Use with your local Turbo test

```python
from diffusers import StableDiffusionXLPipeline
import torch

pipe = StableDiffusionXLPipeline.from_pretrained(
    "/content/sdxl-turbo",
    torch_dtype=torch.float16,
    local_files_only=True,
    use_safetensors=True,
    variant="fp16",
)
pipe.to("cuda")

lora = "/content/drive/MyDrive/vision_ai_models/loras/lightning_8step.safetensors"
pipe.load_lora_weights(lora)
# optional: pipe.fuse_lora(lora_scale=0.8)

image = pipe(
    "a cat wearing sunglasses, photo",
    num_inference_steps=4,
    guidance_scale=0.0,
).images[0]
image
```

## Notes
- Keep each LoRA under ~800 MB (Drive quota).
- Worker loads LoRA when `lora_path` is set on `/worker/image`.
- Drive base path accepted: `snapshots/sdxl-turbo` **or** `snapshots/stabilityai__sdxl-turbo`.
