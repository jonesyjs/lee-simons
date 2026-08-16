"""Workflow steps — the pipeline's units of work.

Each step does its own work + logging and returns a Result; the orchestrator
slices at the adw/ root sequence them.
"""

import os
from dataclasses import dataclass

from modules import git_ops, utils
from modules.claude_client import ClaudeClient
from modules.lib.log import AuditType, Result, audit

claude = ClaudeClient()


@dataclass
class ReviewResult:
    success: bool
    summary: list[str]


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


def review(spec_path: str, path: str, issue_id: str) -> ReviewResult:
    diff = git_ops.get_diff(path)
    spec = utils.read_file(os.path.join(path, spec_path))

    success, summary = _review(diff, spec)
    git_ops.comment(issue_id, "\n".join(f"- {point}" for point in summary))
    return ReviewResult(success=success, summary=summary)


@audit(type=AuditType.STEP)
def document(path: str, review_summary: list[str]) -> Result:
    diff = git_ops.get_diff(path)
    built, learned = _document(diff, review_summary)

    docs = os.path.join(path, "docs")
    utils.write_file(os.path.join(docs, "what-was-built.md"), built)
    utils.write_file(os.path.join(docs, "what-was-learned.md"), learned)
    return Result(description="documentation created", payload={"docs": docs})


# --- internal agent calls (stubbed; become slash commands) ---


def _review(diff: str, spec: str) -> tuple[bool, list[str]]:
    return True, ["implements the spec", "no obvious issues"]


def _document(diff: str, review_summary: list[str]) -> tuple[str, str]:
    return "# What was built\n\n(diff summary)\n", "# What was learned\n\n(process notes)\n"
