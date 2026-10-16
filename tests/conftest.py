import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import responses

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def http() -> Iterator[responses.RequestsMock]:
    """Every request a test makes must be registered, and every registration used."""
    with responses.RequestsMock() as mock:
        yield mock
