"""
Reader interfaces.

A reader's only job is to produce records of one kind. It knows nothing
about the output destination, which satisfies the lab's "reading code
separated from output code" requirement.

Two reader contracts here:
    - IStormEventReader  — the original NCDC use case (CSV → StormEvent)
    - IEventReader       — the Lab 3 audit-log use case (stdin → Event)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from .event import Event
from .models import StormEvent


class IStormEventReader(ABC):
    @abstractmethod
    def read(self) -> Iterator[StormEvent]: ...


class IEventReader(ABC):
    @abstractmethod
    def read(self) -> Iterator[Event]: ...
