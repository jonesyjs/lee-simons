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
    """Appends JSON lines to data/logs/{adw_id}.jsonl.

    One file per run, named by adw_id (permanent folder, file named for the run).
    Opens per write to stay stateless and simple; buffering can come later if
    the per-event open cost ever matters (it won't for pipeline volumes).
    """

    def __init__(self, adw_id: str, root: str = os.path.join("data", "logs")):
        self.path = os.path.join(root, f"{adw_id}.jsonl")
        # Create the (empty) log file now, at wiring time, so it exists from the
        # start of the run — before the first event is written.
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        open(self.path, "a", encoding="utf-8").close()

    def write(self, formatted: str) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
