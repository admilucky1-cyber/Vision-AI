"""
Vision AI v3.0 — Skill Router
Register lightweight text skills and suggest new ones via LLM.
Skills are pure callables: (prompt: str, context: dict) -> str
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("vision-ai.skills")

SkillFn = Callable[[str, Dict[str, Any]], str]


def _skill_summarize(prompt: str, context: Dict[str, Any]) -> str:
    text = (context.get("text") or prompt or "").strip()
    if not text:
        return "No text provided to summarize."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    keep = sentences[: max(3, min(8, len(sentences) // 4 or 3))]
    return "Summary:\n- " + "\n- ".join(s.strip() for s in keep if s.strip())


def _skill_translate_urdu_hint(prompt: str, context: Dict[str, Any]) -> str:
    return (
        "Urdu translation skill engaged. Ask the main chat model:\n"
        f"Translate the following to clear Urdu:\n{prompt}"
    )


def _skill_exam_steps(prompt: str, context: Dict[str, Any]) -> str:
    return (
        "Exam solver skill:\n"
        "1) Restate the question\n"
        "2) List known data / formulas\n"
        "3) Solve step by step\n"
        "4) Box the final answer\n"
        f"Question:\n{prompt}"
    )


def _skill_code_review(prompt: str, context: Dict[str, Any]) -> str:
    return (
        "Code review skill checklist:\n"
        "- Correctness & edge cases\n"
        "- Readability\n"
        "- Security\n"
        "- Performance\n"
        f"Code / request:\n{prompt}"
    )


class SkillRouter:
    def __init__(self) -> None:
        self.INSTALLED_SKILLS: Dict[str, Dict[str, Any]] = {
            "summarize": {
                "name": "Summarize",
                "description": "Condense long text into bullet points",
                "fn": _skill_summarize,
                "builtin": True,
            },
            "urdu_hint": {
                "name": "Urdu Hint",
                "description": "Prepare a clear Urdu translation prompt",
                "fn": _skill_translate_urdu_hint,
                "builtin": True,
            },
            "exam_steps": {
                "name": "Exam Steps",
                "description": "Structure physics/math answers step by step",
                "fn": _skill_exam_steps,
                "builtin": True,
            },
            "code_review": {
                "name": "Code Review",
                "description": "Checklist-driven code review framing",
                "fn": _skill_code_review,
                "builtin": True,
            },
        }
        self._dynamic_code: Dict[str, str] = {}

    def list_skills(self) -> List[Dict[str, Any]]:
        out = []
        for sid, meta in self.INSTALLED_SKILLS.items():
            out.append({
                "id": sid,
                "name": meta.get("name") or sid,
                "description": meta.get("description") or "",
                "builtin": bool(meta.get("builtin")),
            })
        return out

    def run(self, skill_id: str, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        meta = self.INSTALLED_SKILLS.get(skill_id)
        if not meta:
            return f"Skill '{skill_id}' is not installed."
        fn: SkillFn = meta["fn"]
        try:
            return fn(prompt or "", context or {})
        except Exception as e:
            logger.exception("skill %s failed", skill_id)
            return f"Skill error: {e}"

    def install_skill(self, name: str, code: str, description: str = "") -> Dict[str, Any]:
        """
        Register a dynamic skill from a restricted Python expression body.
        The code must define: def run(prompt, context): ...
        """
        safe_id = re.sub(r"[^a-z0-9_]+", "_", (name or "custom").lower()).strip("_") or "custom"
        if safe_id in self.INSTALLED_SKILLS and self.INSTALLED_SKILLS[safe_id].get("builtin"):
            return {"ok": False, "error": "Cannot overwrite builtin skill"}

        # Extremely small sandbox: no imports, no dunders
        if re.search(r"\bimport\b|__|open\s*\(|exec\s*\(|eval\s*\(", code):
            return {"ok": False, "error": "Unsafe code rejected"}

        ns: Dict[str, Any] = {}
        try:
            compiled = compile(code, f"<skill:{safe_id}>", "exec")
            exec(compiled, {"__builtins__": {"len": len, "str": str, "int": int, "float": float, "min": min, "max": max, "range": range}}, ns)
            fn = ns.get("run")
            if not callable(fn):
                return {"ok": False, "error": "Code must define run(prompt, context)"}
        except Exception as e:
            return {"ok": False, "error": f"Compile error: {e}"}

        self.INSTALLED_SKILLS[safe_id] = {
            "name": name or safe_id,
            "description": description or "Custom skill",
            "fn": fn,
            "builtin": False,
        }
        self._dynamic_code[safe_id] = code
        return {"ok": True, "id": safe_id}

    def remove_skill(self, skill_id: str) -> Dict[str, Any]:
        meta = self.INSTALLED_SKILLS.get(skill_id)
        if not meta:
            return {"ok": False, "error": "not found"}
        if meta.get("builtin"):
            return {"ok": False, "error": "Cannot remove builtin skill"}
        del self.INSTALLED_SKILLS[skill_id]
        self._dynamic_code.pop(skill_id, None)
        return {"ok": True}

    
    def suggest_skills(self, user_prompt: str) -> List[str]:
        """Keyword → skill recommendations for the Skill Market / agent."""
        p = (user_prompt or "").lower()
        out: List[str] = []
        rules = [
            (("exam", "paper", "mcq", "mark scheme", "physics", "solve question"), "Exam Steps"),
            (("pdf", "notes", "summarize document", "revision"), "Summarize"),
            (("urdu", "translate", "tarjuma"), "Urdu Hint"),
            (("code", "python", "bug", "refactor", "function"), "Code Review"),
            (("youtube", "video", "transcript", "quiz from video"), "YouTube Summarizer"),
            (("image", "diagram", "draw", "generate picture"), "Image Prompt Craft"),
            (("interview", "cv", "resume"), "Career Coach"),
        ]
        for keys, label in rules:
            if any(k in p for k in keys):
                out.append(label)
        # installed skill names
        for meta in self.INSTALLED_SKILLS.values():
            name = meta.get("name") or ""
            if name and name not in out and any(w in p for w in name.lower().split()):
                out.append(name)
        if not out:
            out = ["Summarize", "Exam Steps"]
        # unique preserve order
        seen = set()
        uniq = []
        for x in out:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        return uniq[:8]

    def suggest_skill(self, user_prompt: str) -> str:
        """Heuristic suggestion (LLM optional if available)."""
        p = (user_prompt or "").lower()
        ideas = []
        if "pdf" in p or "exam" in p:
            ideas.append("exam_steps — step-by-step exam answering")
        if "code" in p or "bug" in p:
            ideas.append("code_review — structured review checklist")
        if "urdu" in p or "translate" in p:
            ideas.append("urdu_hint — translation framing")
        if "summary" in p or "summarize" in p:
            ideas.append("summarize — bullet condensation")
        if not ideas:
            ideas.append("Create a custom skill that formats answers for your domain (e.g. physics lab reports).")
        try:
            from services.llm import ask_ai
            tip = ask_ai(
                f"Suggest one small reusable chat skill for this user need (one sentence): {user_prompt}",
                system="Be concise. Return only the skill idea.",
            )
            if tip:
                ideas.append(str(tip)[:400])
        except Exception:
            pass
        return "Skill ideas:\n- " + "\n- ".join(ideas)




skill_router = SkillRouter()

__all__ = ["SkillRouter", "skill_router"]
