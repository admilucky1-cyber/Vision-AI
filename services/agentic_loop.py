"""
Vision AI v5.3 — Agentic execution + self-correction loop.
Restricted Python sandbox (no file/network/OS). Iterative fix on runtime errors.
"""
from __future__ import annotations

import ast
import io
import logging
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vision-ai.agentic")

MAX_STEPS = 4
EXEC_TIMEOUT_HINT = 3.0  # soft; enforced by complexity limits

_FORBIDDEN = {
    "open", "exec", "eval", "compile", "__import__", "input",
    "breakpoint", "exit", "quit", "help", "memoryview",
}


class RestrictedPythonError(Exception):
    pass


def _validate_ast(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise RestrictedPythonError(f"SyntaxError: {e}") from e
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise RestrictedPythonError("Imports are not allowed in the sandbox")
        if isinstance(node, ast.Attribute):
            if isinstance(node.attr, str) and node.attr.startswith("__"):
                raise RestrictedPythonError(f"Attribute {node.attr} blocked")
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN:
            raise RestrictedPythonError(f"Name {node.id} blocked")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN:
                raise RestrictedPythonError(f"Call {node.func.id} blocked")


def _safe_builtins() -> Dict[str, Any]:
    allowed = {
        "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
        "format", "frozenset", "int", "len", "list", "map", "max", "min",
        "pow", "print", "range", "reversed", "round", "set", "slice", "sorted",
        "str", "sum", "tuple", "zip", "True", "False", "None",
    }
    b = {k: getattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__, k)
         if not isinstance(__builtins__, dict) else __builtins__.get(k)
         for k in allowed}
    # fix when __builtins__ is module
    import builtins as _bi
    out = {k: getattr(_bi, k) for k in allowed if hasattr(_bi, k)}
    out["__build_class__"] = _bi.__build_class__
    return out


def execute_python(code: str) -> Dict[str, Any]:
    """Run restricted Python; return stdout/stderr/result/error."""
    _validate_ast(code)
    if len(code) > 12000:
        raise RestrictedPythonError("Code too large for sandbox")
    g: Dict[str, Any] = {"__builtins__": _safe_builtins()}
    l: Dict[str, Any] = {}
    stdout = io.StringIO()
    stderr = io.StringIO()
    result = None
    err = None
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            # Prefer eval of last expr if simple
            tree = ast.parse(code)
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                *body, last = tree.body
                if body:
                    exec(compile(ast.Module(body=body, type_ignores=[]), "<agent>", "exec"), g, l)
                result = eval(compile(ast.Expression(last.value), "<agent>", "eval"), g, l)
            else:
                exec(compile(code, "<agent>", "exec"), g, l)
                result = l.get("result", l.get("answer"))
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    return {
        "ok": err is None,
        "stdout": stdout.getvalue()[-4000:],
        "stderr": stderr.getvalue()[-2000:],
        "result": repr(result) if result is not None else None,
        "error": err,
    }


def _heuristic_patch(code: str, error: str) -> Optional[str]:
    """Lightweight deterministic patches before LLM (optional offline)."""
    if "NameError" in error and "np" in error:
        return "import math as np  # patched alias blocked — use pure python\n" + code.replace("np.", "")
    if "ZeroDivisionError" in error:
        return code.replace("/ 0", "/ (1e-12)").replace("/0", "/(1e-12)")
    if "SyntaxError" in error and ":" in error:
        return None
    return None


def agentic_run(
    code: str,
    max_steps: int = MAX_STEPS,
    repair_fn=None,
) -> Dict[str, Any]:
    """
    Execute → on failure optionally call repair_fn(code, error) → retry.
    repair_fn can be an LLM wrapper; if None, only heuristic patches.
    """
    steps: List[Dict[str, Any]] = []
    current = code
    for step in range(1, max_steps + 1):
        try:
            out = execute_python(current)
        except RestrictedPythonError as e:
            out = {"ok": False, "stdout": "", "stderr": "", "result": None, "error": str(e)}
        steps.append({"step": step, "code": current, **out})
        if out.get("ok"):
            return {
                "ok": True,
                "final_code": current,
                "steps": steps,
                "stdout": out.get("stdout"),
                "result": out.get("result"),
                "corrected": step > 1,
            }
        err = out.get("error") or "unknown error"
        patched = _heuristic_patch(current, err)
        if repair_fn:
            try:
                patched = repair_fn(current, err) or patched
            except Exception as e:
                logger.warning("repair_fn failed: %s", e)
        if not patched or patched.strip() == current.strip():
            return {
                "ok": False,
                "final_code": current,
                "steps": steps,
                "error": err,
                "corrected": step > 1,
            }
        current = patched
    return {
        "ok": False,
        "final_code": current,
        "steps": steps,
        "error": steps[-1].get("error") if steps else "max steps",
        "corrected": True,
    }
