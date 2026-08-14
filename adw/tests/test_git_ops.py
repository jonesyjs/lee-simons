"""Tests for issue operations — classify_issue."""

import json
import unittest
from unittest import mock

from modules import git_ops
from modules.git_ops import ProblemClass, classify_issue
from modules.lib.log import (
    Appender,
    Sink,
    Stage,
    is_audit,
    reset_appenders,
    set_appenders,
    set_run_context,
    set_stage,
)


class RecordingSink(Sink):
    def __init__(self):
        self.lines = []

    def write(self, formatted):
        self.lines.append(formatted)


class TestClassify(unittest.TestCase):
    def test_each_class_recognised(self):
        for word, expected in [
            ("feature", ProblemClass.FEATURE),
            ("bug", ProblemClass.BUG),
            ("chore", ProblemClass.CHORE),
        ]:
            with mock.patch.object(git_ops.claude, "generate", return_value=f"{word}\n"):
                result = classify_issue("some issue")
                self.assertEqual(result.payload["problem_class"], expected)

    def test_unknown_response_raises(self):
        with mock.patch.object(git_ops.claude, "generate", return_value="banana"):
            with self.assertRaises(ValueError):
                classify_issue("some issue")

    def test_returns_result_with_description(self):
        with mock.patch.object(git_ops.claude, "generate", return_value="bug"):
            result = classify_issue("login broken")
        self.assertEqual(result.description, "issue classified")
        self.assertEqual(result.payload["problem_class"], "bug")  # StrEnum == str


class TestClassifyEmitsAudit(unittest.TestCase):
    def tearDown(self):
        reset_appenders()

    def test_audit_event_emitted(self):
        sink = RecordingSink()
        set_appenders([Appender(sink, filter=is_audit)])
        set_run_context("adw-1", "7")
        set_stage(Stage.PLAN)
        with mock.patch.object(git_ops.claude, "generate", return_value="feature"):
            classify_issue("add dark mode")
        self.assertEqual(len(sink.lines), 1)
        ev = json.loads(sink.lines[0])
        self.assertEqual(ev["description"], "issue classified")
        self.assertEqual(ev["payload"]["problem_class"], "feature")
        self.assertEqual(ev["stage"], "plan")


if __name__ == "__main__":
    unittest.main()
