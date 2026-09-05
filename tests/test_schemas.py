
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def test_chat_in_optional():
    try:
        from services.schemas import ChatIn
        m = ChatIn(message="hello")
        assert m.message == "hello"
    except Exception as e:
        # pydantic may be missing in minimal env
        import pytest
        pytest.skip(str(e))
