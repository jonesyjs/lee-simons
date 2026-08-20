"""Audit decorator (Phase 6) — lift audit logging out of step/operation bodies.

A step or operation returns a `Result` (description + payload) mirroring the
audit envelope. The decorator reads that on the way out and emits an
AuditLogEvent — it sees only the boundary (return value), never internal scope,
so the body stays free of audit code.

Failures are deliberately NOT audited here: a step's own exception is a
debugging concern for operational logs, not the audit/GitHub stream (GitHub sees
outcomes, not exceptions). So the decorator emits on success and lets exceptions
propagate untouched.
"""

import functools
from dataclasses import dataclass, field

from modules.lib.log.models.context import current_adw_id, current_issue_id, current_stage
from modules.lib.log.models.events import AuditLogEvent, AuditType, Outcome
from modules.lib.log.logger import log


@dataclass
class Result:
    """The structured return every audited step/operation produces."""

    description: str
    payload: dict = field(default_factory=dict)


def audit(type: AuditType = AuditType.OPERATION):
    """Decorate a step/operation that returns a Result; emit an audit event."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)  # exceptions propagate unaudited
            log(
                AuditLogEvent(
                    adw_id=current_adw_id(),
                    issue_id=current_issue_id(),
                    stage=current_stage(),
                    type=type,
                    outcome=Outcome.SUCCESS,
                    description=result.description,
                    payload=result.payload,
                )
            )
            return result

        return wrapper

    return decorator
