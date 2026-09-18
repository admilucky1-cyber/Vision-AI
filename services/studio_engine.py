"""Vision AI Studio engine — capability-checked generation with parameter propagation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services import model_registry
from services import drive_state as reg

logger = logging.getLogger("vision-ai.studio")



def _resolve_lora_payload(lora: dict | None, weight: float = 1.0) -> tuple[dict, dict | None]:
    """Return (fields_to_merge, error)."""
    if not lora:
        return {}, None
    raw = (lora.get("drive_path") or lora.get("path") or "").strip()
    path, err = drive_state.sanitize_worker_path(raw, must_exist=False)
    w, werr = drive_state.validate_lora_weight(weight)
    if err:
        # soft: allow worker to resolve relative name under Drive loras/
        if err.get("code") == drive_state.LORA_MISSING and raw:
            return {"lora_path": raw, "lora_weight": w}, None
        return {}, err
    out = {"lora_path": path, "lora_weight": w}
    if werr and werr.get("clamped"):
        out["lora_weight_note"] = werr.get("message")
    return out, None

def _owner(user: Optional[dict]) -> Dict[str, str]:
    u = user or {}
    oid = str(u.get("id") or u.get("username") or "anonymous")
    return {"owner_id": oid, "user": str(u.get("username") or oid)}


async def generate_image(
    *,
    prompt: str,
    model_id: str = "sdxl-turbo",
    lora_id: Optional[str] = None,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    guidance: float = 1.0,
    seed: Optional[int] = None,
    lora_weight: float = 1.0,
    user: Optional[dict] = None,
) -> Dict[str, Any]:
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": {"code": "PROMPT_REQUIRED", "message": "Prompt is required"}}

    model = reg.get_model(model_id)
    if not model:
        return {"ok": False, "error": {"code": "MODEL_NOT_FOUND", "message": f"Unknown model: {model_id}"}}
    if not reg.model_supports(model_id, "t2i") and not reg.model_supports(model_id, "i2i"):
        return {"ok": False, "error": {"code": "CAPABILITY", "message": f"{model_id} does not support image generation"}}

    lora = None
    if lora_id:
        if not reg.model_supports(model_id, "lora"):
            return {"ok": False, "error": {"code": "LORA_UNSUPPORTED", "message": f"{model_id} does not support LoRA"}}
        lora = reg.get_lora(lora_id)
        if not lora:
            return {"ok": False, "error": {"code": "LORA_NOT_FOUND", "message": f"Unknown LoRA: {lora_id}"}}

    owner = _owner(user)
    job = reg.create_job({
        "type": "image_generate",
        "prompt": prompt[:2000],
        "negative_prompt": (negative_prompt or "")[:1000],
        "model_id": model_id,
        "lora_id": lora_id,
        "lora_weight": lora_weight,
        "width": width,
        "height": height,
        "steps": steps,
        "guidance": guidance,
        "seed": seed,
        "status": "running",
        **owner,
    })

    # Propagate model/lora into worker payload (validated paths)
    worker_payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "model_id": model_id,
        "hf_id": model.get("hf_id"),
        "lora_id": lora_id,
        "width": width,
        "height": height,
        "steps": steps,
        "guidance": guidance,
        "seed": seed,
    }
    if lora:
        fields, lerr = _resolve_lora_payload(lora, lora_weight)
        if lerr and lerr.get("code") in ("PATH_REJECTED", "LORA_INVALID"):
            return {"ok": False, "error": lerr}
        worker_payload.update(fields)
    else:
        worker_payload["lora_weight"] = lora_weight

    images: List[dict] = []
    provider = "none"
    error = None

    try:
        from services import colab_worker as cw
        if hasattr(cw, "is_live") and cw.is_live():
            # Prefer payload-aware API if worker supports it
            gen = getattr(cw, "generate_image", None)
            if gen:
                result = gen(
                    prompt,
                    width=width,
                    height=height,
                    steps=steps,
                    negative_prompt=negative_prompt or "",
                    guidance=guidance,
                    seed=seed,
                    model_id=model_id,
                    hf_id=model.get("hf_id"),
                    lora_id=lora_id,
                    lora_path=worker_payload.get("lora_path"),
                    lora_weight=lora_weight,
                    job_id=job["id"],
                )
                if result and (result.get("image") or result.get("url")):
                    images.append(result if isinstance(result, dict) else {"data": result})
                    provider = "colab"
                    reg.transition_job(job["id"], "completed", "colab worker", provider=provider)
    except Exception as e:
        logger.info("colab image: %s", e)

    # If GPU worker exists but returned nothing, keep job claimable
    if not images:
        try:
            from services.flux_image import generate_image_with_fallback
            result = await generate_image_with_fallback(prompt, width=width, height=height)
            if result and (result.get("image") or result.get("url") or result.get("data")):
                images.append(result)
                provider = result.get("provider") or "flux_fallback"
        except Exception as e:
            error = str(e)[:200]
            logger.info("flux: %s", e)

    if not images:
        try:
            from services.image_gen import generate_all_diagrams
            imgs = await generate_all_diagrams("", "creative", user_message=prompt)
            if imgs:
                images = imgs if isinstance(imgs, list) else [imgs]
                provider = "image_gen"
        except Exception as e:
            error = str(e)[:200]

    ok = bool(images)
    if ok:
        art = reg.add_artifact({
            "type": "image",
            "job_id": job["id"],
            "owner_id": owner["owner_id"],
            "model_id": model_id,
            "lora_id": lora_id,
            "count": len(images),
            "provider": provider,
        })
        reg.transition_job(job["id"], "completed", f"provider={provider}", provider=provider, artifact_id=art["id"], result_count=len(images))
    else:
        reg.transition_job(job["id"], "failed", error or "No provider available", error=error)

    return {
        "ok": ok,
        "job_id": job["id"],
        "model": {"id": model.get("id"), "name": model.get("name"), "capabilities": model.get("capabilities")},
        "lora_id": lora_id,
        "params": {"width": width, "height": height, "steps": steps, "guidance": guidance, "seed": seed, "lora_weight": lora_weight},
        "provider": provider,
        "images": images,
        "error": None if ok else {"code": "GENERATION_FAILED", "message": error or "Start Colab Boost or configure image providers"},
    }


def queue_lora_train(
    *,
    dataset_id: str,
    base_model: str,
    rank: int = 16,
    epochs: int = 10,
    resolution: int = 1024,
    learning_rate: float = 1e-4,
    user: Optional[dict] = None,
) -> Dict[str, Any]:
    if not reg.get_model(base_model):
        return {"ok": False, "error": {"code": "MODEL_NOT_FOUND", "message": base_model}}
    if not reg.model_supports(base_model, "lora"):
        return {"ok": False, "error": {"code": "LORA_UNSUPPORTED", "message": f"{base_model} cannot train LoRA"}}
    owner = _owner(user)
    job = reg.create_job({
        "type": "lora_train",
        "dataset_id": dataset_id,
        "base_model": base_model,
        "rank": rank,
        "epochs": epochs,
        "resolution": resolution,
        "learning_rate": learning_rate,
        "status": "queued",
        "message": "Queued for GPU worker. Worker must claim, checkpoint, resume, export LoRA to Drive, then register_lora.",
        "resumable": True,
        **owner,
    })
    return {"ok": True, "job": job}


def queue_video(
    *,
    prompt: str,
    mode: str = "i2v",
    model_id: str = "svd-xt",
    input_image: Optional[str] = None,
    frames: int = 14,
    fps: int = 7,
    seed: Optional[int] = None,
    user: Optional[dict] = None,
) -> Dict[str, Any]:
    model = reg.get_model(model_id)
    if not model:
        return {"ok": False, "error": {"code": "MODEL_NOT_FOUND", "message": model_id}}
    mode = (mode or "i2v").lower()
    if mode == "t2v" and not reg.model_supports(model_id, "t2v"):
        return {"ok": False, "error": {"code": "CAPABILITY", "message": f"{model_id} does not support T2V (SVD-XT is I2V only)"}}
    if mode == "i2v" and not reg.model_supports(model_id, "i2v"):
        return {"ok": False, "error": {"code": "CAPABILITY", "message": f"{model_id} does not support I2V"}}
    if mode == "i2v" and not input_image:
        return {"ok": False, "error": {"code": "INPUT_REQUIRED", "message": "I2V requires an input image"}}
    max_frames = int(model.get("maximum_frames") or 25)
    frames = max(1, min(int(frames), max_frames))
    owner = _owner(user)
    job = reg.create_job({
        "type": "video_generate",
        "prompt": (prompt or "")[:2000],
        "mode": mode,
        "model_id": model_id,
        "frames": frames,
        "fps": fps,
        "seed": seed,
        "has_input_image": bool(input_image),
        "status": "queued",
        "message": "Requires live GPU worker with matching capabilities. Free T4 = short clips only.",
        **owner,
    })
    return {
        "ok": True,
        "job": job,
        "limits": {"maximum_frames": max_frames, "note": model.get("notes")},
    }
