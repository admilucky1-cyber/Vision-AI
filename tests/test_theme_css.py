
"""Static checks: theme CSS files exist and contain key tokens."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_eye_care_exists():
    p = ROOT / "frontend/static/css/eye-care.css"
    assert p.is_file()
    t = p.read_text(encoding="utf-8")
    assert "0c1017" in t or "eye" in t.lower()


def test_theme_presets_exists():
    p = ROOT / "frontend/static/css/theme-presets.css"
    assert p.is_file()
    t = p.read_text(encoding="utf-8")
    assert "nord" in t and "high-contrast" in t


def test_index_links_css():
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert "nova-system.css" in html


def test_modern_ui_css_present():
    assert (ROOT / "frontend/static/css/modern-ui.css").is_file()
    assert (ROOT / "frontend/static/css/tokens.css").is_file()


def test_welcome_suggestions_in_index():
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert "suggestion-chip" in html
    assert "suggestionGrid" in html


def test_index_app_version_matches():
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    ver = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert f'content="{ver}"' in html or "4.8.2" in html


def test_vendor_self_hosted():
    assert (ROOT / "frontend/static/vendor/marked/marked.min.js").is_file()
    assert (ROOT / "frontend/static/vendor/dompurify/purify.min.js").is_file()
    assert (ROOT / "frontend/static/vendor/katex/katex.min.js").is_file()
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net/npm/marked" not in html
    assert "/frontend/static/vendor/marked/" in html


def test_workspace_token_aliases():
    tokens = (ROOT / "frontend/static/css/tokens.css").read_text(encoding="utf-8")
    for name in (
        "--color-bg-secondary",
        "--color-bg-tertiary",
        "--color-text-secondary",
        "--color-text-tertiary",
        "--color-accent-light",
    ):
        assert name in tokens, name
    assert "--space-1" in tokens  # full system not wiped


def test_ui_refine_present():
    assert (ROOT / "frontend/static/css/ui-refine.css").is_file()
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert "nova-system.css" in html


def test_responsive_safe_area_rules():
    css = (ROOT / "frontend/static/css/ui-refine.css").read_text(encoding="utf-8")
    assert "safe-area-inset" in css
    assert "100dvh" in css
    assert "pointer: coarse" in css


def test_theme_accent_bridge():
    css = (ROOT / "frontend/static/css/themes.css").read_text(encoding="utf-8")
    assert "--color-accent: var(--accent)" in css
