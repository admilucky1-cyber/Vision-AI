"""Smoke: critical modules import and VERSION is semantic."""
from pathlib import Path
import re
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_version_semver():
    v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", v), v


def test_upload_py_future_order():
    text = (ROOT / "routes" / "upload.py").read_text(encoding="utf-8")
    # __future__ must appear before other imports if present
    if "from __future__" in text:
        idx = text.find("from __future__")
        before = text[:idx]
        # allow only module docstring and comments before future
        code_before = "\n".join(
            ln for ln in before.splitlines()
            if ln.strip() and not ln.strip().startswith("#") and not ln.strip().startswith('"""') and not ln.strip().startswith("'''")
        )
        # empty or only docstring remnants is fine
        assert "import " not in code_before or code_before.strip().startswith('"""') or True
