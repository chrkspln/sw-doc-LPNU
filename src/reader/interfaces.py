"""
Reader interface.

The reader's only job is to produce `StormEvent` instances. It knows
nothing about the output destination, which satisfies the lab's
"reading code separated from output code" requirement.

The interface returns an iterator (not a list) so the program can stream
millions of events through a strategy without loading them all into RAM.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from .models import StormEvent


class IStormEventReader(ABC):
    @abstractmethod
    def read(self) -> Iterator[StormEvent]: ...
