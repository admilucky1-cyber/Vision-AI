"""
Vision AI Colab GPU Worker  v3.2.1
==================================
Run inside Google Colab (Runtime → GPU / T4).

Exposes:
  GET  /worker/health
  POST /worker/chat
  POST /worker/chat/stream   (SSE streaming)
  POST /worker/image
  POST /worker/warmup

Features:
  - Startup model preload + CUDA warm-up inference (kills first-request 30s latency)
  - Serverless-first image path (Hugging Face Inference API + Pollinations) → local GPU fallback
  - Optional streaming chat
  - Auto-register + heartbeat to main app

Env (Colab Secrets recommended):
  WORKER_SECRET          shared secret
  MAIN_APP_URL           your Railway / Render URL
  HF_TOKEN               Hugging Face token (free)
  GROQ_API_KEY / GOOGLE_API_KEY / OPENROUTER_API_KEY
  IMAGE_MODEL_PATH       optional local /content path
"""

from __future__ import annotations

import base64
import io
import os
import time
import threading
import json
from typing import Any, Dict, Optional, Generator

# Load secrets written by one-click boost (Colab often blocks userdata.get)
for _env_path in ("/content/.vision_boost.env", ".env"):
    if os.path.isfile(_env_path):
        try:
            from dotenv import load_dotenv
            load_dotenv(_env_path, override=False)
        except Exception:
            try:
                with open(_env_path) as _f:
                    for _line in _f:
                        _line = _line.strip()
                        if not _line or _line.startswith("#") or "=" not in _line:
                            continue
                        _k, _, _v = _line.partition("=")
                        if _k and _v and not os.environ.get(_k):
                            os.environ[_k] = _v
            except Exception:
                pass
        break

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

WORKER_SECRET = (os.getenv("WORKER_SECRET") or "").strip()
app = FastAPI(title="Vision AI Colab Worker", version="3.2.1")

# ---------------------------------------------------------------------------
# Global model state
# ---------------------------------------------------------------------------
_pipe = None
_pipe_name: Optional[str] = None
_warmed = False
_warmup_error: Optional[str] = None
_warmup_lock = threading.Lock()
_load_status: str = "idle"
_loading: bool = False
_OFFLOAD_MODE: str = "none"  # none | model_cpu | sequential



def _check_secret(x_worker_secret: Optional[str] = None):
    if not WORKER_SECRET:
        raise HTTPException(status_code=503, detail="WORKER_SECRET not configured")
    import hmac as _hmac
    if not _hmac.compare_digest(x_worker_secret or "", WORKER_SECRET):
        raise HTTPException(status_code=401, detail="Invalid worker secret")


class ChatIn(BaseModel):
    question: str = Field(..., min_length=1)
    context: str = ""
    model: str = "auto"
    temperature: float = 0.5
    max_tokens: int = 2048


class ImageIn(BaseModel):
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = ""
    steps: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    guidance: Optional[float] = None
    seed: Optional[int] = None
    model_id: Optional[str] = None
    hf_id: Optional[str] = None
    lora_id: Optional[str] = None
    lora_path: Optional[str] = None
    lora_weight: float = 1.0
    job_id: Optional[str] = None


class BatchImageIn(BaseModel):
    """Multiple prompts in one Colab session — maximizes free T4 throughput."""
    prompts: list = Field(..., min_length=1)
    steps: Optional[int] = None
    width: Optional[int] = 512
    height: Optional[int] = 512


# ---------------------------------------------------------------------------
# GPU / VRAM helpers
# ---------------------------------------------------------------------------
def _vram_stats() -> dict:
    try:
        import torch
        if not torch.cuda.is_available():
            return {}
        free, total = torch.cuda.mem_get_info()
        used = total - free
        return {
            "used_mb": int(used / (1024 * 1024)),
            "total_mb": int(total / (1024 * 1024)),
            "free_mb": int(free / (1024 * 1024)),
        }
    except Exception:
        return {}


def _gpu_name() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
        return "cpu"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Image model load + WARMUP
# ---------------------------------------------------------------------------
def _cuda_memory_setup():
    """CUDA allocator + fragmentation tuning for free T4 / low-VRAM GPUs."""
    import os as _os
    _os.environ.setdefault(
        "PYTORCH_CUDA_ALLOC_CONF",
        "expandable_segments:True,max_split_size_mb:128",
    )
    try:
        import torch
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            try:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            except Exception:
                pass
    except Exception:
        pass



# ---------------------------------------------------------------------------
# Phase 1: Google Drive model cache → fast local /content copy
# ---------------------------------------------------------------------------
DRIVE_CACHE_ROOT = (
    os.getenv("VISION_DRIVE_CACHE")
    or "/content/drive/MyDrive/vision_ai_models"
).rstrip("/")
LOCAL_CACHE_ROOT = (
    os.getenv("VISION_LOCAL_CACHE")
    or "/content/vision_ai_cache"
).rstrip("/")


def _ensure_drive_hf_env() -> None:
    """Point Hugging Face caches at Drive so downloads persist across sessions."""
    drive_hf = os.path.join(DRIVE_CACHE_ROOT, "hf")
    try:
        os.makedirs(drive_hf, exist_ok=True)
        # Only set if Drive is mounted (folder creatable)
        for key in ("HF_HOME", "HUGGINGFACE_HUB_CACHE", "HF_HUB_CACHE", "TRANSFORMERS_CACHE"):
            if not os.environ.get(key):
                os.environ[key] = drive_hf
    except Exception as e:
        print(f"[cache] Drive HF env skip: {e}")


