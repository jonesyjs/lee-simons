"""Tests for the review and document steps."""

import os
import tempfile
import unittest
from unittest import mock

from modules import git_ops, workflow_ops
from modules.lib.log import reset_appenders


class TestReview(unittest.TestCase):
    def tearDown(self):
        reset_appenders()

    def test_returns_result_and_posts_summary(self):
        with tempfile.TemporaryDirectory() as root:
            spec = os.path.join(root, "spec.md")
            with open(spec, "w") as f:
                f.write("# Spec")
            with mock.patch.object(git_ops.git, "diff", return_value="diff"), \
                    mock.patch.object(git_ops.github, "comment", return_value="url") as comment:
                result = workflow_ops.review(spec, root, "7")
            self.assertTrue(result.success)
            self.assertEqual(len(result.summary), 2)
            # summary posted directly to the issue, as bullets
            comment.assert_called_once()
            issue, body = comment.call_args.args
            self.assertEqual(issue, "7")
            self.assertIn("- implements the spec", body)


class TestDocument(unittest.TestCase):
    def tearDown(self):
        reset_appenders()

    def test_writes_two_docs(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(git_ops.git, "diff", return_value="diff"):
                result = workflow_ops.document(root, ["ok"])
            docs = os.path.join(root, "docs")
            self.assertTrue(os.path.exists(os.path.join(docs, "what-was-built.md")))
            self.assertTrue(os.path.exists(os.path.join(docs, "what-was-learned.md")))
            self.assertEqual(result.description, "documentation created")


if __name__ == "__main__":
    unittest.main()
