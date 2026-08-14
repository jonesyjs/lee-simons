"""lib.log — the ADW event logger (hand-rolled, stdlib only).

Phase 1: the event model. Phase 2: a minimal synchronous `log()`.
Sinks, layouts, and appenders arrive in later phases.
"""

from modules.lib.log.models.events import (
    SCHEMA_VERSION,
    AuditLogEvent,
    AuditType,
    Level,
    LogEvent,
    OperationalLogEvent,
    OperationalType,
    Outcome,
    Stage,
)
from modules.lib.log.delivery.appenders import Appender
from modules.lib.log.auditlog_decorator import Result, audit
from modules.lib.log.models.context import (
    current_adw_id,
    current_issue_id,
    current_stage,
    set_run_context,
    set_stage,
)
from modules.lib.log.delivery.filters import is_audit, is_operational, min_level
from modules.lib.log.delivery.layouts import JsonLinesLayout, Layout, MessageLayout
from modules.lib.log.delivery.registry import (
    add_appender,
    clear_appenders,
    reset_appenders,
    set_appenders,
)
from modules.lib.log.logger import log
from modules.lib.log.delivery.sinks import ConsoleSink, FileSink, Sink

__all__ = [
    "SCHEMA_VERSION",
    "LogEvent",
    "OperationalLogEvent",
    "AuditLogEvent",
    "Stage",
    "Level",
    "Outcome",
    "OperationalType",
    "AuditType",
    "log",
    "Layout",
    "JsonLinesLayout",
    "MessageLayout",
    "Sink",
    "ConsoleSink",
    "FileSink",
    "Appender",
    "is_operational",
    "is_audit",
    "min_level",
    "set_appenders",
    "add_appender",
    "clear_appenders",
    "reset_appenders",
    "audit",
    "Result",
    "set_run_context",
    "set_stage",
    "current_adw_id",
    "current_issue_id",
    "current_stage",
]
