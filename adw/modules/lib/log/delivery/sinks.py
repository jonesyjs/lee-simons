"""Sinks — destinations an appender writes to (Phase 3).

A sink only writes an already-formatted string; it knows nothing about events,
layouts, or filtering.
"""

import os
from abc import ABC, abstractmethod


class Sink(ABC):
    @abstractmethod
    def write(self, formatted: str) -> None:
        ...


class ConsoleSink(Sink):
    def write(self, formatted: str) -> None:
        print(formatted)


class FileSink(Sink):
    """Appends JSON lines to logs/{adw_id}/{filename}.

    Opens per write to stay stateless and simple; buffering can come later if
    the per-event open cost ever matters (it won't for pipeline volumes).
    """

    def __init__(self, adw_id: str, filename: str = "events.jsonl", root: str = "logs"):
        self.path = os.path.join(root, adw_id, filename)

    def write(self, formatted: str) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
