"""GitHub connector — a self-contained audit sink for issue comments.

A connector is the adapter edge where the logger plugs into a concrete external
system. Unlike a plain sink, it owns its client and reads the run's target from
log context — so nothing is injected at wiring time. Drop it into an appender
and it just works:

    Appender(GitHubConnector(), layout=MessageLayout(), filter=is_audit)

This is the one place the logging subsystem is allowed to know about a concrete
client; the rest of `lib.log` stays pure.
"""

from modules.github_client import GitHubClient
from modules.lib.log.models.context import current_issue_id
from modules.lib.log.delivery.sinks import Sink


class GitHubConnector(Sink):
    def __init__(self):
        self._client = GitHubClient()

    def write(self, formatted: str) -> None:
        self._client.comment(current_issue_id(), formatted)