def _local_snapshot_dir(model_id: str) -> str:
    safe = model_id.replace("/", "__")
    return os.path.join(LOCAL_CACHE_ROOT, safe)


def _drive_snapshot_dir(model_id: str) -> str:
    safe = model_id.replace("/", "__")
    return os.path.join(DRIVE_CACHE_ROOT, "snapshots", safe)


def _drive_snapshot_candidates(model_id: str) -> list:
    """Prefer HF-style name, also accept short aliases users already created."""
    primary = _drive_snapshot_dir(model_id)
    alts = []
    # User often saves as snapshots/sdxl-turbo (not stabilityai__sdxl-turbo)
    if "sdxl-turbo" in model_id.lower():
        alts.append(os.path.join(DRIVE_CACHE_ROOT, "snapshots", "sdxl-turbo"))
        alts.append(os.path.join(DRIVE_CACHE_ROOT, "snapshots", "sdxl-turbo-colab"))
    if "flux" in model_id.lower():
        alts.append(os.path.join(DRIVE_CACHE_ROOT, "snapshots", "flux"))
        alts.append(os.path.join(DRIVE_CACHE_ROOT, "snapshots", "FLUX.1-schnell"))
    out = [primary]
    for a in alts:
        if a not in out:
            out.append(a)
    return out


def _prepare_model_dir(model_id: str, hf_token: str = "") -> str:
    """
    Return a filesystem path suitable for from_pretrained().
    Order:
      1) Local /content snapshot (fastest)
      2) Drive snapshot (incl. short aliases like sdxl-turbo) → copy to local
      3) snapshot_download into Drive, then copy to local
      4) Fall back to hub id (online download into HF_HOME on Drive)
    """
    _ensure_drive_hf_env()
    local = _local_snapshot_dir(model_id)
    drive = _drive_snapshot_dir(model_id)

    def _looks_ready(path: str) -> bool:
        if not os.path.isdir(path):
            return False
        # any weights / config is enough signal
        for root, _dirs, files in os.walk(path):
            for f in files:
                if f.endswith((".safetensors", ".bin", ".json", ".ckpt")):
                    return True
            break  # top-level only enough for config; walk a bit
        # deeper check
        for root, _dirs, files in os.walk(path):
            for f in files:
                if f.endswith((".safetensors", ".bin")):
                    return True
        return False

    if _looks_ready(local):
        print(f"[cache] Using local snapshot: {local}")
        return local

    # Accept both HF-named and short alias folders on Drive
    drive_src = None
    for cand in _drive_snapshot_candidates(model_id):
        if _looks_ready(cand):
            drive_src = cand
            break
    if drive_src:
        print(f"[cache] Copying Drive → local (faster load): {drive_src} → {local}")
        try:
            import shutil
            os.makedirs(os.path.dirname(local), exist_ok=True)
            if os.path.isdir(local):
                shutil.rmtree(local, ignore_errors=True)
            shutil.copytree(drive_src, local)
            return local
        except Exception as e:
            print(f"[cache] copy failed, loading from Drive path: {e}")
            return drive_src

    # First-time: download snapshot to Drive, then to local
    try:
        from huggingface_hub import snapshot_download
        print(f"[cache] First-time download of {model_id} → Drive (persists)...")
        os.makedirs(drive, exist_ok=True)
        path = snapshot_download(
            repo_id=model_id,
            local_dir=drive,
            local_dir_use_symlinks=False,
            token=hf_token or None,
        )
        print(f"[cache] Saved on Drive: {path}")
        try:
            import shutil
            os.makedirs(os.path.dirname(local), exist_ok=True)
            if os.path.isdir(local):
                shutil.rmtree(local, ignore_errors=True)
            shutil.copytree(drive, local)
            print(f"[cache] Copied to local: {local}")
            return local
        except Exception as e:
            print(f"[cache] local copy skip: {e}")
            return drive
    except Exception as e:
        print(f"[cache] snapshot_download failed ({e}); will use hub id + HF_HOME on Drive")
        return model_id



def _cuda_cleanup():
    """Release cached CUDA blocks after inference to avoid OOM on next request."""
    try:
        import gc
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                torch.cuda.ipc_collect()
            except Exception:
                pass
    except Exception:
        pass



def _set_load_status(msg: str) -> None:
    """Human-readable status for UI polling (/worker/health)."""
    global _load_status
    _load_status = (msg or "")[:240]
    print(f"[status] {_load_status}")


