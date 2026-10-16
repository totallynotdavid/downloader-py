from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Media:
    type: Literal["image", "video"]
    url: str


class ExtractionError(Exception):
    """The post exists in a supported platform but its media could not be read."""


@contextmanager
def reading(source: str) -> Iterator[None]:
    """Turn a response that lacks the expected fields into an ExtractionError."""
    try:
        yield
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ExtractionError(f"{source} returned an unexpected response: {exc!r}") from exc
