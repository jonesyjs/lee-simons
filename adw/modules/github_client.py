from modules.lib.client import SubprocessClient


class GitHubClient(SubprocessClient):
    """The `gh` CLI backend — read/write to GitHub issues."""

    transient_signatures = (
        "rate limit",
        "429",
        "503",
        "502",
        "timeout",
        "connection reset",
        "temporarily unavailable",
    )

    def comment(self, issue: str, body: str) -> str:
        return self.call(["gh", "issue", "comment", str(issue), "--body", body])

    def fetch_issue(self, issue: str) -> str:
        return self.call(["gh", "issue", "view", str(issue), "--json", "title,body"])

    def list_open_issues(self) -> str:
        return self.call(["gh", "issue", "list", "--state", "open", "--json", "number,body"])

    def issue_comments(self, issue: str) -> str:
        return self.call(["gh", "issue", "view", str(issue), "--json", "comments"])