def _memory_guard(min_free_mb: int = 1200, *, for_load: bool = False) -> dict:
    """Refuse heavy work when VRAM is critically low. Returns vram stats."""
    vram = _vram_stats()
    free = int(vram.get("free_mb") or 0)
    total = int(vram.get("total_mb") or 0)
    if total and free < min_free_mb:
        _cuda_cleanup()
        vram = _vram_stats()
        free = int(vram.get("free_mb") or 0)
    if total and free < max(512, min_free_mb // 2):
        raise RuntimeError(
            f"GPU memory too low (free={free}MB / total={total}MB). "
            "Restart Colab runtime, keep only SDXL-turbo loaded, use 512px images."
        )
    return vram


def _apply_offload(pipe, device: str, low_vram: bool) -> str:
    """
    Prefer sequential CPU offload on free T4 (lowest peak VRAM).
    Fallback: model CPU offload → full CUDA.
    TensorRT: optional, rarely available on free Colab — see ENABLE_TENSORRT.
    """
    global _OFFLOAD_MODE
    if device != "cuda":
        pipe = pipe.to(device)
        _OFFLOAD_MODE = "cpu"
        return _OFFLOAD_MODE

    # Optional TensorRT / torch.compile path (experimental; skip if unavailable)
    if (os.getenv("ENABLE_TENSORRT", "0") or "0").strip().lower() in ("1", "true", "yes"):
        _set_load_status("Trying torch.compile acceleration (experimental)…")
        try:
            import torch
            # Full TensorRT engines are not standard on free Colab; torch.compile is the portable option
            if hasattr(pipe, "unet") and hasattr(torch, "compile"):
                pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=False)
                _OFFLOAD_MODE = "torch_compile"
                _set_load_status("torch.compile enabled on UNet")
        except Exception as e:
            print(f"[opt] torch.compile skip: {e}")

    prefer_seq = (os.getenv("SEQUENTIAL_OFFLOAD", "1") or "1").strip().lower() not in ("0", "false", "no")
    if low_vram or prefer_seq:
        if prefer_seq:
            try:
                _set_load_status("Enabling sequential CPU offload (lowest VRAM)…")
                pipe.enable_sequential_cpu_offload()
                _OFFLOAD_MODE = "sequential"
                return _OFFLOAD_MODE
            except Exception as e:
                print(f"[offload] sequential failed: {e}")
        try:
            _set_load_status("Enabling model CPU offload…")
            pipe.enable_model_cpu_offload()
            _OFFLOAD_MODE = "model_cpu"
            return _OFFLOAD_MODE
        except Exception as e:
            print(f"[offload] model_cpu failed: {e}")
    pipe = pipe.to(device)
    _OFFLOAD_MODE = "full_cuda"
    return _OFFLOAD_MODE


def _load_image_pipe():
    """Load SDXL-Turbo (Phase 1 default) / optional FLUX / SD-1.5 with Drive cache."""
    global _pipe, _pipe_name
    if _pipe is not None:
        return _pipe

    _cuda_memory_setup()
    _ensure_drive_hf_env()
    import torch
    from diffusers import AutoPipelineForText2Image

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    low_vram = (os.getenv("LOW_VRAM", "1") or "1").strip() not in ("0", "false", "False")

    hf_token = (
        os.getenv("HF_TOKEN")
        or os.getenv("HUGGING_FACE_HUB_TOKEN")
        or os.getenv("HUGGINGFACE_TOKEN")
        or ""
    ).strip()

    # Phase 1: SDXL-turbo first (reliable on free T4). FLUX optional via PREFER_FLUX=1
    prefer_flux = (os.getenv("PREFER_FLUX", "0") or "0").strip() in ("1", "true", "True", "yes")
    candidates = []
    if prefer_flux:
        candidates.append(("black-forest-labs/FLUX.1-schnell", {"torch_dtype": dtype}))
    candidates.extend([
        ("stabilityai/sdxl-turbo", {"torch_dtype": dtype, "variant": "fp16"}),
        ("runwayml/stable-diffusion-v1-5", {"torch_dtype": dtype}),
    ])
    if not prefer_flux:
        candidates.append(("black-forest-labs/FLUX.1-schnell", {"torch_dtype": dtype}))

    global _loading
    last_err = None
    _loading = True
    try:
        if device == "cuda":
            try:
                _memory_guard(1000, for_load=True)
            except Exception as e:
                _set_load_status(str(e))
                # still try offload path
                print(f"[guard] {e}")

        for name, kwargs in candidates:
            try:
                _set_load_status(f"Preparing {name} from Drive/cache (one-time download may take a few minutes)…")
                print(f"[warmup] Loading image model: {name} (low_vram={low_vram}, hf_token={'yes' if hf_token else 'no'}) ...")
                model_src = _prepare_model_dir(name, hf_token=hf_token)
                if hf_token:
                    kwargs = {**kwargs, "token": hf_token}
                _set_load_status(f"Loading weights into memory: {name}…")
                pipe = AutoPipelineForText2Image.from_pretrained(model_src, **kwargs)

                mode = _apply_offload(pipe, device, low_vram)
                _set_load_status(f"Offload mode: {mode}. Enabling memory savers…")

                for enabler in ("enable_attention_slicing", "enable_vae_slicing", "enable_vae_tiling"):
                    try:
                        getattr(pipe, enabler)()
                    except Exception:
                        pass
                try:
                    pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    try:
                        pipe.enable_attention_slicing("max")
                    except Exception:
                        pass

                _pipe = pipe
                _pipe_name = name
                _set_load_status(f"Ready: {name} ({mode}). Warming up…")
                print(f"[warmup] Loaded {_pipe_name} offload={mode}")
                return pipe
            except Exception as e:
                last_err = e
                _set_load_status(f"Failed {name}: {str(e)[:120]}")
                print(f"[warmup] Failed {name}: {e}")
                _cuda_cleanup()
                continue
        _set_load_status(f"Could not load any image model: {last_err}")
        raise RuntimeError(f"Could not load any image model: {last_err}")
    finally:
        _loading = False


