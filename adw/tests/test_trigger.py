"""Tests for the shared trigger core."""

import unittest
from unittest import mock

from modules import git_ops, trigger


class TestShouldRun(unittest.TestCase):
    def test_valid_token(self):
        self.assertTrue(trigger._should_run("please run adw_plan_build"))

    def test_loop_guard_ignores_own_comment(self):
        self.assertFalse(trigger._should_run(f"{git_ops.BOT_IDENTIFIER} adw_plan_build"))

    def test_no_routing_token(self):
        self.assertFalse(trigger._should_run("just a normal issue"))

    def test_empty(self):
        self.assertFalse(trigger._should_run(""))


class TestParseTrigger(unittest.TestCase):
    def test_slice_only(self):
        self.assertEqual(trigger._parse_trigger("adw_plan_build"), ("plan_build", None))

    def test_slice_and_id(self):
        self.assertEqual(
            trigger._parse_trigger("adw_review_document adw-20260815-abcd1234"),
            ("review_document", "adw-20260815-abcd1234"),
        )

    def test_full_pipeline_slice(self):
        slice_name, _ = trigger._parse_trigger("adw_plan_build_review_document")
        self.assertEqual(slice_name, "plan_build_review_document")

    def test_none(self):
        self.assertEqual(trigger._parse_trigger("nothing here"), (None, None))


class TestMintAdwId(unittest.TestCase):
    def test_format(self):
        self.assertTrue(trigger._mint_adw_id().startswith("adw-"))


class TestHandleIssue(unittest.TestCase):
    def test_launches_and_returns_new_id(self):
        with mock.patch.object(trigger.subprocess, "Popen") as popen, \
                mock.patch.object(git_ops.github, "comment", return_value="url"):
            adw_id = trigger.handle_issue("7", "do adw_plan_build")
        self.assertTrue(adw_id.startswith("adw-"))
        popen.assert_called_once()

    def test_loop_guard_does_not_launch(self):
        with mock.patch.object(trigger.subprocess, "Popen") as popen:
            self.assertIsNone(
                trigger.handle_issue("7", f"{git_ops.BOT_IDENTIFIER} adw_plan_build")
            )
            popen.assert_not_called()

    def test_no_token_does_not_launch(self):
        with mock.patch.object(trigger.subprocess, "Popen") as popen:
            self.assertIsNone(trigger.handle_issue("7", "hello"))
            popen.assert_not_called()

    def test_dependent_slice_without_id_errors(self):
        with mock.patch.object(trigger.subprocess, "Popen") as popen, \
                mock.patch.object(git_ops.github, "comment", return_value="url") as comment:
            self.assertIsNone(trigger.handle_issue("7", "run adw_review_document"))
            popen.assert_not_called()
            comment.assert_called_once()  # posted the error comment

    def test_dependent_slice_with_id_launches(self):
        with mock.patch.object(trigger.subprocess, "Popen") as popen, \
                mock.patch.object(git_ops.github, "comment", return_value="url"):
            adw_id = trigger.handle_issue("7", "adw_review_document adw-123")
        self.assertEqual(adw_id, "adw-123")
        popen.assert_called_once()


class TestCommentCarriesBotMarker(unittest.TestCase):
    def test_git_ops_comment_prepends_identifier(self):
        with mock.patch.object(git_ops.github, "comment", return_value="url") as raw:
            git_ops.comment("7", "hello")
        body = raw.call_args.args[1]
        self.assertTrue(body.startswith(git_ops.BOT_IDENTIFIER))


if __name__ == "__main__":
    unittest.main()
