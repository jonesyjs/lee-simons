"""Tests for the review and document steps.

Both steps shell out to a slash command and parse a JSON report, so the agent
call is mocked and the assertions are about the contract either side of it: what
is persisted, what path the agent is handed, and what Result comes back.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from modules import workflow_ops
from modules.lib.log import reset_appenders
from modules.lib.state import verdict_path

SPEC = "adw/data/outputs/specs/abc.md"

APPROVED = json.dumps(
    {
        "success": True,
        "verdict": "APPROVED",
        "use_cases": [
            {
                "name": "Rejects empty input",
                "verdict": "Satisfied",
                "evidence": "src/parse.ts:42",
            }
        ],
        "out_of_scope": [],
        "review_summary": "All use cases satisfied.",
    }
)

REJECTED = json.dumps(
    {"success": False, "verdict": "EXIT_NO_USE_CASES", "error": "spec has no use cases"}
)

DOCUMENTED = json.dumps(
    {
        "success": True,
        "verdict": "DOCUMENTED",
        "doc_path": "app_docs/feature-abc-parse-guard.md",
        "use_cases_documented": 1,
        "out_of_scope_recorded": 0,
        "document_summary": "Documents the empty-input guard.",
    }
)


class StepTestCase(unittest.TestCase):
    """Runs each test with cwd set to a temp adw/ dir, as the pipeline does."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()
        reset_appenders()


class TestReview(StepTestCase):
    def test_persists_verdict_and_returns_summary(self):
        with mock.patch.object(workflow_ops.claude, "generate", return_value=APPROVED):
            result = workflow_ops.review(SPEC, "abc", "..")

        written = verdict_path("abc")
        self.assertTrue(os.path.exists(written))
        with open(written) as f:
            self.assertEqual(json.load(f)["verdict"], "APPROVED")

        self.assertTrue(result.payload["success"])
        self.assertEqual(result.description, "All use cases satisfied.")

    def test_gate_failure_persists_and_describes_the_error(self):
        with mock.patch.object(workflow_ops.claude, "generate", return_value=REJECTED):
            result = workflow_ops.review(SPEC, "abc", "..")

        self.assertTrue(os.path.exists(verdict_path("abc")))
        self.assertFalse(result.payload["success"])
        self.assertEqual(result.description, "spec has no use cases")

    def test_tolerates_a_fenced_verdict(self):
        fenced = f"Here you go:\n```json\n{APPROVED}\n```"
        with mock.patch.object(workflow_ops.claude, "generate", return_value=fenced):
            result = workflow_ops.review(SPEC, "abc", "..")
        self.assertEqual(result.payload["verdict"], "APPROVED")


class TestDocument(StepTestCase):
    def test_hands_the_agent_a_worktree_relative_verdict_path(self):
        with mock.patch.object(
            workflow_ops.claude, "generate", return_value=DOCUMENTED
        ) as generate:
            workflow_ops.document(SPEC, "abc", "..")

        prompt = generate.call_args.args[0]
        # the agent runs at the worktree root, a level up from this process
        self.assertIn(os.path.join("adw", "data", "outputs", "reviews", "abc.json"), prompt)
        self.assertIn(SPEC, prompt)
        self.assertEqual(generate.call_args.kwargs["cwd"], "..")

    def test_returns_the_report_as_the_payload(self):
        with mock.patch.object(workflow_ops.claude, "generate", return_value=DOCUMENTED):
            result = workflow_ops.document(SPEC, "abc", "..")

        self.assertEqual(result.payload["doc_path"], "app_docs/feature-abc-parse-guard.md")
        self.assertEqual(result.description, "Documents the empty-input guard.")


if __name__ == "__main__":
    unittest.main()
