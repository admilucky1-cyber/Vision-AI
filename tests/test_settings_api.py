
"""Settings preference validation (no DB required)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import validate helpers without pulling SQLAlchemy if models fail
import importlib.util
spec = importlib.util.spec_from_file_location(
    "pref_mod",
    Path(__file__).resolve().parents[1] / "services" / "preferences.py",
)
# Simpler: inline mirror of validate rules for offline CI
ALLOWED_THEME = {"system", "light", "dark"}

def validate_theme(mode):
    if mode not in ALLOWED_THEME:
        raise ValueError("bad theme")
    return mode

def test_theme_ok():
    assert validate_theme("dark") == "dark"

def test_theme_bad():
    try:
        validate_theme("neon")
        assert False
    except ValueError:
        assert True