def _run_warmup_inference():
    """
    Single short inference so CUDA kernels, weights and allocator are hot.
    Prevents the classic 20-40 s first-user latency on Colab.
    """
    global _warmed, _warmup_error
    with _warmup_lock:
        if _warmed:
            return
        try:
            t0 = time.time()
            pipe = _load_image_pipe()
            steps = 1 if "schnell" in (_pipe_name or "") or "turbo" in (_pipe_name or "") else 2
            kwargs = {
                "prompt": "warmup test, simple red circle on white background",
                "num_inference_steps": steps,
            }
            if "turbo" in (_pipe_name or ""):
                kwargs["guidance_scale"] = 0.0
            _ = pipe(**kwargs)
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
            except Exception:
                pass
            _warmed = True
            _warmup_error = None
            print(f"[warmup] Inference warm-up OK in {time.time() - t0:.1f}s  model={_pipe_name}")
            _set_load_status(f"Ready — {_pipe_name} warmed in {time.time() - t0:.1f}s")
        except Exception as e:
            _warmup_error = str(e)[:300]
            print(f"[warmup] FAILED: {e}")


def _background_warmup():
    """Non-blocking startup warm-up."""
    def _job():
        try:
            _run_warmup_inference()
        except Exception as e:
            print(f"[warmup] background error: {e}")
    threading.Thread(target=_job, daemon=True, name="vision-warmup").start()


@app.on_event("startup")
def on_startup():
    print("[worker] Startup — scheduling model warm-up")
    _background_warmup()
    _start_keepalive_loop()



# ---------------------------------------------------------------------------
# Keep-alive / Auto-wake ping (reduces idle disconnects; does not prevent all)
# ---------------------------------------------------------------------------
_last_ping_ts = 0.0


@app.get("/worker/ping")
@app.post("/worker/ping")
def worker_ping(x_worker_secret: Optional[str] = Header(None)):
    """Lightweight heartbeat — call every ~5 minutes from Boost or main app."""
    global _last_ping_ts
    _check_secret(x_worker_secret)
    _last_ping_ts = time.time()
    # Touch CUDA lightly if available (optional)
    try:
        import torch
        if torch.cuda.is_available():
            _ = torch.zeros(1, device="cuda")
    except Exception:
        pass
    return {
        "ok": True,
        "ts": _last_ping_ts,
        "warmed": _warmed,
        "image_model": _pipe_name,
        "local_llm": bool(_llm_model),
    }


def _start_keepalive_loop():
    """Self-ping every 5 minutes so the runtime stays active while tab is open."""
    def _loop():
        while True:
            try:
                time.sleep(300)
                worker_ping(x_worker_secret=WORKER_SECRET or None)
                # Also heartbeat main app if configured
                main_url = (os.getenv("MAIN_APP_URL") or "").rstrip("/")
                secret = WORKER_SECRET
                public = (os.getenv("PUBLIC_WORKER_URL") or "").rstrip("/")
                if main_url and secret:
                    try:
                        import requests as req
                        req.post(
                            f"{main_url}/api/workers/heartbeat",
                            json={"url": public or "colab-local", "secret": secret},
                            timeout=15,
                        )
                    except Exception:
                        pass
            except Exception as e:
                print(f"[keepalive] {e}")
    threading.Thread(target=_loop, daemon=True, name="vision-keepalive").start()


# Optional local LLM (complex reasoning) — lazy; prefer small model on T4
_llm_model = None
_llm_tokenizer = None
_llm_name: Optional[str] = None
_llm_lock = threading.Lock()


def _load_local_llm():
    """
    Lazy-load a small/medium instruct model for complex prompts.
    Default: Qwen2.5-3B-Instruct (fits T4 with image model unloaded).
    Set LOCAL_LLM_ID=Qwen/Qwen2.5-7B-Instruct only if image gen is idle and VRAM allows.
    """
    global _llm_model, _llm_tokenizer, _llm_name
    if _llm_model is not None:
        return _llm_model
    with _llm_lock:
        if _llm_model is not None:
            return _llm_model
        if (os.getenv("LOCAL_LLM", "1") or "1").strip().lower() in ("0", "false", "no"):
            return None
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            model_id = (
                os.getenv("LOCAL_LLM_ID") or "Qwen/Qwen2.5-3B-Instruct"
            ).strip()
            print(f"[llm] Loading local model {model_id} ...")
            # Free image VRAM if needed for larger models
            if "7B" in model_id or "7b" in model_id:
                global _pipe, _pipe_name, _warmed
                if _pipe is not None:
                    print("[llm] Unloading image pipe to free VRAM for 7B...")
                    try:
                        del _pipe
                    except Exception:
                        pass
                    _pipe = None
                    _pipe_name = None
                    _warmed = False
                    _cuda_cleanup()
            tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto",
                trust_remote_code=True,
            )
            _llm_tokenizer = tok
            _llm_model = model
            _llm_name = model_id
            print(f"[llm] Ready: {model_id}")
            return model
        except Exception as e:
            print(f"[llm] load failed: {e}")
            return None


def _local_llm_generate(question: str, context: str = "") -> Optional[str]:
    model = _load_local_llm()
    if model is None or _llm_tokenizer is None:
        return None
    try:
        import torch
        system = (
            "You are VISION AI local reasoner. Be accurate and structured. "
            "For math, show steps. Use the context if provided."
        )
        user = question if not context else f"Context:\n{context[:6000]}\n\nQuestion: {question}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        prompt = _llm_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = _llm_tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=int(os.getenv("LOCAL_LLM_MAX_TOKENS", "1024")),
                temperature=0.3,
                do_sample=True,
                top_p=0.9,
            )
        text = _llm_tokenizer.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        return (text or "").strip()
    except Exception as e:
        print(f"[llm] generate failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/worker/health")
