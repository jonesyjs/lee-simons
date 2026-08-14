"""Tests for pipeline integration — audit decorator, context, sinks (Phase 6)."""

import json
import unittest
from unittest import mock

from modules.lib.log import (
    Appender,
    MessageLayout,
    Result,
    Sink,
    Stage,
    audit,
    is_audit,
    reset_appenders,
    set_appenders,
    set_run_context,
    set_stage,
)
from modules.lib.log.models.events import AuditType, OperationalLogEvent, OperationalType


class RecordingSink(Sink):
    def __init__(self):
        self.lines = []

    def write(self, formatted):
        self.lines.append(formatted)


class AuditTestCase(unittest.TestCase):
    def setUp(self):
        self.sink = RecordingSink()
        set_appenders([Appender(self.sink, filter=is_audit)])
        set_run_context("adw-99", "issue-7")
        set_stage(Stage.PLAN)

    def tearDown(self):
        reset_appenders()


class TestAuditDecorator(AuditTestCase):
    def test_emits_audit_event_from_result(self):
        @audit(type=AuditType.OPERATION)
        def make_thing():
            return Result(description="thing made", payload={"id": 5})

        out = make_thing()
        self.assertEqual(out.payload["id"], 5)  # return passes through
        self.assertEqual(len(self.sink.lines), 1)
        ev = json.loads(self.sink.lines[0])
        self.assertEqual(ev["description"], "thing made")
        self.assertEqual(ev["adw_id"], "adw-99")     # from context
        self.assertEqual(ev["issue_id"], "issue-7")
        self.assertEqual(ev["stage"], "plan")
        self.assertEqual(ev["outcome"], "success")
        self.assertEqual(ev["payload"]["id"], 5)

    def test_exception_is_not_audited(self):
        @audit()
        def boom():
            raise RuntimeError("step failed")

        with self.assertRaises(RuntimeError):
            boom()
        self.assertEqual(self.sink.lines, [])  # failures go operational, not audit


class TestCreateBranchWired(AuditTestCase):
    def test_create_branch_emits_audit(self):
        from modules import git_ops

        with mock.patch.object(git_ops, "_generate_branch_name", return_value="fix-login"), \
             mock.patch.object(git_ops.git, "worktree_add", return_value=""):
            result = git_ops.create_branch("fix the login", "/tmp/wt")

        self.assertEqual(result.payload["branch"], "fix-login")
        ev = json.loads(self.sink.lines[0])
        self.assertEqual(ev["description"], "branch created")
        self.assertEqual(ev["payload"]["branch"], "fix-login")
        self.assertEqual(ev["type"], "operation")


class TestMessageLayout(unittest.TestCase):
    def test_message_layout_is_human_readable(self):
        ev = OperationalLogEvent(
            adw_id="a", issue_id="1", description="branch created",
            stage=Stage.PLAN, type=OperationalType.LLM_CALL, payload={"branch": "x"},
        )
        self.assertEqual(MessageLayout().format(ev), "branch created (branch: x)")


if __name__ == "__main__":
    unittest.main()
