"""Walking-skeleton test for the plan_build orchestrator slice."""

import json
import os
import tempfile
import unittest
from unittest import mock

import plan_build
from modules import git_ops
from modules.lib.log import (
    Appender,
    Sink,
    is_audit,
    reset_appenders,
    set_appenders,
    set_run_context,
)
from modules.lib.state import read as read_state


class RecordingSink(Sink):
    def __init__(self):
        self.lines = []

    def write(self, formatted):
        self.lines.append(formatted)


def _fake_generate(prompt, model=None):
    if "branch name" in prompt:
        return "fix-login\n"
    if "Classify" in prompt:
        return "feature\n"
    return ""


class TestPlanBuildSlice(unittest.TestCase):
    def tearDown(self):
        reset_appenders()

    def test_runs_end_to_end(self):
        rec = RecordingSink()

        def fake_configure(adw_id, issue_id):
            set_run_context(adw_id, issue_id)
            set_appenders([Appender(rec, filter=is_audit)])

        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(plan_build, "configure_logging", fake_configure), \
                mock.patch.object(git_ops.github, "fetch_issue", return_value="Login is broken"), \
                mock.patch.object(git_ops.claude, "generate", side_effect=_fake_generate), \
                mock.patch.object(git_ops.git, "worktree_add", return_value=""), \
                mock.patch.object(git_ops.git, "stage_all", return_value=""), \
                mock.patch.object(git_ops.git, "commit", return_value=""):
            plan_build.main("7", "adw-1", root=root)

            # state persisted with the frozen branch name
            state = read_state("adw-1", root=root)
            self.assertEqual(state.branch_name, "fix-login")
            self.assertEqual(state.issue_id, "7")

            # spec produced (the plan→build handoff)
            spec = os.path.join(root, "adw-adw-1", "spec.md")
            self.assertTrue(os.path.exists(spec))
            self.assertIn("feature", open(spec).read())

        # audit trail, in order
        descs = [json.loads(line)["description"] for line in rec.lines]
        self.assertEqual(
            descs,
            ["branch created", "issue classified", "plan created", "build complete"],
        )
        stages = [json.loads(line)["stage"] for line in rec.lines]
        self.assertEqual(stages, ["plan", "plan", "plan", "build"])


if __name__ == "__main__":
    unittest.main()
