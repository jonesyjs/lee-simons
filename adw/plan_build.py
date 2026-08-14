"""plan_build — cold-start slice: Plan → Build.

The orchestrator: wires the run (logging, branch, state) and sequences the steps.
"""

import os
import sys

from modules import git_ops, workflow_ops
from modules.lib.log import Stage, set_stage
from modules.lib.state import PlanType, RunState
from modules.lib.state import create as create_state
from modules.lib.state import run_dir
from modules.log_setup import configure_logging


def main(issue_id: str, adw_id: str, root: str = ".") -> None:
    configure_logging(adw_id, issue_id)
    worktree = run_dir(adw_id, root)
    issue = git_ops.fetch_issue(issue_id)

    set_stage(Stage.PLAN)
    branch = git_ops.create_branch(issue, worktree).payload["branch"]
    create_state(
        RunState(adw_id=adw_id, issue_id=issue_id, plan_type=PlanType.FEATURE,
                 branch_name=branch),
        root=root,
    )

    spec_path = os.path.join(worktree, "spec.md")
    workflow_ops.plan(issue, spec_path)

    set_stage(Stage.BUILD)
    workflow_ops.build(spec_path, worktree)


if __name__ == "__main__":
    main(issue_id=sys.argv[1], adw_id=sys.argv[2])
