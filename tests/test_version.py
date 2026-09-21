from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_version_file():
    import re
    v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.match(r"^\d+\.\d+\.\d+$", v), f"VERSION must be semver, got: {v!r}"
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version\s*=\s*"([^"]+)"', metadata, re.MULTILINE)
    assert declared and declared.group(1) == v


def test_colab_boost_future_import():
    text = (ROOT / "colab_one_click_boost.py").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert "from __future__ import annotations" in text
    idx_future = text.find("from __future__ import annotations")
    before = text[:idx_future]
    assert "import " not in before.split('\"\"\"')[-1] if '\"\"\"' in before else "import " not in before
