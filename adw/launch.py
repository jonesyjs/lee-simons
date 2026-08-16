"""launch — the bootstrap that stands the worktree up, then hands off.

Runs from the main checkout. It does the one thing the pipeline can't do from
inside a worktree that doesn't exist yet: fetch the issue, cut the branch +
worktree, and seed the run's state. It then launches full_build.py with its cwd
set into the worktree's adw/ dir, so from there every path is `.`-relative and
all run artifacts (state, logs, spec outputs) live in — and merge out of — the
worktree.

Branch creation happens before logging is wired, so its audit line goes to the
console default rather than a file; that is the accepted bootstrap gap.
"""

import os
import subprocess
import sys

from modules import git_ops
from modules.lib.state import RunStateModel
from modules.lib.state import create as create_state
from modules.lib.state import worktree_dir


def launch(issue_id: str, adw_id: str, root: str = ".") -> None:
    issue = git_ops.fetch_issue(issue_id)

    # The one outside reference: the worktree lives at the project root, a level
    # up from adw/ (see paths.worktree_dir).
    worktree = worktree_dir(adw_id, root)
    branch = git_ops.create_branch(issue, worktree).payload["branch"]

    # Seed state inside the worktree so the pipeline finds it already there.
    adw_dir = os.path.join(worktree, "adw")
    create_state(
        RunStateModel(adw_id=adw_id, issue_id=issue_id, branch_name=branch),
        root=adw_dir,
    )

    # Hand off: run the pipeline from inside the worktree. cwd = adw_dir makes
    # every root="." default resolve into the worktree.
    subprocess.run(
        [sys.executable, "full_build.py", issue_id, adw_id],
        cwd=adw_dir,
        check=True,
    )


if __name__ == "__main__":
    launch(issue_id=sys.argv[1], adw_id=sys.argv[2])
