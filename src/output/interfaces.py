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
an iterable of records.

A "record" here is any object that exposes a `.to_dict() -> dict`
method. Two such records exist in this project:

    - StormEvent (NCDC weather-event use case)
    - Event      (Lab 3 audit-log use case)

Strategies do not depend on either concrete class — they just call
`.to_dict()` and serialize the result. Adding a third record type
later wouldn't require changes to any strategy.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Protocol


class _HasToDict(Protocol):
    def to_dict(self) -> dict: ...


class IOutputStrategy(ABC):
    """Strategy interface — one method swaps the entire output destination."""

    name: str = "abstract"

    @abstractmethod
    def open(self) -> None:
        """Establish the connection / open the file / prepare the producer."""

    @abstractmethod
    def write(self, record: _HasToDict) -> None:
        """Send one record to the underlying sink."""

    @abstractmethod
    def close(self) -> None:
        """Flush and release any resources held by the strategy."""

    # ------------------------------------------------------------------ #
    def write_all(self, records: Iterable[_HasToDict]) -> int:
        """Run the full lifecycle over an iterable of records.

        Returns the number of records written.
        """
        self.open()
        count = 0
        try:
            for r in records:
                self.write(r)
                count += 1
        finally:
            self.close()
        return count
