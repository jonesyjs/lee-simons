"""Operations — composed, meaningful units of work the pipeline calls.

One shared operations module over the git, GitHub, and Claude clients. Owns
intent; the clients below are blind to the goal. Each public operation returns a
`Result` (description + payload) and is audited.
"""

import json

from modules.claude_client import ClaudeClient
from modules.git_client import GitClient
from modules.github_client import GitHubClient
from modules.lib.log import AuditType, Result, audit

claude = ClaudeClient()
git = GitClient()
github = GitHubClient()

# Every comment the pipeline posts carries this marker so the trigger's loop
# guard can recognise (and ignore) its own comments — never re-triggering a run.
BOT_IDENTIFIER = "[ADW-AGENTS]"


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
    """Post a comment to the issue, tagged so the trigger won't re-fire on it."""
    if not body.startswith(BOT_IDENTIFIER):
        body = f"{BOT_IDENTIFIER} {body}"
    return github.comment(issue, body)


def list_issues() -> list[dict]:
    """Open issues as [{'number', 'body'}, ...]."""
    return json.loads(github.list_open_issues())


def issue_has_bot_comment(issue: str) -> bool:
    """True if the pipeline has already commented on this issue (i.e. processed)."""
    data = json.loads(github.issue_comments(issue))
    return any(BOT_IDENTIFIER in c.get("body", "") for c in data.get("comments", []))


# --- internal steps -------------------------------------------------------


def _generate_branch_name(issue: str) -> str:
    """Generate a branch name from an issue. The thick, value-making step."""
    name = claude.generate(
        f"Suggest a short git branch name (kebab-case, no prefix) for this work. "
        f"Reply with only the name, nothing else:\n\n{issue}",
        model="sonnet",
    )
    return name.strip()
