"""Appender — filter, format, write (Phase 4).

Consumes an event, applies its own filter, invokes its layout, writes to its
sink. Filtering is decentralised: each appender owns its criteria, so producers
never name a sink.

Best-effort per appender: a failure in one appender (bad filter, dead sink) is
swallowed so it neither breaks the producer nor stops the other appenders.
"""

from modules.lib.log.models.events import LogEvent
from modules.lib.log.delivery.filters import Filter
from modules.lib.log.delivery.layouts import JsonLinesLayout, Layout
from modules.lib.log.delivery.sinks import Sink


class Appender:
    def __init__(self, sink: Sink, *, layout: Layout | None = None, filter: Filter | None = None):
        self.sink = sink
        self.layout = layout or JsonLinesLayout()
        self.filter = filter  # None = accept all

    def handle(self, event: LogEvent) -> None:
        try:
            if self.filter is not None and not self.filter(event):
                return
            self.sink.write(self.layout.format(event))
        except Exception:
            pass  # best-effort: never break the producer or the other appenders
