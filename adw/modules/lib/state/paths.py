"""Path computation — derive locations from ids, never store them.

The state file lives in the run's branch work tree at adw-{adw_id}/run-state.json.
Artifact locations (spec, report, docs) are computed by callers from the ids +
branch + a step name when steps need them — not held in state.
"""

import os


def run_dir(adw_id: str, root: str = ".") -> str:
    return os.path.join(root, f"adw-{adw_id}")


def state_path(adw_id: str, root: str = ".") -> str:
    return os.path.join(run_dir(adw_id, root), "run-state.json")
