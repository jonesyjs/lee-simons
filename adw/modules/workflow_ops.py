"""Workflow steps — the pipeline's units of work.

Each step does its own work + logging and returns a Result; the orchestrator
slices at the adw/ root sequence them.
"""

import os
from dataclasses import dataclass

from modules import git_ops
from modules.lib.log import AuditType, Result, audit


@dataclass
class ReviewResult:
    """Review's return — a pass/fail verdict + a short human summary.

    Distinct from the audit Result: it drives the proceed-vs-escalate branch and
    is posted to the issue directly, not via the audit decorator.
    """

    success: bool
    summary: list[str]


@audit(type=AuditType.STEP)
def plan(issue: str, spec_path: str) -> Result:
    """Classify the issue, then generate the spec (the plan→build handoff)."""
    problem_class = git_ops.classify_issue(issue).payload["problem_class"]
    spec = _generate_plan(issue, problem_class)
    os.makedirs(os.path.dirname(spec_path) or ".", exist_ok=True)
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec)
    return Result(
        description="plan created",
        payload={"spec_path": spec_path, "problem_class": problem_class},
    )


@audit(type=AuditType.STEP)
def build(spec_path: str, path: str) -> Result:
    """Read only the spec, implement it, then commit."""
    with open(spec_path, encoding="utf-8") as f:
        spec = f.read()
    _implement(spec, path)
    git_ops.commit_work(path, "build: implement spec")
    return Result(description="build complete", payload={"spec_path": spec_path})


def review(spec_path: str, path: str, issue_id: str) -> ReviewResult:
    """Score the build (diff) against the spec; post the summary to the issue.

    Not audited: the summary is posted directly through the GitHub client,
    bypassing the audit decorator (per the Workflow SA doc).
    """
    diff = git_ops.get_diff(path)
    with open(spec_path, encoding="utf-8") as f:
        spec = f.read()
    success, summary = _review(diff, spec)
    git_ops.comment(issue_id, "\n".join(f"- {point}" for point in summary))
    return ReviewResult(success=success, summary=summary)


@audit(type=AuditType.STEP)
def document(path: str, review_summary: list[str]) -> Result:
    """Produce 'what was built' + 'what was learned' from the diff and review."""
    diff = git_ops.get_diff(path)
    built, learned = _document(diff, review_summary)
    docs = os.path.join(path, "docs")
    os.makedirs(docs, exist_ok=True)
    with open(os.path.join(docs, "what-was-built.md"), "w", encoding="utf-8") as f:
        f.write(built)
    with open(os.path.join(docs, "what-was-learned.md"), "w", encoding="utf-8") as f:
        f.write(learned)
    return Result(description="documentation created", payload={"docs": docs})


# --- internal agent calls (stubbed; become slash commands) ---


def _generate_plan(issue: str, problem_class: str) -> str:
    return f"# Spec ({problem_class})\n\n{issue}\n"


def _implement(spec: str, path: str) -> None:
    pass


def _review(diff: str, spec: str) -> tuple[bool, list[str]]:
    return True, ["implements the spec", "no obvious issues"]


def _document(diff: str, review_summary: list[str]) -> tuple[str, str]:
    return "# What was built\n\n(diff summary)\n", "# What was learned\n\n(process notes)\n"
