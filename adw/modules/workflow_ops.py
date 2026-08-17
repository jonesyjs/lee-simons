"""Workflow steps — the pipeline's units of work.

Each step does its own work + logging and returns a Result; the orchestrator
slices at the adw/ root sequence them.
"""

import json
import os

from modules import git_ops, utils
from modules.claude_client import ClaudeClient
from modules.lib.log import AuditType, Result, audit

claude = ClaudeClient()

@audit(type=AuditType.STEP)
def plan(issue: str, issue_id: str, adw_id: str, worktree: str) -> Result:
    command = claude.generate(f"/classify_issue {issue}").strip()
    written = claude.generate(f"{command} {issue_id} {adw_id} {issue}", cwd=worktree).strip()

    if not os.path.exists(os.path.join(worktree, written)):
        raise RuntimeError(f"spec not found in worktree: {written}")

    return Result(
        description="plan created",
        payload={"spec_path": written, "command": command},
    )


@audit(type=AuditType.STEP)
def build(spec_path: str, path: str) -> Result:
    # Run the /build command directly: it reads the spec at spec_path (relative
    # to the worktree root = cwd) and implements it in place.
    claude.generate(f"/build {spec_path}", cwd=path)
    git_ops.commit_work(path, "build: implement spec")

    return Result(description="build complete", payload={"spec_path": spec_path})

@audit(type=AuditType.STEP)
def review(spec_path: str, path: str) -> Result:
    # Run /review directly: it diffs the build commit against its base and judges
    # each spec use case, emitting a JSON verdict.
    verdict = json.loads(claude.generate(f"/review {spec_path}", cwd=path))

    # On success the verdict carries review_summary; a gate failure carries error.
    description = verdict.get("review_summary") or verdict.get("error", "review complete")
    return Result(description=description, payload=verdict)


# @audit(type=AuditType.STEP)
# def document(path: str, review_summary: list[str]) -> Result:
#     diff = git_ops.get_diff(path)
#     built, learned = _document(diff, review_summary)

#     docs = os.path.join(path, "docs")
#     utils.write_file(os.path.join(docs, "what-was-built.md"), built)
#     utils.write_file(os.path.join(docs, "what-was-learned.md"), learned)
#     return Result(description="documentation created", payload={"docs": docs})

# --- internal agent calls (stubbed; become slash commands) ---


def _document(diff: str, review_summary: list[str]) -> tuple[str, str]:
    return "# What was built\n\n(diff summary)\n", "# What was learned\n\n(process notes)\n"
