"""Filters — predicates an appender uses to self-select events (Phase 4).

A filter is just `Callable[[LogEvent], bool]`. These are ready-made helpers;
any predicate works.
"""

from collections.abc import Callable

from modules.lib.log.models.events import (
    AuditLogEvent,
    Level,
    LogEvent,
    OperationalLogEvent,
)

Filter = Callable[[LogEvent], bool]


def is_operational(event: LogEvent) -> bool:
    return isinstance(event, OperationalLogEvent)


def is_audit(event: LogEvent) -> bool:
    return isinstance(event, AuditLogEvent)


# Severity ordering (StrEnum values don't order by severity on their own).
_LEVEL_RANK = {Level.DEBUG: 10, Level.INFO: 20, Level.WARN: 30, Level.ERROR: 40}


def min_level(threshold: Level) -> Filter:
    """Accept operational events at or above `threshold`. Non-operational
    events (no level) are rejected."""
    floor = _LEVEL_RANK[threshold]

    def _f(event: LogEvent) -> bool:
        level = getattr(event, "level", None)
        return level is not None and _LEVEL_RANK[level] >= floor

    return _f
