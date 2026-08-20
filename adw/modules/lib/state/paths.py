"""Path computation — derive locations from ids, never store them.

Split by what the thing IS:
- `data/` is the pipeline's own data → lives in adw/. Split again by lifetime:
  `data/outputs/` for durable artifacts (specs, reviews, work) and `data/temp/`
  for transient run bookkeeping (state, logs).
- `trees/` are worktrees — copies of the whole project → live at the PROJECT
  root, a level up from adw/ (run from adw/, so "..").

Every path here is relative to `root`, which is the adw/ dir. The pipeline runs
with cwd=adw/, so root="." is the common case; agents run a level up at the
worktree root, so paths handed to a command pass root="adw".
"""

import os


def state_path(adw_id: str, root: str = ".") -> str:
    return os.path.join(root, "data", "temp", "state", f"{adw_id}.json")


def verdict_path(adw_id: str, root: str = ".") -> str:
    """The run's review verdict — a durable output, because /document reads it."""
    return os.path.join(root, "data", "outputs", "reviews", f"{adw_id}.json")


def worktree_dir(adw_id: str, root: str = ".") -> str:
    """The run's git worktree (code), at the project root — not under adw/data/."""
    return os.path.join(root, "..", "trees", adw_id)
