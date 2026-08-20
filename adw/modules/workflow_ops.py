"""Workflow steps — the pipeline's units of work.

Each step does its own work + logging and returns a Result; the orchestrator
slices at the adw/ root sequence them.
"""

import json
import os

from modules import git_ops, utils
from modules.claude_client import ClaudeClient
from modules.lib.log import AuditType, Result, audit
from modules.lib.state import verdict_path

claude = ClaudeClient()

# This process runs with cwd=<worktree>/adw, but the agent runs a level up at the
# worktree root. Paths handed to a command are prefixed with this so both ends
# resolve the same file from their own cwd.
ADW_DIR = "adw"


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
def review(spec_path: str, adw_id: str, path: str) -> Result:
    # Run /review directly: it diffs the build commit against its base and judges
    # each spec use case, emitting a JSON verdict.
    verdict = _parse_report(claude.generate(f"/review {spec_path}", cwd=path))

    # /document consumes the verdict as a file, so persist it. Written relative to
    # this process's cwd (adw/); document() hands the agent the worktree-relative
    # form of the same path.
    utils.write_file(verdict_path(adw_id), json.dumps(verdict, indent=2))

    # On success the verdict carries review_summary; a gate failure carries error.
    description = verdict.get("review_summary") or verdict.get("error", "review complete")
    return Result(description=description, payload=verdict)


@audit(type=AuditType.STEP)
def document(spec_path: str, adw_id: str, path: str) -> Result:
    # Run /document directly: it reads the review verdict, then the diff at each
    # use case's cited line, and writes one markdown file under app_docs/.
    verdict = verdict_path(adw_id, root=ADW_DIR)  # worktree-relative, for the agent
    report = _parse_report(
        claude.generate(f"/document {spec_path} {adw_id} {verdict}", cwd=path)
    )

    description = report.get("document_summary") or report.get("error", "documentation complete")
    return Result(description=description, payload=report)


# --- internal helpers ---


def _parse_report(output: str) -> dict:
    """Extract the JSON report from a command's output.

    /review and /document are both asked to emit JSON only, but the model
    sometimes wraps it in a markdown fence or precedes it with a line of prose.
    Slice from the first brace to the last so json.loads sees only the object.
    """
    start, end = output.find("{"), output.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in command output: {output!r}")
    return json.loads(output[start : end + 1])
