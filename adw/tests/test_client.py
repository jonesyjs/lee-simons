"""Tests for the Client Layer — focus on the resilience behaviour.

Run from the `adw/` directory:  python3 -m unittest discover -s tests -v

subprocess and time.sleep are mocked so nothing real is spawned and no wall-clock
time is spent; the tests assert the retry/backoff/classification logic directly.
"""

import subprocess
import unittest
from types import SimpleNamespace
from unittest import mock

from modules.lib.client.base_client import BaseClient, ClientError
from modules.lib.client.subprocess_client import SubprocessClient
from modules.claude_client import ClaudeClient
from modules.git_client import GitClient


def _completed(returncode=0, stdout="", stderr=""):
    """Stand-in for subprocess.CompletedProcess."""
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class ScriptedClient(BaseClient):
    """Test double: each attempt does the next scripted outcome.

    outcomes items:
      ("ok", value)     -> return value
      ("transient",)    -> raise a retryable ClientError
      ("deterministic",)-> raise a non-retryable ClientError
    """

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def _invoke(self, request):
        self.calls += 1
        kind, *rest = self.outcomes[self.calls - 1]
        if kind == "ok":
            return rest[0]
        raise ClientError(kind, transient=(kind == "transient"))


class TestRetryLoop(unittest.TestCase):
    """The base retry/backoff action, independent of any transport."""

    def setUp(self):
        # Never actually sleep; capture the backoff durations instead.
        patcher = mock.patch("modules.lib.client.base_client.time.sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def test_success_returns_without_retry(self):
        c = ScriptedClient([("ok", "result")])
        self.assertEqual(c.call("req"), "result")
        self.assertEqual(c.calls, 1)
        self.sleep.assert_not_called()

    def test_transient_then_success_retries(self):
        c = ScriptedClient([("transient",), ("ok", "result")])
        self.assertEqual(c.call("req"), "result")
        self.assertEqual(c.calls, 2)
        self.assertEqual(self.sleep.call_count, 1)

    def test_transient_exhausts_and_surfaces(self):
        c = ScriptedClient([("transient",), ("transient",), ("transient",)])
        with self.assertRaises(ClientError):
            c.call("req")
        self.assertEqual(c.calls, 3)  # max_attempts
        self.assertEqual(self.sleep.call_count, 2)  # slept between the 3 tries

    def test_deterministic_surfaces_immediately(self):
        c = ScriptedClient([("deterministic",), ("ok", "unreached")])
        with self.assertRaises(ClientError):
            c.call("req")
        self.assertEqual(c.calls, 1)  # NOT retried
        self.sleep.assert_not_called()

    def test_backoff_is_exponential(self):
        c = ScriptedClient([("transient",), ("transient",), ("transient",)])
        with self.assertRaises(ClientError):
            c.call("req")
        # 0.1 * 2**0, 0.1 * 2**1
        self.assertEqual(
            [call.args[0] for call in self.sleep.call_args_list],
            [0.1, 0.2],
        )

    def test_respects_custom_max_attempts(self):
        c = ScriptedClient([("transient",)] * 5)
        c.max_attempts = 5
        with self.assertRaises(ClientError):
            c.call("req")
        self.assertEqual(c.calls, 5)
        self.assertEqual(self.sleep.call_count, 4)


class TestBaseIsAbstract(unittest.TestCase):
    def test_cannot_instantiate_base(self):
        with self.assertRaises(TypeError):
            BaseClient()


class TestSubprocessInvoke(unittest.TestCase):
    """The subprocess transport: outcome classification of one raw call."""

    def _run(self, client, **run_kwargs):
        with mock.patch(
            "modules.lib.client.subprocess_client.subprocess.run", **run_kwargs
        ) as run:
            return run, client._invoke(["some", "cmd"])

    def test_success_returns_stdout(self):
        with mock.patch(
            "modules.lib.client.subprocess_client.subprocess.run",
            return_value=_completed(0, stdout="hello\n"),
        ):
            self.assertEqual(SubprocessClient()._invoke(["x"]), "hello\n")

    def test_timeout_is_transient(self):
        with mock.patch(
            "modules.lib.client.subprocess_client.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1),
        ):
            with self.assertRaises(ClientError) as ctx:
                SubprocessClient()._invoke(["x"])
            self.assertTrue(ctx.exception.transient)

    def test_nonzero_unknown_is_deterministic(self):
        # Base SubprocessClient has no signatures -> unknown -> deterministic.
        with mock.patch(
            "modules.lib.client.subprocess_client.subprocess.run",
            return_value=_completed(1, stderr="something broke"),
        ):
            with self.assertRaises(ClientError) as ctx:
                SubprocessClient()._invoke(["x"])
            self.assertFalse(ctx.exception.transient)
            self.assertEqual(ctx.exception.code, 1)

    def test_nonzero_matching_signature_is_transient(self):
        with mock.patch(
            "modules.lib.client.subprocess_client.subprocess.run",
            return_value=_completed(1, stderr="Error: 429 rate limit exceeded"),
        ):
            with self.assertRaises(ClientError) as ctx:
                ClaudeClient()._invoke(["x"])
            self.assertTrue(ctx.exception.transient)


class TestRecognition(unittest.TestCase):
    """Per-CLI transient recognition (_is_transient)."""

    def test_claude_signatures(self):
        c = ClaudeClient()
        self.assertTrue(c._is_transient("Error: rate limit exceeded"))
        self.assertTrue(c._is_transient("API overloaded, retry"))
        self.assertFalse(c._is_transient("unknown model: foo"))

    def test_git_signatures(self):
        g = GitClient()
        self.assertTrue(g._is_transient("fatal: could not lock config file"))
        self.assertFalse(g._is_transient("fatal: branch already exists"))

    def test_case_insensitive(self):
        self.assertTrue(ClaudeClient()._is_transient("RATE LIMIT hit"))

    def test_cross_cli_signatures_do_not_leak(self):
        # git stderr must not match Claude's signatures and vice versa.
        self.assertFalse(GitClient()._is_transient("rate limit"))
        self.assertFalse(ClaudeClient()._is_transient("index.lock"))


class TestArgvBuilding(unittest.TestCase):
    """The command surface: one function, one command, variation via inputs."""

    def test_generate_builds_bare_argv(self):
        with mock.patch.object(ClaudeClient, "call", return_value="out") as call:
            ClaudeClient().generate("hi")
            call.assert_called_once_with(["claude", "-p", "hi"])

    def test_generate_adds_model_when_given(self):
        with mock.patch.object(ClaudeClient, "call", return_value="out") as call:
            ClaudeClient().generate("hi", model="sonnet")
            call.assert_called_once_with(["claude", "-p", "hi", "--model", "sonnet"])

    def test_worktree_add_builds_argv(self):
        with mock.patch.object(GitClient, "call", return_value="out") as call:
            GitClient().worktree_add("/tmp/wt", "feat-x")
            call.assert_called_once_with(
                ["git", "worktree", "add", "-b", "feat-x", "/tmp/wt"]
            )

    def test_diff_builds_argv(self):
        with mock.patch.object(GitClient, "call", return_value="out") as call:
            GitClient().diff("/tmp/wt")
            call.assert_called_once_with(["git", "-C", "/tmp/wt", "diff"])

    def test_commit_builds_argv(self):
        with mock.patch.object(GitClient, "call", return_value="out") as call:
            GitClient().commit("/tmp/wt", "do the thing")
            call.assert_called_once_with(
                ["git", "-C", "/tmp/wt", "commit", "-m", "do the thing"]
            )


class TestEndToEndResilience(unittest.TestCase):
    """A real client retrying a transient subprocess failure to success."""

    def test_claude_retries_transient_then_succeeds(self):
        outcomes = [
            _completed(1, stderr="503 temporarily unavailable"),  # transient
            _completed(0, stdout="pong\n"),  # success
        ]
        with mock.patch("modules.lib.client.base_client.time.sleep"), mock.patch(
            "modules.lib.client.subprocess_client.subprocess.run", side_effect=outcomes
        ) as run:
            result = ClaudeClient().generate("ping")
        self.assertEqual(result, "pong\n")
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
