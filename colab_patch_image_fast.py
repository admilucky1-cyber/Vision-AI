"""Run once in Colab: patches colab_worker_server.py to use HF API first (no 7GB download)."""
from pathlib import Path
import re

p = Path("/content/Vision-AI/colab_worker_server.py")
if not p.exists():
    raise SystemExit("Run from project with colab_worker_server.py present")

t = p.read_text()
start = t.find('@app.post("/worker/image")')
if start < 0:
    raise SystemExit("worker/image not found")
end = t.find("\ndef register_with_main_app", start)
if end < 0:
    end = t.find("\nif __name__", start)
if end < 0:
    raise SystemExit("could not find end of worker_image")

new_fn = r'''@app.post("/worker/image")
def worker_image(body: ImageIn, x_worker_secret: Optional[str] = Header(None)):
    _check_secret(x_worker_secret)
    prompt = body.prompt.strip()
    hf = (os.getenv("HF_TOKEN") or "").strip()
    import requests as req
    api_models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "runwayml/stable-diffusion-v1-5",
    ]
    for model in api_models:
        try:
            headers = {"Authorization": f"Bearer {hf}"} if hf else {}
            r = req.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers=headers,
                json={"inputs": prompt, "options": {"wait_for_model": True}},
                timeout=100,
            )
            ctype = r.headers.get("Content-Type", "")
            if r.status_code == 200 and "image" in ctype:
                return {
                    "success": True,
                    "image_data": base64.b64encode(r.content).decode("utf-8"),
                    "provider": f"HF-API/{model}",
                }
            if r.status_code == 503:
                time.sleep(8)
                r2 = req.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=headers,
                    json={"inputs": prompt, "options": {"wait_for_model": True}},
                    timeout=120,
                )
                if r2.status_code == 200 and "image" in r2.headers.get("Content-Type", ""):
                    return {
                        "success": True,
                        "image_data": base64.b64encode(r2.content).decode("utf-8"),
                        "provider": f"HF-API/{model}",
                    }
        except Exception:
            continue
    try:
        import torch
        if not torch.cuda.is_available():
            raise HTTPException(
                status_code=503,
                detail="Set HF_TOKEN in Colab Secrets for fast images, or Runtime→GPU.",
            )
        pipe = _load_image_pipe()
        kwargs = {
            "prompt": prompt,
            "num_inference_steps": 4 if "schnell" in (_pipe_name or "") or "turbo" in (_pipe_name or "") else 20,
        }
        if "turbo" in (_pipe_name or ""):
            kwargs["guidance_scale"] = 0.0
        out = pipe(**kwargs)
        img = out.images[0]
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return {
            "success": True,
            "image_data": base64.b64encode(buf.getvalue()).decode("utf-8"),
            "provider": f"Colab/{_pipe_name}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image gen failed: {e}")


'''
p.write_text(t[:start] + new_fn + t[end:])
print("Patched", p)
print("Now: Runtime→Restart, set HF_TOKEN secret, re-run one-click boost")
