"""plan_build_review_document — the full pipeline, run from inside the worktree.

Plan → Build → Review → Document, end to end. Assumes it is launched with its
cwd set to the worktree's `adw/` dir (see launch.py), so every path is `.`-
relative and lands in the worktree: state, logs, and spec outputs all travel
with the branch when it merges. The launcher has already fetched the issue, cut
the branch/worktree, and seeded the run's state — this just runs the steps.

Review branches: success → document, fail → escalate (the failed review summary
is already posted to the issue).
"""

import os
import sys

from modules import git_ops, workflow_ops
from modules.lib.log import Stage
from modules.lib.state import update_stage
from modules.log_setup import configure_logging


def main(issue_id: str, adw_id: str, root: str = ".") -> None:
    configure_logging(adw_id, issue_id, root)  # root="." → worktree/adw/data/logs
    issue = git_ops.fetch_issue(issue_id)
    project_root = os.path.join(root, os.pardir)

    # Plan: the agent writes the spec into the worktree and returns its path.
    update_stage(adw_id, Stage.PLAN, root=root)
    spec_path = workflow_ops.plan(issue, issue_id, adw_id, project_root).payload["spec_path"]

    # Build: read only the spec, implement it, commit.
    update_stage(adw_id, Stage.BUILD, root=root)
    workflow_ops.build(spec_path, project_root)

    # Review: judge the build's diff against the spec's use cases; post to the
    # issue and persist the verdict for the document step to read.
    update_stage(adw_id, Stage.REVIEW, root=root)
    result = workflow_ops.review(spec_path, adw_id, project_root)
    if not result.payload.get("success"):
        return  # escalate to a human

    # Document: one entry per use case, from the verdict, into app_docs/.
    update_stage(adw_id, Stage.DOCUMENT, root=root)
    workflow_ops.document(spec_path, adw_id, project_root)


if __name__ == "__main__":
    main(issue_id=sys.argv[1], adw_id=sys.argv[2])
