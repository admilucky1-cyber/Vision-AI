
"""Unit tests: diagram/graph intent detection (no GPU required)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.image_gen import user_wants_diagram, user_wants_creative_image


def test_iv_graph_is_diagram():
    assert user_wants_diagram("create graph between current and voltage")
    assert user_wants_diagram("draw I-V graph for a resistor")


def test_mosque_is_creative_not_chart():
    assert user_wants_diagram("3d image of mosque")
    # photography should not be forced to chart path
    assert user_wants_creative_image("photorealistic image of a mosque at sunset")


def test_chart_not_creative():
    assert not user_wants_creative_image("draw a bar chart of sales")
    assert user_wants_diagram("draw a bar chart of sales")


def test_empty_message():
    assert not user_wants_diagram("")
    assert not user_wants_creative_image("")
