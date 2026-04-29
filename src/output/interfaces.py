"""
The Strategy interface (GoF "Strategy" role).

This is the abstraction every concrete output destination implements.
The client code (`main.py`) holds a reference of type `IOutputStrategy`
and calls `write` / `write_all` on it without knowing or caring which
concrete class is plugged in. Swapping implementations is therefore a
factory decision driven by config — never a code edit.

Lifecycle:
    open()   ─┐
              │   establish connection / open file / spin up producer
    write()  ─┤   called once per record
    write()  ─┤
    write()  ─┤
    close()  ─┘   flush, close, release resources

`write_all` is a convenience wrapper that runs the full lifecycle for
an iterable of events. Subclasses can override it for batch optimization
(e.g. a Kafka producer that wants `producer.flush()` only at the end).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ..reader.models import StormEvent


class IOutputStrategy(ABC):
    """Strategy interface — one method swaps the entire output destination."""

    name: str = "abstract"

    @abstractmethod
    def open(self) -> None:
        """Establish the connection / open the file / prepare the producer."""

    @abstractmethod
    def write(self, event: StormEvent) -> None:
        """Send one event to the underlying sink."""

    @abstractmethod
    def close(self) -> None:
        """Flush and release any resources held by the strategy."""

    # ------------------------------------------------------------------ #
    def write_all(self, events: Iterable[StormEvent]) -> int:
        """Run the full lifecycle over an iterable of events.

        Returns the number of events written. Subclasses can override
        for batch behaviour, but the default implementation is correct
        for any well-formed strategy.
        """
        self.open()
        count = 0
        try:
            for ev in events:
                self.write(ev)
                count += 1
        finally:
            self.close()
        return count
