"""
Vision AI — ONE-CLICK GPU Boost for Google Colab
================================================
Reads Colab Secrets reliably (exact names + aliases + interactive fallback).

CRITICAL Colab rules (why "secrets exist but worker sees none"):
  1) Secret name must be EXACT (HF_TOKEN not hf_token / HUGGING_FACE).
  2) Each secret needs the blue "Notebook access" toggle ON for THIS notebook.
  3) Runtime → Restart runtime after adding/toggling secrets.
  4) Same Google account that owns the secrets must own the notebook.
"""

from __future__ import annotations

import os
import sys
import time
import threading
import asyncio
import traceback

DEFAULT_APP = "https://vision-ai-v2-production.up.railway.app"
DEFAULT_SECRET = "vision-colab-secret"
REPO = "https://github.com/admilucky1-cyber/Vision-AI-v2.git"
ROOT = "/content/Vision-AI"
ENV_FILE = "/content/.vision_boost.env"


def _userdata_get(name: str) -> tuple:
    """Return (value, error_reason). value='' if missing/denied."""
    try:
        from google.colab import userdata
# After Runtime→Restart, Colab injects secrets into the environment
    except Exception as e:
        return "", f"google.colab.userdata unavailable: {e}"
    try:
        got = userdata.get(name)
        if got is None:
            return "", "not found"
        v = str(got).strip()
        if not v:
            return "", "empty value"
        return v, ""
    except Exception as e:
        err = type(e).__name__ + ": " + str(e)[:120]
        return "", err


def _secret(name: str, default: str = "", aliases=None) -> str:
    names = [name] + list(aliases or [])
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v:
            return v
    for n in names:
        v, _err = _userdata_get(n)
        if v:
            os.environ[n] = v
            os.environ[name] = v
            return v
    return (default or "").strip()



def ensure_drive_cache():
    """Phase 1: mount Drive and create model cache folder (Colab only)."""
    try:
        from google.colab import drive
        if not os.path.isdir("/content/drive/MyDrive"):
            print("Mounting Google Drive for model cache...")
            drive.mount("/content/drive")
        cache = "/content/drive/MyDrive/vision_ai_models"
        os.makedirs(cache, exist_ok=True)
        os.environ.setdefault("VISION_DRIVE_CACHE", cache)
        os.environ.setdefault("HF_HOME", os.path.join(cache, "hf"))
        print(f"✅ Drive model cache: {cache}")
        return cache
    except Exception as e:
        print(f"Drive cache optional skip: {e}")
        return ""


def debug_secrets():
    candidates = [
        ("NGROK_TOKEN", ["NGROK_AUTHTOKEN", "NGROK"]),
        ("HF_TOKEN", ["HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HF_API_TOKEN"]),
        ("GROQ_API_KEY", ["GROQ_KEY"]),
        ("GOOGLE_API_KEY", ["GEMINI_API_KEY", "GOOGLE_KEY"]),
        ("OPENROUTER_API_KEY", ["OPENROUTER_KEY"]),
        ("WORKER_SECRET", ["COLAB_WORKER_SECRET"]),
        ("MAIN_APP_URL", []),
        ("TELEGRAM_BOT_TOKEN", []),
    ]
    print("--- Secret check (names only) ---")
    found = 0
    for primary, aliases in candidates:
        v, err = _userdata_get(primary)
        if v:
            found += 1
            print(f"  OK  {primary}")
            continue
        got_alias = False
        for a in aliases:
            av, _ = _userdata_get(a)
            if av:
                found += 1
                print(f"  OK  {primary}  (via alias {a})")
                os.environ[primary] = av
                got_alias = True
                break
        if got_alias:
            continue
        reason = err or "not found"
        print(f"  --  {primary}  [{reason}]")
    if found == 0:
        print()
        print("No secrets readable. Fix ALL of these:")
        print("  1) Name EXACT: HF_TOKEN, NGROK_TOKEN, GROQ_API_KEY, ...")
        print("  2) Key icon -> Secrets -> each secret -> Notebook access = ON (blue)")
        print("  3) Runtime -> Restart runtime, then re-run this cell")
        print("  4) Notebook must be owned by the same Google account as the secrets")
    else:
        print(f"Readable: {found}/{len(candidates)}")
    print("---------------------------------")
    return found


def _prompt(label: str) -> str:
    try:
        return input(label).strip()
    except EOFError:
        return ""


def ensure_project():
    import subprocess
    if not os.path.isdir(ROOT):
        subprocess.check_call(["git", "clone", "--depth", "1", REPO, ROOT])
    else:
        try:
            subprocess.check_call(
                ["git", "-C", ROOT, "pull", "--ff-only"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
    os.chdir(ROOT)
    if not os.path.isfile("colab_worker_server.py"):
        raise SystemExit("colab_worker_server.py missing — git pull/push the repo")


def pip_install():
    import subprocess
    pkgs = [
        "fastapi",
        "uvicorn[standard]",
        "pyngrok",
        "requests==2.32.4",
        "openai",
        "google-generativeai",
        "pillow",
        "pydantic",
        "python-dotenv",
        "huggingface_hub",
    ]
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *pkgs])


def write_env_file(vars_dict: dict):
    lines = []
    for k, v in vars_dict.items():
        if v:
            lines.append(f"{k}={v}")
    os.makedirs("/content", exist_ok=True)
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    for k, v in vars_dict.items():
        if v:
            os.environ[k] = v
    print(f"Wrote {ENV_FILE} ({len(lines)} keys)")


