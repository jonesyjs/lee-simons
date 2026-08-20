"""Run context — correlation the audit decorator reads.

The orchestrator sets the run's identity (`adw_id`, `issue_id`, `root`) once.
`stage` is NOT held here — it lives in the run's state file (the single source of
truth), and `current_stage()` reads it from there, so an external reader and the
logger see the same value. Uses contextvars so nested calls inherit the run.
"""

import contextvars

_adw_id: contextvars.ContextVar[str] = contextvars.ContextVar("adw_id", default="")
_issue_id: contextvars.ContextVar[str] = contextvars.ContextVar("issue_id", default="")
_root: contextvars.ContextVar[str] = contextvars.ContextVar("root", default=".")


def set_run_context(adw_id: str, issue_id: str, root: str = ".") -> None:
    _adw_id.set(adw_id)
    _issue_id.set(issue_id)
    _root.set(root)


def current_adw_id() -> str:
    return _adw_id.get()


def current_issue_id() -> str:
    return _issue_id.get()


def current_stage() -> str | None:
    """The run's current stage, read from its state file (source of truth)."""
    # Imported lazily to keep the import graph simple (state never imports log).
    from modules.lib.state import InvalidState, StateNotFound, read

    try:
        return read(_adw_id.get(), root=_root.get()).stage
    except (StateNotFound, InvalidState):
        return None
