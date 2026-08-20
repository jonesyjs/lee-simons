"""Emit — synchronous fan-out to the registered appenders.

`log(event)` hands the event to every appender in the registry (see
delivery/registry.py); each self-filters and writes to its own sink. Producers
name no destination. Never raises — every appender is best-effort internally.

Synchronous by design: one feature per detached subprocess, so per-process event
volume is trivial and no producer is latency-sensitive. See the Implementation
Phases doc for why a queue/async stream is not built.
"""

from modules.lib.log.delivery.registry import appenders
from modules.lib.log.models.events import LogEvent


def log(event: LogEvent) -> None:
    """Emit one event to every registered appender. Never raises."""
    for appender in appenders():
        appender.handle(event)  # each appender is best-effort internally
