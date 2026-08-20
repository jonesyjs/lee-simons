import os
import subprocess
import sys

from modules import git_ops
from modules.lib.state import RunStateModel
from modules.lib.state import create as create_state
from modules.lib.state import worktree_dir


def launch(issue_id: str, adw_id: str, root: str = ".") -> None:
    issue = git_ops.fetch_issue(issue_id)
    worktree = worktree_dir(adw_id, root)
    branch = git_ops.create_branch(issue, worktree).payload["branch"]

    adw_dir = os.path.join(worktree, "adw")
    create_state(
        RunStateModel(adw_id=adw_id, issue_id=issue_id, branch_name=branch),
        root=adw_dir,
    )

    subprocess.run(
        [sys.executable, "full_build.py", issue_id, adw_id],
        cwd=adw_dir,
        check=True,
    )


if __name__ == "__main__":
    launch(issue_id=sys.argv[1], adw_id=sys.argv[2])
