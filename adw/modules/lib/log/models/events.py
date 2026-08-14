"""Log event model — the envelope every stage emits.

Two event types via inheritance over a shared base (logging SA doc):
- OperationalLogEvent — in-the-moment debugging, severity-based.
- AuditLogEvent      — durable record of pipeline outcomes.

The base carries identity + correlation; each subtype extends it. A sink is only
a destination, never a type — either model can route anywhere.

Identity fields (`log_id`, `ts`, `schema_version`) are stamped at construction,
which for the sync-first logger is emit time. All timestamps use one UTC clock.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

SCHEMA_VERSION = "1.0"


# --- categorical fields (StrEnum: compare/serialize as plain strings) ---


class Stage(StrEnum):
    PLAN = "plan"
    BUILD = "build"
    REVIEW = "review"
    DOCUMENT = "document"


class Level(StrEnum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"


class Outcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    STATE_TRANSITION = "state_transition"


# Type enums are intentionally lean. Add a member only when it is a distinct,
# repeatable event not expressible as a payload variation of an existing type;
# operational and audit never share a type. Grow these as real events appear.


class OperationalType(StrEnum):
    LLM_CALL = "llm_call"        # an agent/model call (payload: model, tokens)
    STEP_FAILURE = "step_failure"  # a step raised an exception


class AuditType(StrEnum):
    OPERATION = "operation"  # an operation completed (e.g. branch created)
    STEP = "step"            # a pipeline step reached an outcome


# --- events ---


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(kw_only=True)
class LogEvent:
    """Shared base: identity, correlation, and the free-form payload."""

    adw_id: str          # the run this event belongs to (correlation key)
    issue_id: str        # the git issue the run stems from (correlation key)
    description: str      # human-readable summary of the event
    payload: dict = field(default_factory=dict)  # type-specific data
    schema_version: str = SCHEMA_VERSION
    log_id: str = field(default_factory=_new_id)
    ts: str = field(default_factory=_now)


@dataclass(kw_only=True)
class OperationalLogEvent(LogEvent):
    """In-the-moment debugging output."""

    stage: Stage
    type: OperationalType
    level: Level = Level.INFO


@dataclass(kw_only=True)
class AuditLogEvent(LogEvent):
    """Durable record of a pipeline outcome or milestone."""

    stage: Stage
    type: AuditType
    outcome: Outcome
