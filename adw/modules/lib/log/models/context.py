"""Run context (Phase 6) — correlation the audit decorator reads.

The orchestrator sets the run's identity (`adw_id`, `issue_id`) once and updates
`stage` as it moves through plan → build → review → document. The audit
decorator reads these when it emits, so steps/operations never thread them by
hand. Uses contextvars so nested calls inherit the current run.
"""

import contextvars

from modules.lib.log.models.events import Stage

_adw_id: contextvars.ContextVar[str] = contextvars.ContextVar("adw_id", default="")
_issue_id: contextvars.ContextVar[str] = contextvars.ContextVar("issue_id", default="")
_stage: contextvars.ContextVar[Stage | None] = contextvars.ContextVar("stage", default=None)


def set_run_context(adw_id: str, issue_id: str) -> None:
    _adw_id.set(adw_id)
    _issue_id.set(issue_id)


def set_stage(stage: Stage) -> None:
    _stage.set(stage)


def current_adw_id() -> str:
    return _adw_id.get()


def current_issue_id() -> str:
    return _issue_id.get()


def current_stage() -> Stage | None:
    return _stage.get()
