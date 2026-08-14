"""Tests for state management — RunState + the JSON DAL."""

import json
import os
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace

from modules.lib.state import (
    InvalidState,
    PlanType,
    RunState,
    StateNotFound,
    create,
    read,
    state_path,
    update,
)


def _state(branch=None):
    return RunState(adw_id="adw-1", issue_id="42", plan_type=PlanType.FEATURE,
                    branch_name=branch)


class TestRunState(unittest.TestCase):
    def test_fields(self):
        s = _state()
        self.assertEqual(s.adw_id, "adw-1")
        self.assertEqual(s.plan_type, "feature")  # StrEnum == str
        self.assertIsNone(s.branch_name)

    def test_is_immutable(self):
        s = _state()
        with self.assertRaises(FrozenInstanceError):
            s.adw_id = "x"

    def test_replace_makes_new_instance(self):
        s = _state()
        s2 = replace(s, branch_name="fix-login")
        self.assertIsNone(s.branch_name)         # original untouched
        self.assertEqual(s2.branch_name, "fix-login")
        self.assertIsNot(s, s2)


class TestPaths(unittest.TestCase):
    def test_state_path(self):
        self.assertEqual(
            state_path("abc", root="/tmp"), "/tmp/adw-abc/run-state.json"
        )


class TestDAL(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_create_then_read_roundtrip(self):
        create(_state(), root=self.root)
        got = read("adw-1", root=self.root)
        self.assertEqual(got, _state())
        self.assertIsInstance(got.plan_type, PlanType)  # enum restored

    def test_update_sets_branch_and_persists(self):
        create(_state(), root=self.root)
        returned = update("adw-1", "fix-login", root=self.root)
        self.assertEqual(returned.branch_name, "fix-login")
        self.assertEqual(read("adw-1", root=self.root).branch_name, "fix-login")

    def test_read_missing_raises_not_found(self):
        with self.assertRaises(StateNotFound):
            read("nope", root=self.root)

    def test_read_malformed_raises_invalid(self):
        path = state_path("adw-1", root=self.root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("{not json")
        with self.assertRaises(InvalidState):
            read("adw-1", root=self.root)

    def test_atomic_write_leaves_no_temp(self):
        create(_state(), root=self.root)
        run_folder = os.path.dirname(state_path("adw-1", root=self.root))
        self.assertEqual(os.listdir(run_folder), ["run-state.json"])  # no .tmp

    def test_create_overwrites(self):
        create(_state(), root=self.root)
        create(_state(branch="b"), root=self.root)
        self.assertEqual(read("adw-1", root=self.root).branch_name, "b")

    def test_written_json_shape(self):
        create(_state(branch="b"), root=self.root)
        with open(state_path("adw-1", root=self.root)) as f:
            data = json.load(f)
        self.assertEqual(
            data,
            {"adw_id": "adw-1", "issue_id": "42", "plan_type": "feature",
             "branch_name": "b"},
        )


if __name__ == "__main__":
    unittest.main()
