"""Operations — composed, meaningful units of work the pipeline calls.

One shared operations module over the git, GitHub, and Claude clients. Owns
intent; the clients below are blind to the goal. Each public operation returns a
`Result` (description + payload) and is audited.
"""

from enum import StrEnum

from modules.claude_client import ClaudeClient
from modules.git_client import GitClient
from modules.github_client import GitHubClient
from modules.lib.log import AuditType, Result, audit

claude = ClaudeClient()
git = GitClient()
github = GitHubClient()


class ProblemClass(StrEnum):
    """The classification of an issue; selects meta-prompt + prime routing.

    Kept separate from State's `plan_type` for now (they may converge later).
    """

    FEATURE = "feature"
    BUG = "bug"
    CHORE = "chore"


# --- git operations ---


@audit(type=AuditType.OPERATION)
def create_branch(issue: str, path: str) -> Result:
    """Name a branch for the issue, then cut a worktree on it."""
    branch = _generate_branch_name(issue)
    git.worktree_add(path, branch)
    return Result(description="branch created", payload={"branch": branch})


def get_diff(path: str) -> str:
    """Return the git diff of the work in a worktree."""
    return git.diff(path)


def commit_work(path: str, message: str) -> str:
    """Stage everything in a worktree and commit it."""
    git.stage_all(path)
    return git.commit(path, message)


# --- github operations ---


def fetch_issue(issue: str) -> str:
    """Fetch the issue's title + body from GitHub."""
    return github.fetch_issue(issue)


def comment(issue: str, body: str) -> str:
    """Post a comment to the issue (e.g. the review summary)."""
    return github.comment(issue, body)


# --- issue operations ---


@audit(type=AuditType.OPERATION)
def classify_issue(issue: str) -> Result:
    """Classify the issue into a problem class."""
    return Result(
        description="issue classified",
        payload={"problem_class": _classify(issue)},
    )


# --- internal steps -------------------------------------------------------


def _generate_branch_name(issue: str) -> str:
    """Generate a branch name from an issue. The thick, value-making step."""
    name = claude.generate(
        f"Suggest a short git branch name (kebab-case, no prefix) for this work. "
        f"Reply with only the name, nothing else:\n\n{issue}",
        model="sonnet",
    )
    return name.strip()


# Stubbed inline for now; becomes a slash command when the Plan step is built.
_CLASSIFY_PROMPT = """\
Classify this GitHub issue into exactly one category: feature, bug, or chore.
Reply with only the single word, nothing else.

{issue}"""


def _classify(issue: str) -> ProblemClass:
    response = claude.generate(
        _CLASSIFY_PROMPT.format(issue=issue), model="sonnet"
    ).strip().lower()
    for problem_class in ProblemClass:
        if problem_class.value in response:
            return problem_class
    raise ValueError(f"could not classify issue from response: {response!r}")
