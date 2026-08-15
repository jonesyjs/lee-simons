"""Logging setup — the runtime wiring the orchestrator calls once per run.

Sets the run context and appender registry. The GitHub connector is
self-contained (owns its client, reads the issue from context), so there is
nothing to inject here.
"""

from modules.lib.log import (
    Appender,
    FileSink,
    JsonLinesLayout,
    MessageLayout,
    is_audit,
    set_appenders,
    set_run_context,
)
from modules.lib.log.connectors import GitHubConnector


def configure_logging(adw_id: str, issue_id: str, root: str = ".") -> None:
    """Wire the run's logging: everything → file (JSON), audit → GitHub issue.

    `root` is stored in the run context so the logger can read the current stage
    from the state file at the right location.
    """
    set_run_context(adw_id, issue_id, root)
    set_appenders([
        Appender(FileSink(adw_id), layout=JsonLinesLayout()),
        Appender(GitHubConnector(), layout=MessageLayout(), filter=is_audit),
    ])
