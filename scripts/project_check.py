#!/usr/bin/env python3
"""Vision AI project check — HTML/JS/CSS/Python/Rust/C++ surface scan."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
issues: list[str] = []
ok: list[str] = []

def check_html():
    for p in (ROOT / "frontend").rglob("*.html"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if "<html" in t.lower() and 'charset' not in t.lower():
            issues.append(f"{p.relative_to(ROOT)}: missing charset")
        if t.count("<html") != t.count("</html>") and "</html>" in t:
            issues.append(f"{p.relative_to(ROOT)}: html tag imbalance")
        # unclosed script rough
        if t.count("<script") > t.count("</script>"):
            issues.append(f"{p.relative_to(ROOT)}: possible unclosed script")
        else:
            ok.append(f"html:{p.name}")

def check_js():
    for p in (ROOT / "frontend/static/js").glob("*.js"):
        t = p.read_text(encoding="utf-8", errors="replace")
        # very rough brace balance
        if t.count("{") != t.count("}"):
            issues.append(f"{p.relative_to(ROOT)}: brace imbalance {{ }}")
        if t.count("(") != t.count(")"):
            issues.append(f"{p.relative_to(ROOT)}: paren imbalance")
        else:
            ok.append(f"js:{p.name}")

def check_css():
    for p in (ROOT / "frontend/static/css").glob("*.css"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if t.count("{") != t.count("}"):
            issues.append(f"{p.relative_to(ROOT)}: CSS brace imbalance")
        else:
            ok.append(f"css:{p.name}")

def check_python():
    import py_compile
    for p in list((ROOT / "services").rglob("*.py")) + list((ROOT / "routes").rglob("*.py")):
        try:
            py_compile.compile(str(p), doraise=True)
            ok.append(f"py:{p.name}")
        except Exception as e:
            issues.append(f"{p.relative_to(ROOT)}: {e}")
    for name in ("main.py", "run.py"):
        p = ROOT / name
        if p.exists():
            try:
                py_compile.compile(str(p), doraise=True)
                ok.append(f"py:{name}")
            except Exception as e:
                issues.append(f"{name}: {e}")

def check_rust():
    for p in ROOT.rglob("*.rs"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if "fn main" not in t and "pub fn" not in t and "fn " not in t:
            issues.append(f"{p.relative_to(ROOT)}: no fn found (empty?)")
        else:
            ok.append(f"rs:{p.name}")

def check_cpp():
    for p in list(ROOT.rglob("*.cpp")) + list(ROOT.rglob("*.c")) + list(ROOT.rglob("*.h")):
        ok.append(f"c/cpp present:{p.name}")

def main():
    check_html()
    check_js()
    check_css()
    check_python()
    check_rust()
    check_cpp()
    print(f"OK items: {len(ok)}")
    print(f"Issues: {len(issues)}")
    for i in issues[:50]:
        print("ISSUE:", i)
    if issues:
        sys.exit(1)
    print("PROJECT_CHECK_PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
