"""Smoke: critical modules import and VERSION is 4.x or 5.x."""
from pathlib import Path
import re
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_version_semver():
    v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.match(r"^[45]\.\d+\.\d+$", v), v


def test_upload_py_future_order():
    text = (ROOT / "routes/upload.py").read_text(encoding="utf-8")
    # compile
    ast.parse(text)
    future = text.find("from __future__")
    assert future > 0
    assert text.find("from routes.login") == -1 or text.find("from routes.login") > future or '"""' in text[:future]


def test_drive_state_import():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "drive_state", ROOT / "services" / "drive_state.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "detect_drive_state")
    assert hasattr(mod, "sanitize_worker_path")
    path, err = mod.sanitize_worker_path("../../etc/passwd")
    assert path is None and err is not None


def test_auth_js_exists():
    assert (ROOT / "frontend/static/js/auth.js").is_file()


def test_models_route_has_migrations_key():
    text = (ROOT / "routes/models.py").read_text(encoding="utf-8")
    assert "migrations" in text
