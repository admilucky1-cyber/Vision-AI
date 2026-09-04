"""
Vision AI — RunPod Serverless GPU client
========================================
Optional power-user path using the user's own RunPod API key + endpoint.
Host (Railway) stays free-tier; cost only hits the user's RunPod account.

Env:
  RUNPOD_API_KEY          RunPod API key
  RUNPOD_ENDPOINT_ID      Serverless endpoint ID
  RUNPOD_TIMEOUT_SEC      Poll timeout (default 180)
  RUNPOD_IMAGE_MODEL      Optional model hint for the worker
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("vision-ai.runpod")

RUNPOD_API_KEY = (os.getenv("RUNPOD_API_KEY") or "").strip()
RUNPOD_ENDPOINT_ID = (os.getenv("RUNPOD_ENDPOINT_ID") or "").strip()
RUNPOD_TIMEOUT = int(os.getenv("RUNPOD_TIMEOUT_SEC", "180"))
API_BASE = "https://api.runpod.ai/v2"


def is_enabled() -> bool:
    return bool(RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID)


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def health() -> Dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "reason": "RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID not set"}
    try:
        r = requests.get(
            f"{API_BASE}/{RUNPOD_ENDPOINT_ID}/health",
            headers=_headers(),
            timeout=15,
        )
        data = r.json() if r.content else {}
        return {
            "ok": r.status_code == 200,
            "enabled": True,
            "endpoint": RUNPOD_ENDPOINT_ID,
            "status_code": r.status_code,
            "raw": data,
        }
    except Exception as e:
        return {"ok": False, "enabled": True, "error": str(e)[:200]}


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    negative_prompt: str = "",
) -> Dict[str, Any]:
    if not is_enabled():
        return {"success": False, "error": "RunPod not configured"}

    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": negative_prompt or "blurry, low quality, watermark, text",
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": 0.0 if steps <= 8 else 3.5,
        }
    }
    model_hint = (os.getenv("RUNPOD_IMAGE_MODEL") or "").strip()
    if model_hint:
        payload["input"]["model"] = model_hint

    try:
        r = requests.post(
            f"{API_BASE}/{RUNPOD_ENDPOINT_ID}/run",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        if r.status_code not in (200, 201):
            return {"success": False, "error": f"RunPod submit HTTP {r.status_code}: {r.text[:200]}"}
        job = r.json()
        job_id = job.get("id") or job.get("job_id")
        if not job_id:
            return _extract_image(job, provider="RunPod-Sync")

        deadline = time.time() + RUNPOD_TIMEOUT
        while time.time() < deadline:
            s = requests.get(
                f"{API_BASE}/{RUNPOD_ENDPOINT_ID}/status/{job_id}",
                headers=_headers(),
                timeout=20,
            )
            if s.status_code != 200:
                time.sleep(2)
                continue
            data = s.json()
            status = (data.get("status") or "").upper()
            if status in ("COMPLETED", "SUCCESS"):
                return _extract_image(data, provider="RunPod-Serverless")
            if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
                return {
                    "success": False,
                    "error": f"RunPod job {status}: {str(data.get('error') or data)[:200]}",
                }
            time.sleep(1.5)
        return {"success": False, "error": f"RunPod poll timeout after {RUNPOD_TIMEOUT}s"}
    except Exception as e:
        logger.warning(f"RunPod image failed: {e}")
        return {"success": False, "error": str(e)[:300]}


def _extract_image(data: Dict[str, Any], provider: str) -> Dict[str, Any]:
    output = data.get("output") or data.get("result") or data
    if isinstance(output, list) and output:
        output = output[0]
    if not isinstance(output, dict):
        if isinstance(output, str) and len(output) > 500:
            b64 = output.split(",", 1)[-1] if output.startswith("data:") else output
            return {"success": True, "image_data": b64, "provider": provider}
        return {"success": False, "error": "Unexpected RunPod output shape"}

    for key in ("image_base64", "image", "image_data", "base64", "output"):
        val = output.get(key)
        if isinstance(val, str) and len(val) > 200:
            b64 = val.split(",", 1)[-1] if val.startswith("data:") else val
            return {"success": True, "image_data": b64, "provider": provider}

    url = output.get("image_url") or output.get("url")
    if isinstance(url, str) and url.startswith("http"):
        try:
            img = requests.get(url, timeout=60)
            if img.status_code == 200:
                return {
                    "success": True,
                    "image_data": base64.b64encode(img.content).decode("utf-8"),
                    "provider": provider,
                }
        except Exception as e:
            return {"success": False, "error": f"RunPod image URL fetch failed: {e}"}
    return {"success": False, "error": f"No image in RunPod output: {list(output.keys())[:8]}"}


def chat(prompt: str, system: str = "", max_tokens: int = 1024) -> Optional[str]:
    if not is_enabled():
        return None
    payload = {
        "input": {
            "prompt": prompt,
            "system": system,
            "max_tokens": max_tokens,
            "task": "chat",
        }
    }
    try:
        r = requests.post(
            f"{API_BASE}/{RUNPOD_ENDPOINT_ID}/runsync",
            headers=_headers(),
            json=payload,
            timeout=min(120, RUNPOD_TIMEOUT),
        )
        if r.status_code != 200:
            return None
        data = r.json()
        out = data.get("output") or {}
        if isinstance(out, dict):
            text = out.get("text") or out.get("answer") or out.get("response")
            if text:
                return str(text).strip()
        if isinstance(out, str) and len(out) > 5:
            return out.strip()
    except Exception as e:
        logger.debug(f"RunPod chat skip: {e}")
    return None


__all__ = ["is_enabled", "health", "generate_image", "chat"]
