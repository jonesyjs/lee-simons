"""lib.state — the run's metadata contract (RunState) and its access layer.

Tracks only run identifiers, never artifacts (those live in the git branch).
State is a JSON file at adw-{adw_id}/run-state.json; the DAL is a thin CRU over it.
"""

from modules.lib.state.repository import InvalidState, StateNotFound, create, read, update
from modules.lib.state.paths import run_dir, state_path
from modules.lib.state.models.run_state import PlanType, RunState

__all__ = [
    "RunState",
    "PlanType",
    "create",
    "read",
    "update",
    "StateNotFound",
    "InvalidState",
    "state_path",
    "run_dir",
]