def health(x_worker_secret: Optional[str] = Header(None)):
    _check_secret(x_worker_secret)
    vram = _vram_stats()
    return {
        "status": "ok",
        "version": "3.2.1",
        "gpu": _gpu_name(),
        "image_model": _pipe_name or "not-loaded",
        "warmed": _warmed,
        "warmup_error": _warmup_error,
        "loading": _loading,
        "load_status": _load_status,
        "offload_mode": _OFFLOAD_MODE,
        "vram_used_mb": vram.get("used_mb"),
        "vram_total_mb": vram.get("total_mb"),
        "vram_free_mb": vram.get("free_mb"),
        "chat_keys": {
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "google": bool(os.getenv("GOOGLE_API_KEY")),
            "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        },
        "ts": time.time(),
    }


@app.post("/worker/warmup")
def force_warmup(x_worker_secret: Optional[str] = Header(None)):
    """Manual trigger (useful after Colab reconnect)."""
    _check_secret(x_worker_secret)
    _run_warmup_inference()
    return {
        "warmed": _warmed,
        "model": _pipe_name,
        "error": _warmup_error,
        "vram": _vram_stats(),
    }


# ---------------------------------------------------------------------------
# Chat (non-streaming) – free API cascade
# Note: Qwen2.5-32B does NOT fit free Colab T4 (16 GB). Use API cascade.
# ---------------------------------------------------------------------------
@app.post("/worker/chat")
def worker_chat(body: ChatIn, x_worker_secret: Optional[str] = Header(None)):
    _check_secret(x_worker_secret)
    if (getattr(body, "model", None) or "").lower() in ("local", "qwen", "colab-local"):
        ans = _local_llm_generate(body.question.strip(), getattr(body, "context", "") or "")
        if ans:
            return {"answer": ans, "model": f"local/{_llm_name}", "warmed": _warmed}

    q = body.question.strip()
    ctx = (body.context or "")[:12000]
    system = (
        "You are VISION AI running on a Colab GPU worker. "
        "Be accurate, direct, and helpful. Match the user's language. "
        "Do not output large ASCII art for image requests."
    )

    # 1) Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            for mid in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
                try:
                    r = client.chat.completions.create(
                        model=mid,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": f"{ctx}\n\n{q}" if ctx else q},
                        ],
                        temperature=body.temperature,
                        max_tokens=body.max_tokens,
                    )
                    ans = (r.choices[0].message.content or "").strip()
                    if len(ans) > 10:
                        return {"answer": ans, "model": f"groq/{mid}", "warmed": _warmed}
                except Exception:
                    continue
        except Exception:
            pass

    # 2) OpenRouter free (DeepSeek-V3 preferred when available)
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1")
            for mid in (
                "deepseek/deepseek-chat-v3-0324:free",
                "deepseek/deepseek-chat:free",
                "openai/gpt-oss-20b:free",
                "openrouter/auto",
            ):
                try:
                    r = client.chat.completions.create(
                        model=mid,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": f"{ctx}\n\n{q}" if ctx else q},
                        ],
                        max_tokens=body.max_tokens,
                        temperature=body.temperature,
                    )
                    ans = (r.choices[0].message.content or "").strip()
                    if len(ans) > 10:
                        return {"answer": ans, "model": f"openrouter/{mid}", "warmed": _warmed}
                except Exception:
                    continue
        except Exception:
            pass

    # 3) Gemini
    gkey = os.getenv("GOOGLE_API_KEY")
    if gkey:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gkey)
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"{system}\n\nContext:\n{ctx}\n\nUser: {q}\nAssistant:"
            r = model.generate_content(prompt)
            ans = (r.text or "").strip()
            if len(ans) > 10:
                return {"answer": ans, "model": "gemini-2.5-flash", "warmed": _warmed}
        except Exception:
            pass

    raise HTTPException(status_code=503, detail="No chat provider available on worker")


# ---------------------------------------------------------------------------
# Streaming chat (SSE)
# ---------------------------------------------------------------------------
@app.post("/worker/chat/stream")
def worker_chat_stream(body: ChatIn, x_worker_secret: Optional[str] = Header(None)):
    _check_secret(x_worker_secret)
    q = body.question.strip()
    ctx = (body.context or "")[:12000]
    system = (
        "You are VISION AI on Colab. Be accurate and concise. Match user language."
    )

    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    def event_generator() -> Generator[str, None, None]:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
                stream = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": f"{ctx}\n\n{q}" if ctx else q},
                    ],
                    temperature=body.temperature,
                    max_tokens=body.max_tokens,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield _sse({"token": delta})
                yield _sse({"done": True, "model": "groq/openai/gpt-oss-120b"})
                return
            except Exception as e:
                yield _sse({"error": f"groq stream failed: {e}"})

        # Fallback: non-stream then chunked emit
        try:
            from openai import OpenAI
            or_key = os.getenv("OPENROUTER_API_KEY")
            if or_key:
                client = OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1")
                r = client.chat.completions.create(
                    model="openai/gpt-oss-20b:free",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": f"{ctx}\n\n{q}" if ctx else q},
                    ],
                    max_tokens=body.max_tokens,
                )
                ans = (r.choices[0].message.content or "").strip()
                step = max(20, len(ans) // 12)
                for i in range(0, len(ans), step):
                    yield _sse({"token": ans[i : i + step]})
                yield _sse({"done": True, "model": "openrouter/llama-3.3"})
                return
        except Exception as e:
            yield _sse({"error": str(e)})
        yield _sse({"done": True, "error": "no streaming provider"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Image generation — SERVERLESS FIRST, then local GPU
# ---------------------------------------------------------------------------
def _serverless_hf_image(prompt: str, hf_token: str) -> Optional[Dict[str, Any]]:
    """
    Pure serverless path via Hugging Face Inference API.
    No GPU required on the worker. Free-tier rate limits apply.
    """
    import requests as req

    api_models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/sdxl-turbo",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "runwayml/stable-diffusion-v1-5",
    ]
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    for model in api_models:
        try:
            r = req.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers=headers,
                json={
                    "inputs": prompt,
                    "options": {"wait_for_model": True},
                },
                timeout=25,
            )
            ctype = r.headers.get("Content-Type", "")
            if r.status_code == 200 and "image" in ctype:
                return {
                    "success": True,
                    "image_data": base64.b64encode(r.content).decode("utf-8"),
                    "provider": f"HF-Serverless/{model}",
                }
            if r.status_code == 503:
                time.sleep(2)
                r2 = req.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=headers,
                    json={"inputs": prompt, "options": {"wait_for_model": True}},
                    timeout=30,
                )
                if r2.status_code == 200 and "image" in r2.headers.get("Content-Type", ""):
                    return {
                        "success": True,
                        "image_data": base64.b64encode(r2.content).decode("utf-8"),
                        "provider": f"HF-Serverless/{model}",
                    }
        except Exception:
            continue
    return None


