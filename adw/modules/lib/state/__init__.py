"""lib.state — the run's metadata contract (RunStateModel) and its access layer.

Tracks only run identifiers, never artifacts. State is a JSON file at
data/state/{adw_id}.json; the DAL is a thin CRU over it.
"""

from modules.lib.state.repository import (
    InvalidState,
    StateNotFound,
    create,
    read,
    update,
    update_stage,
)
from modules.lib.state.paths import state_path, worktree_dir
from modules.lib.state.run_state import RunStateModel

__all__ = [
    "RunStateModel",
    "create",
    "read",
    "update",
    "update_stage",
    "StateNotFound",
    "InvalidState",
    "state_path",
    "worktree_dir",
]
