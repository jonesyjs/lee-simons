"""Layouts — transform an event into a sink's output format (Phase 3).

A layout only formats; it never decides where the result goes.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict

from modules.lib.log.models.events import LogEvent


class Layout(ABC):
    @abstractmethod
    def format(self, event: LogEvent) -> str:
        ...


class JsonLinesLayout(Layout):
    """One JSON object per line (JSON Lines)."""

    def format(self, event: LogEvent) -> str:
        return json.dumps(asdict(event))


class MessageLayout(Layout):
    """Human-readable one-liner — for sinks people read (e.g. GitHub comments).

    The description carries the summary; any payload is appended compactly.
    """

    def format(self, event: LogEvent) -> str:
        if event.payload:
            details = ", ".join(f"{k}: {v}" for k, v in event.payload.items())
            return f"{event.description} ({details})"
        return event.description