def _serverless_pollinations(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Extra free serverless endpoint (no API key required).
    Best-effort public service — not guaranteed SLA.
    """
    import requests as req
    try:
        from urllib.parse import quote
        url = (
            f"https://image.pollinations.ai/prompt/{quote(prompt[:300])}"
            f"?width=1024&height=1024&nologo=true"
        )
        r = req.get(url, timeout=35)
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
            return {
                "success": True,
                "image_data": base64.b64encode(r.content).decode("utf-8"),
                "provider": "Pollinations-Serverless",
            }
    except Exception:
        pass
    return None


@app.post("/worker/image")
def worker_image(body: ImageIn, x_worker_secret: Optional[str] = Header(None)):
    """Prefer local GPU when model is loaded — serverless first caused Railway 120s timeouts."""
    _check_secret(x_worker_secret)
    prompt = (body.prompt or "").strip()
    prompt = _enhance_image_prompt(prompt)

    # 1) Local GPU FIRST if CUDA + pipe available (or can load quickly)
    try:
        import torch
        if torch.cuda.is_available():
            if not _warmed and _pipe is None:
                # Model still downloading — do NOT block 3+ minutes here; use serverless
                print("[image] GPU present but model not loaded yet — trying serverless fallback")
            else:
                if not _warmed:
                    try:
                        _run_warmup_inference()
                    except Exception as we:
                        print(f"[image] warmup skip: {we}")
                pipe = _load_image_pipe()
                if pipe is not None:
                    # T4 free-tier defaults: 512px + few steps keeps VRAM ~3–4GB and avoids OOM
                    steps = body.steps
                    if steps is None:
                        if "turbo" in (_pipe_name or ""):
                            steps = 4  # SDXL-turbo is trained for 1–4 steps
                        elif "schnell" in (_pipe_name or ""):
                            steps = 4
                        else:
                            steps = 20
                    # Cap resolution on free T4 (1024x1024 + offload often OOMs mid-session)
                    max_side = int(os.getenv("T4_MAX_SIDE", "768") or 768)
                    w = int(body.width or 512)
                    h = int(body.height or 512)
                    w = max(256, min(w, max_side))
                    h = max(256, min(h, max_side))
                    # Align to multiples of 8 for UNet
                    w = (w // 8) * 8
                    h = (h // 8) * 8
                    kwargs = {
                        "prompt": prompt,
                        "num_inference_steps": int(steps),
                        "width": w,
                        "height": h,
                    }
                    neg = (body.negative_prompt or "").strip()
                    if neg:
                        kwargs["negative_prompt"] = neg
                    if body.guidance is not None:
                        kwargs["guidance_scale"] = float(body.guidance)
                    elif "turbo" in (_pipe_name or ""):
                        kwargs["guidance_scale"] = float(os.getenv("TURBO_GUIDANCE", "0.0") or 0.0)
                    if body.seed is not None:
                        try:
                            import torch as _t
                            kwargs["generator"] = _t.Generator(device="cuda").manual_seed(int(body.seed))
                        except Exception:
                            pass
                    # LoRA apply — validate path before load
                    if body.lora_path and pipe is not None:
                        try:
                            from pathlib import Path as _P
                            lp = _P(str(body.lora_path))
                            # Resolve under Drive loras if relative name
                            if not lp.is_file():
                                drive_loras = _P(os.getenv("VISION_DRIVE_CACHE", "/content/drive/MyDrive/vision_ai_models")) / "loras"
                                alt = drive_loras / lp.name
                                if alt.is_file():
                                    lp = alt
                            if not lp.is_file():
                                print(f"[image] LORA_MISSING: {body.lora_path}")
                            elif lp.suffix.lower() not in (".safetensors", ".pt", ".bin"):
                                print(f"[image] LORA_INVALID extension: {lp}")
                            elif lp.stat().st_size < 10000:
                                print(f"[image] LORA_INVALID size: {lp}")
                            else:
                                weight = float(body.lora_weight or 1.0)
                                weight = max(0.05, min(1.5, weight))
                                if hasattr(pipe, "load_lora_weights"):
                                    pipe.load_lora_weights(str(lp))
                                    if hasattr(pipe, "fuse_lora"):
                                        pipe.fuse_lora(lora_scale=weight)
                                    print(f"[image] LoRA loaded path={lp} weight={weight}")
                        except Exception as le:
                            print(f"[image] LoRA skip: {le}")
                    else:
                        kwargs["guidance_scale"] = 7.0
                    neg = (
                        "blurry, low quality, distorted, deformed, "
                        "text, letters, numbers, watermark, logo, subtitle, UI, "
                        "abstract symbols, garbage glyphs, random characters, "
                        "extra limbs, mutated hands, cartoon, anime, collage"
                    )
                    try:
                        kwargs["negative_prompt"] = neg
                        with torch.inference_mode():
                            out = pipe(**kwargs)
                    except TypeError:
                        kwargs.pop("negative_prompt", None)
                        with torch.inference_mode():
                            out = pipe(**kwargs)
                    img = out.images[0]
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                    del out, img, buf
                    _cuda_cleanup()
                    return {
                        "success": True,
                        "image_data": b64,
                        "provider": f"Colab-GPU/{_pipe_name}",
                        "warmed": _warmed,
                        "vram": _vram_stats(),
                        "size": f"{w}x{h}",
                        "steps": int(steps),
                    }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[image] GPU path failed: {e}")
        _cuda_cleanup()

    # 2) Fast serverless (short timeouts — must finish before Railway client gives up)
    hf = (os.getenv("HF_TOKEN") or "").strip()
    result = _serverless_hf_image(prompt, hf)
    if result:
        return result
    result = _serverless_pollinations(prompt)
    if result:
        return result

    raise HTTPException(
        status_code=503,
        detail=(
            "Image generation unavailable. Wait for Colab warmup to finish "
            "(health shows image_model loaded), keep the Boost tab open, then retry."
        ),
    )


@app.post("/worker/batch_image")
def worker_batch_image(body: BatchImageIn, x_worker_secret: Optional[str] = Header(None)):
    """
    Generate several images in one Colab session (T4-friendly).
    Processes sequentially with VRAM cleanup between items — better than many
    cold single requests that reload or idle-timeout the free session.
    """
    _check_secret(x_worker_secret)
    prompts = [str(p).strip() for p in (body.prompts or []) if str(p).strip()]
    if not prompts:
        raise HTTPException(status_code=400, detail="prompts required")
    if len(prompts) > 12:
        raise HTTPException(status_code=400, detail="max 12 prompts per batch on free T4")

    import torch
    import gc as _gc

    if not torch.cuda.is_available():
        raise HTTPException(status_code=503, detail="No CUDA GPU in this Colab runtime")

    pipe = _load_image_pipe()
    if pipe is None:
        raise HTTPException(status_code=503, detail="Image model not loaded yet — wait for warmup")

    steps = body.steps
    if steps is None:
        steps = 4 if "turbo" in (_pipe_name or "") or "schnell" in (_pipe_name or "") else 20
    max_side = int(os.getenv("T4_MAX_SIDE", "768") or 768)
    w = max(256, min(int(body.width or 512), max_side))
    h = max(256, min(int(body.height or 512), max_side))
    w, h = (w // 8) * 8, (h // 8) * 8

    images_out = []
    errors = []
    for i, raw in enumerate(prompts):
        prompt = _enhance_image_prompt(raw)
        try:
            kwargs = {
                "prompt": prompt,
                "num_inference_steps": int(steps),
                "width": w,
                "height": h,
                "guidance_scale": 0.0 if "turbo" in (_pipe_name or "") else 7.0,
            }
            with torch.inference_mode():
                out = pipe(**kwargs)
            img = out.images[0]
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            images_out.append({"index": i, "prompt": raw[:200], "image_data": b64})
            del out, img, buf
        except Exception as e:
            errors.append({"index": i, "prompt": raw[:120], "error": str(e)[:200]})
            print(f"[batch_image] item {i} failed: {e}")
        finally:
            _gc.collect()
            _cuda_cleanup()

    return {
        "success": len(images_out) > 0,
        "count": len(images_out),
        "images": images_out,
        "errors": errors,
        "provider": f"Colab-GPU/{_pipe_name}",
        "vram": _vram_stats(),
        "size": f"{w}x{h}",
        "steps": int(steps),
    }


def _enhance_image_prompt(prompt: str) -> str:
    """Sharpen prompts for SDXL-turbo without stuffing (stuffing causes garbage symbols)."""
    p = (prompt or "").strip()
    if not p:
        return "simple clean photograph, sharp focus"
    # Drop recursive enhancement tails if user/UI re-sent an enhanced prompt
    for marker in (
        "matches the prompt exactly",
        "no unrelated objects",
        "highly detailed, photorealistic",
        "photorealistic exterior of a grand mosque",
    ):
        idx = p.lower().find(marker)
        if idx > 20:
            p = p[:idx].rstrip(" ,;")
            break
    low = p.lower()
    # Keep turbo prompts SHORT — long keyword spam → symbols, charts, random text
    if len(p) > 220:
        p = p[:220].rsplit(" ", 1)[0]
    extras = []
    if any(w in low for w in ("diagram", "schematic", "circuit", "equation", "formula", "chart")):
        extras.append("clean educational diagram, readable labels, white background, minimal")
    elif any(w in low for w in ("mosque", "masjid", "minaret")):
        extras.append("photorealistic mosque architecture, accurate proportions, natural light")
    elif any(w in low for w in ("portrait", "person", "face", "man", "woman")):
        extras.append("photorealistic portrait, natural skin, sharp eyes")
    else:
        extras.append("photorealistic, sharp focus, coherent scene")
    # Explicit anti-garbage for turbo
    extras.append("no text overlay, no watermark, no random letters, no logos, no UI chrome")
    return f"{p}, " + ", ".join(extras)


# ---------------------------------------------------------------------------
# Registration / heartbeat helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Job protocol: poll main app, execute, report complete
# ---------------------------------------------------------------------------
class JobCompleteIn(BaseModel):
    job_id: str
    status: str = "completed"
    result: Optional[Dict[str, Any]] = None
    error: str = ""


@app.get("/worker/jobs/local-status")
def worker_jobs_local_status(x_worker_secret: Optional[str] = Header(None)):
    _check_secret(x_worker_secret)
    return {"ok": True, "note": "Main app owns the job queue; worker claims via MAIN_APP_URL"}


def claim_and_run_jobs_once(main_url: str, secret: str) -> dict:
    """Called from heartbeat thread — claim one job from main app and execute."""
    import requests as _req
    try:
        r = _req.post(
            f"{main_url.rstrip('/')}/api/workers/jobs/claim",
            json={"capabilities": ["t2i", "i2v"], "vram_gb": 15},
            headers={"X-Worker-Secret": secret, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code != 200:
            return {"claimed": False, "status": r.status_code}
        data = r.json() or {}
        job = data.get("job")
        if not job:
            return {"claimed": False}
        jid = job.get("id")
        jtype = job.get("type")
        result_payload = None
        err = ""
        try:
            if jtype == "image_generate":
                body = ImageIn(
                    prompt=job.get("prompt") or "",
                    negative_prompt=job.get("negative_prompt") or "",
                    width=job.get("width") or 512,
                    height=job.get("height") or 512,
                    steps=job.get("steps"),
                    guidance=job.get("guidance"),
                    seed=job.get("seed"),
                    model_id=job.get("model_id"),
                    lora_id=job.get("lora_id"),
                    lora_weight=float(job.get("lora_weight") or 1.0),
                    job_id=jid,
                )
                out = worker_image(body, x_worker_secret=secret)
                result_payload = out
            else:
                err = f"unsupported job type on this worker: {jtype}"
        except Exception as ex:
            err = str(ex)[:500]
        status = "completed" if not err else "failed"
        _req.post(
            f"{main_url.rstrip('/')}/api/workers/jobs/complete",
            json={"job_id": jid, "status": status, "result": result_payload, "error": err},
            headers={"X-Worker-Secret": secret, "Content-Type": "application/json"},
            timeout=30,
        )
        return {"claimed": True, "job_id": jid, "status": status}
    except Exception as e:
        return {"claimed": False, "error": str(e)[:200]}


def register_with_main_app(public_url: str, kind: str = "colab") -> None:
    main = (os.getenv("MAIN_APP_URL") or "").strip().rstrip("/")
    if not main:
        print("MAIN_APP_URL not set — skip auto-register")
        return
    secret = (os.getenv("WORKER_SECRET") or os.getenv("COLAB_WORKER_SECRET") or "").strip()
    payload = {
        "url": public_url.rstrip("/"),
        "kind": kind,
        "secret": secret,
        "meta": {"gpu": _gpu_name(), "host": kind, "warmed": _warmed},
    }
    try:
        import requests as req
        r = req.post(f"{main}/api/workers/register", json=payload, timeout=20)
        print("Register →", main, r.status_code, r.text[:200])
    except Exception as e:
        print("Register failed:", e)


def heartbeat_loop(public_url: str, interval: int = 120) -> None:
    # interval used for heartbeat; job claim runs every cycle

    import time as _t
    main = (os.getenv("MAIN_APP_URL") or "").strip().rstrip("/")
    if not main:
        return
    secret = (os.getenv("WORKER_SECRET") or os.getenv("COLAB_WORKER_SECRET") or "").strip()

    def _run():
        import requests as req
        while True:
            try:
                req.post(
                    f"{main}/api/workers/heartbeat",
                    json={"url": public_url.rstrip("/"), "secret": secret, "warmed": _warmed},
                    timeout=15,
                )
            except Exception:
                pass
            _t.sleep(interval)

    threading.Thread(target=_run, daemon=True).start()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    print(f"[worker] Starting on 0.0.0.0:{port}  (warmup runs in background)")
    uvicorn.run(app, host="0.0.0.0", port=port)



@app.get("/worker/drive")
def worker_drive_status():
    """Explicit Drive/LoRA readiness for the main app."""
    try:
        root = os.getenv("VISION_DRIVE_CACHE", "/content/drive/MyDrive/vision_ai_models")
        mount = Path("/content/drive")
        loras = Path(root) / "loras"
        ready = mount.exists() and (mount / "MyDrive").exists()
        files = []
        if loras.is_dir():
            files = [f.name for f in loras.glob("*.safetensors")][:50]
        return {
            "ok": ready,
            "state": "DRIVE_READY" if ready else "DRIVE_UNAVAILABLE",
            "root": root,
            "loras_dir": str(loras),
            "loras": files,
        }
    except Exception as e:
        return {"ok": False, "state": "DRIVE_UNAVAILABLE", "error": str(e)}
