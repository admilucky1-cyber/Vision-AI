"""Device / runtime tier profiler — guides local vs cloud model choice (nimbus-style, practical)."""
from __future__ import annotations

import os
import platform
from typing import Any, Dict


def _mem_gb() -> float:
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 ** 3), 2)
    except Exception:
        try:
            # Linux
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024 ** 2), 2)
        except Exception:
            pass
    return 0.0


def _cpu_count() -> int:
    return os.cpu_count() or 1


def profile_runtime() -> Dict[str, Any]:
    """Score this host (server or hint for client)."""
    cores = _cpu_count()
    ram = _mem_gb()
    system = platform.system()
    machine = platform.machine()
    # Simple tier score 0–100
    score = min(100, int(cores * 8 + min(ram, 32) * 2))
    if ram < 4 or cores <= 2:
        tier = "edge"
        quant = "q2_K / q3_K — tiny models only (0.5B–1.5B)"
        prefer = ["qwen2.5-0.5b", "phi-3-mini", "gemini-flash", "groq-fast"]
    elif ram < 12 or cores <= 4:
        tier = "mobile_desktop"
        quant = "q4_K_M — small/medium (1.5B–7B if local)"
        prefer = ["qwen2.5-3b", "llama-3.2-3b", "groq", "gemini-flash"]
    elif ram < 24:
        tier = "workstation"
        quant = "q5_K_M / q8 — up to ~13B local comfortable"
        prefer = ["qwen2.5-7b", "llama-3.1-8b", "groq", "deepseek"]
    else:
        tier = "server"
        quant = "fp16 / q8 — large local or full cloud cascade"
        prefer = ["auto-cascade", "deepseek", "gemini-pro", "local-13b+"]

    ollama = bool(os.getenv("OLLAMA_BASE_URL") or os.getenv("OPENAI_COMPAT_BASE_URL"))
    return {
        "tier": tier,
        "score": score,
        "cpu_cores": cores,
        "ram_gb": ram,
        "system": system,
        "machine": machine,
        "quantization_advice": quant,
        "preferred_models": prefer,
        "local_endpoint_configured": ollama,
        "recommendation": (
            "Use free cloud cascade (Groq/Gemini) on edge tiers; "
            "enable Ollama/LM Studio only if RAM allows."
            if tier in ("edge", "mobile_desktop")
            else "Cloud cascade or local mid-size models are both fine."
        ),
    }


def simple_arithmetic_fallback(text: str) -> Dict[str, Any]:
    """Deterministic calculator when LLM is down — longest digit-bearing match."""
    import re
    from services.math_solver import solve_expression

    raw = (text or "").strip()
    if not raw:
        return {"ok": False, "error": "empty"}
    # Prefer explicit math-looking chunks
    candidates = re.findall(
        r"[0-9][0-9\.\s\+\-\*\/\^\(\)]{0,80}[0-9\)]",
        raw.replace("×", "*").replace("÷", "/"),
    )
    if not candidates:
        # whole string if only math symbols
        if re.fullmatch(r"[\d\.\s\+\-\*\/\^\(\)]+", raw):
            candidates = [raw]
    if not candidates:
        return {"ok": False, "error": "no_expression"}
    # longest candidate with a digit
    candidates = sorted(candidates, key=len, reverse=True)
    expr = candidates[0].strip()
    # pure simple eval path without sympy
    if re.fullmatch(r"[\d\.\s\+\-\*\/\(\)]+", expr):
        try:
            # safe: only digits and operators
            val = eval(expr, {"__builtins__": {}}, {})  # noqa: S307 — filtered charset
            return {"ok": True, "input": expr, "result": str(val), "mode": "arithmetic"}
        except Exception:
            pass
    return solve_expression(expr)
