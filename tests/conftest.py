import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from escape_room.v2.config import load_config  # noqa: E402
from escape_room.v2.state import new_state  # noqa: E402


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def state():
    return new_state()


class FakeLLM:
    """Pretends to be Gemini so I can test the online path without a key or internet."""

    available = True
    models = ["fake-model"]

    def __init__(self, replies=None, error=None):
        self.replies = list(replies or [])
        self.error = error
        self.calls = []

    def generate(self, system, contents, json_mode=False):
        self.calls.append((system, contents, json_mode))
        if self.error:
            raise self.error
        return self.replies.pop(0) if self.replies else ""


@pytest.fixture
def fake_llm():
    return FakeLLM
