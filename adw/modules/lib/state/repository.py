"""Repository — a thin CRU interface over the run's JSON state file.

State is just a JSON file, so this is deliberately small: read/write with an
atomic write (temp → rename) to avoid a half-written file, and simple errors for
missing/malformed files. No retry — a local per-run file write rarely fails
transiently, and deterministic failures (disk full, permissions) shouldn't be
retried anyway. Revisit only if state ever moves off local disk.

Surface: Create, Read, Update (no Delete — cleanup is branch deletion).
"""

import json
import os
from dataclasses import asdict, replace

from modules.lib.state.paths import state_path
from modules.lib.state.run_state import RunStateModel


class StateNotFound(Exception):
    """No state file for this adw_id."""


class InvalidState(Exception):
    """The state file exists but could not be parsed."""


def create(state: RunStateModel, root: str = ".") -> None:
    """Write RunStateModel as JSON. Overwrites silently (uniqueness guaranteed upstream)."""
    _atomic_write(state_path(state.adw_id, root), json.dumps(asdict(state)))


def read(adw_id: str, root: str = ".") -> RunStateModel:
    """Load and parse the state file into a RunStateModel."""
    path = state_path(adw_id, root)
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError as exc:
        raise StateNotFound(adw_id) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidState(adw_id) from exc
    return _from_dict(data)


def update(adw_id: str, branch_name: str, root: str = ".") -> RunStateModel:
    """Set branch_name once (after generation) and write back. File must exist."""
    updated = replace(read(adw_id, root), branch_name=branch_name)
    _atomic_write(state_path(adw_id, root), json.dumps(asdict(updated)))
    return updated


def update_stage(adw_id: str, stage: str, root: str = ".") -> RunStateModel:
    """Set the run's current stage and write back. The single source of truth
    the logger reads from. File must exist."""
    updated = replace(read(adw_id, root), stage=str(stage))
    _atomic_write(state_path(adw_id, root), json.dumps(asdict(updated)))
    return updated


def _atomic_write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)  # atomic rename


def _from_dict(data: dict) -> RunStateModel:
    return RunStateModel(
        adw_id=data["adw_id"],
        issue_id=data["issue_id"],
        branch_name=data.get("branch_name"),
        stage=data.get("stage"),
    )
