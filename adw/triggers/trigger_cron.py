#!/usr/bin/env -S uv run
"""Cron trigger — poll GitHub for issues and launch qualifying runs.

Long-running poller (stdlib only). Each pass lists open issues, skips ones the
pipeline has already commented on (its ack marks them processed), and hands the
rest to the shared trigger core.

Usage: uv run triggers/trigger_cron.py
"""

import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import git_ops, trigger

INTERVAL_SECONDS = 20
_stop = False


def _handle_signal(signum, frame):
    global _stop
    _stop = True


def poll_once() -> None:
    for issue in git_ops.list_issues():
        number = str(issue["number"])
        if git_ops.issue_has_bot_comment(number):
            continue  # already processed — our ack comment is present
        trigger.handle_issue(number, issue.get("body", ""))


def main() -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    while not _stop:
        poll_once()
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
