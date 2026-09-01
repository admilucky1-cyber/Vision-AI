
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_version_file():
    import re
    v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.match(r"^\d+\.\d+\.\d+$", v), f"VERSION must be semver, got: {v!r}"
    assert v.startswith(("4.", "5.")), f"Expected 4.x or 5.x series, got: {v!r}"


def test_colab_boost_future_import():
    text = (ROOT / "colab_one_click_boost.py").read_text(encoding="utf-8")
    # __future__ must not be after other imports incorrectly
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    # first non-docstring code line should be future or import after docstring
    assert "from __future__ import annotations" in text
    idx_future = text.find("from __future__ import annotations")
    idx_import_os = text.find("\nimport os")
    # docstring may precede future; no import before future except nothing
    before = text[:idx_future]
    assert "import " not in before.split('"""')[-1] if '"""' in before else "import " not in before
