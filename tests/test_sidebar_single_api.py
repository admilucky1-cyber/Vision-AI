"""Ensure index.js does not define multiple full sidebar controllers."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "frontend/static/js/index.js").read_text(encoding="utf-8")


def test_single_toggle_assignment_to_controller():
    # Early stubs + final controller assignment are OK; forbid recursive self-call body
    assert "if (typeof window.toggleSidebar === 'function') {\n        window.toggleSidebar();" not in JS
    assert "window.__vaSidebar" in JS


def test_auth_js_canonical_keys():
    auth = (ROOT / "frontend/static/js/auth.js").read_text(encoding="utf-8")
    assert "vision_ai_access_token" in auth
    assert "VisionAuth" in auth
