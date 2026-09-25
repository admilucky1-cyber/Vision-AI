
"""I-V graph generation — skips if matplotlib missing."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

try:
    from services.image_gen import MATPLOTLIB_AVAILABLE, draw_iv_graph
except Exception:
    MATPLOTLIB_AVAILABLE = False


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
def test_draw_iv_ohmic():
    r = draw_iv_graph(ohmic=True)
    assert r.get("success"), r.get("error")
    assert r.get("image_data")
    assert len(r["image_data"]) > 100


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
def test_draw_iv_non_ohmic():
    r = draw_iv_graph(ohmic=False)
    assert r.get("success"), r.get("error")