def run_uvicorn():
    try:
        if os.path.isfile(ENV_FILE):
            try:
                from dotenv import load_dotenv
                load_dotenv(ENV_FILE, override=True)
            except Exception:
                pass
            with open(ENV_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    if k and v:
                        os.environ[k] = v

        import uvicorn
        config = uvicorn.Config(
            "colab_worker_server:app",
            host="0.0.0.0",
            port=7860,
            log_level="info",
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())
    except Exception:
        print("WORKER THREAD CRASH:")
        traceback.print_exc()


def hf_login(token: str):
    if not token:
        return
    try:
        from huggingface_hub import login
        login(token=token, add_to_git_credential=False)
        print("HF hub login: OK")
    except Exception as e:
        print(f"HF hub login skip: {e}")


def main():
    print("=== Vision AI One-Click Boost ===")
    print("Secrets: Key icon → Notebook access ON → Runtime → Restart runtime, then re-run")
    ensure_drive_cache()
    debug_secrets()

    ensure_project()
    pip_install()

    main_url = _secret("MAIN_APP_URL", DEFAULT_APP).rstrip("/")
    secret = (
        _secret("WORKER_SECRET", "", aliases=["COLAB_WORKER_SECRET"])
        or DEFAULT_SECRET
    )
    ngrok_token = _secret("NGROK_TOKEN", "", aliases=["NGROK_AUTHTOKEN", "NGROK"])
    hf = _secret(
        "HF_TOKEN",
        "",
        aliases=["HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HF_API_TOKEN"],
    )
    groq = _secret("GROQ_API_KEY", "", aliases=["GROQ_KEY"])
    google = _secret("GOOGLE_API_KEY", "", aliases=["GEMINI_API_KEY", "GOOGLE_KEY"])
    openrouter = _secret("OPENROUTER_API_KEY", "", aliases=["OPENROUTER_KEY"])

    if not ngrok_token:
        print("NGROK_TOKEN not readable from Secrets.")
        print("Exact name must be: NGROK_TOKEN")
        print("https://dashboard.ngrok.com/get-started/your-authtoken")
        ngrok_token = _prompt("Or paste ngrok token now: ")
    if not ngrok_token:
        raise SystemExit("NGROK_TOKEN required")

    if not hf:
        print("HF_TOKEN not readable — FLUX/local downloads need it.")
        print("https://huggingface.co/settings/tokens")
        hf = _prompt("Paste HF_TOKEN (or Enter to skip): ")

    if not groq and not openrouter and not google:
        print("No chat API key readable (GROQ / OPENROUTER / GOOGLE).")
        print("Worker chat will 503 without at least one.")
        groq = _prompt("Paste GROQ_API_KEY (or Enter to skip): ")
        if not groq:
            openrouter = _prompt("Paste OPENROUTER_API_KEY (or Enter to skip): ")

    write_env_file(
        {
            "MAIN_APP_URL": main_url,
            "WORKER_SECRET": secret,
            "COLAB_WORKER_SECRET": secret,
            "HF_TOKEN": hf,
            "HUGGING_FACE_HUB_TOKEN": hf,
            "GROQ_API_KEY": groq,
            "GOOGLE_API_KEY": google,
            "OPENROUTER_API_KEY": openrouter,
            "LOW_VRAM": "1",
        }
    )

    hf_login(hf)

    from pyngrok import ngrok, conf
    conf.get_default().auth_token = ngrok_token

    threading.Thread(target=run_uvicorn, daemon=True).start()
    print("Worker starting on :7860 ...")

    import requests as req
    headers = {"X-Worker-Secret": secret}

    ready = False
    last_err = ""
    for _ in range(40):
        try:
            h = req.get(
                "http://127.0.0.1:7860/worker/health",
                headers=headers,
                timeout=2,
            )
            if h.status_code == 200:
                ready = True
                print("Local worker OK:", h.text[:160])
                break
            last_err = f"HTTP {h.status_code} {h.text[:80]}"
        except Exception as e:
            last_err = str(e)
        time.sleep(0.5)

    if not ready:
        print("WARNING: local worker not ready:", last_err)

    public = ngrok.connect(7860, bind_tls=True).public_url
    print("Public:", public)

    r = req.post(
        f"{main_url}/api/workers/register",
        json={
            "url": public,
            "kind": "colab",
            "secret": secret,
            "meta": {"one_click": True, "hf": bool(hf), "groq": bool(groq)},
        },
        timeout=25,
    )
    print("Register:", r.status_code, r.text[:240])

    def hb():
        while True:
            try:
                req.post(
                    f"{main_url}/api/workers/heartbeat",
                    json={"url": public, "secret": secret},
                    timeout=15,
                )
            except Exception:
                pass
            time.sleep(90)

    threading.Thread(target=hb, daemon=True).start()

    try:
        ph = req.get(f"{public}/worker/health", headers=headers, timeout=20)
        print("Public health:", ph.status_code, ph.text[:200])
    except Exception as e:
        print("Public health check failed:", e)

    print("=" * 50)
    print("DONE — leave this tab open")
    print("HF_TOKEN:", "yes" if hf else "NO — FLUX/HF API limited")
    print("GROQ:", "yes" if groq else "no")
    print("OPENROUTER:", "yes" if openrouter else "no")
    print("GOOGLE:", "yes" if google else "no")
    print("Check:", f"{main_url}/boost")
    print("=" * 50)
    if not hf:
        print("TIP: Without HF_TOKEN, local FLUX fails and HF Inference rate-limits.")
    if not (groq or openrouter or google):
        print("TIP: Without a chat key, POST /worker/chat returns 503.")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("Stopped")


if __name__ == "__main__":
    main()
