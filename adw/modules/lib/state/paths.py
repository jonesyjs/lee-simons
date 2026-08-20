"""Path computation — derive locations from ids, never store them.

Split by what the thing IS:
- `data/` is the pipeline's own data → lives in adw/. Split again by lifetime:
  `data/outputs/` for durable artifacts (specs, work) and `data/temp/` for
  transient run bookkeeping (state, logs).
- `trees/` are worktrees — copies of the whole project → live at the PROJECT
  root, a level up from adw/ (run from adw/, so "..").
"""

import os


def state_path(adw_id: str, root: str = ".") -> str:
    return os.path.join(root, "data", "temp", "state", f"{adw_id}.json")


def worktree_dir(adw_id: str, root: str = ".") -> str:
    """The run's git worktree (code), at the project root — not under adw/data/."""
    return os.path.join(root, "..", "trees", adw_id)
