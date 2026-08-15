"""plan_build_review_document — the full pipeline, cold-start.

Plan → Build → Review → Document, end to end. Mints state and cuts the branch,
runs all four steps, and branches on review: success → document, fail → escalate
(the failed review summary is already posted to the issue).
"""

import os
import sys

from modules import git_ops, workflow_ops
from modules.lib.log import Stage
from modules.lib.state import RunStateModel
from modules.lib.state import create as create_state
from modules.lib.state import update as update_state
from modules.lib.state import update_stage, worktree_dir
from modules.log_setup import configure_logging


def main(issue_id: str, adw_id: str, root: str = ".") -> None:
    configure_logging(adw_id, issue_id, root)
    create_state(RunStateModel(adw_id=adw_id, issue_id=issue_id), root=root)
    issue = git_ops.fetch_issue(issue_id)

    # Create-branch
    worktree = worktree_dir(adw_id, root)
    branch = git_ops.create_branch(issue, worktree).payload["branch"]
    update_state(adw_id, branch, root=root)

    # Plan Step
    update_stage(adw_id, Stage.PLAN, root=root)
    spec_path = workflow_ops.plan(issue, issue_id, adw_id, worktree).payload["spec_path"]

    # # Build: read only the spec, implement it, commit.
    # update_stage(adw_id, Stage.BUILD, root=root)
    # workflow_ops.build(spec_path, worktree)

    # # Review: score the build against the spec; post the summary to the issue.
    # update_stage(adw_id, Stage.REVIEW, root=root)
    # result = workflow_ops.review(spec_path, worktree, issue_id)
    # if not result.success:
    #     return  # escalate to a human

    # # Document: write "what was built" + "what was learned".
    # update_stage(adw_id, Stage.DOCUMENT, root=root)
    # workflow_ops.document(worktree, result.summary)


if __name__ == "__main__":
    main(issue_id=sys.argv[1], adw_id=sys.argv[2])
