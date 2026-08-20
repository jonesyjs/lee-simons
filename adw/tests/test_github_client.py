"""Tests for the GitHub (`gh`) client and its wiring to the audit sink."""

import unittest
from unittest import mock

from modules.github_client import GitHubClient
from modules.lib.log import (
    Appender,
    MessageLayout,
    is_audit,
    reset_appenders,
    set_run_context,
)
from modules.lib.log.connectors import GitHubConnector
from modules.lib.log.models.events import AuditLogEvent, AuditType, Outcome, Stage


class TestArgvBuilding(unittest.TestCase):
    def test_comment_builds_argv(self):
        with mock.patch.object(GitHubClient, "call", return_value="url") as call:
            GitHubClient().comment("42", "branch created")
            call.assert_called_once_with(
                ["gh", "issue", "comment", "42", "--body", "branch created"]
            )

    def test_fetch_issue_builds_argv(self):
        with mock.patch.object(GitHubClient, "call", return_value="{}") as call:
            GitHubClient().fetch_issue("42")
            call.assert_called_once_with(
                ["gh", "issue", "view", "42", "--json", "title,body"]
            )


class TestRecognition(unittest.TestCase):
    def test_rate_limit_is_transient(self):
        self.assertTrue(GitHubClient()._is_transient("API rate limit exceeded"))

    def test_not_found_is_deterministic(self):
        self.assertFalse(GitHubClient()._is_transient("could not resolve to an Issue"))


class TestConnectorToAuditSink(unittest.TestCase):
    def tearDown(self):
        reset_appenders()

    def test_audit_event_posts_a_comment(self):
        set_run_context("adw-a", "7")  # connector reads the issue from context
        with mock.patch.object(GitHubClient, "comment", return_value="url") as comment:
            app = Appender(GitHubConnector(), layout=MessageLayout(), filter=is_audit)
            app.handle(AuditLogEvent(
                adw_id="adw-a", issue_id="7", description="branch created",
                stage=Stage.PLAN, type=AuditType.OPERATION, outcome=Outcome.SUCCESS,
                payload={"branch": "fix-login"},
            ))
            comment.assert_called_once_with("7", "branch created (branch: fix-login)")

    def test_connector_post_failure_is_swallowed(self):
        set_run_context("adw-a", "7")
        with mock.patch.object(GitHubClient, "comment", side_effect=IOError("down")):
            app = Appender(GitHubConnector(), layout=MessageLayout(), filter=is_audit)
            app.handle(AuditLogEvent(
                adw_id="adw-a", issue_id="7", description="x",
                stage=Stage.PLAN, type=AuditType.OPERATION, outcome=Outcome.SUCCESS,
            ))  # must not raise


if __name__ == "__main__":
    unittest.main()
