"""Tests for the minimal emit (Phase 2)."""

import io
import json
import unittest
from contextlib import redirect_stdout

from modules.lib.log import (
    AuditLogEvent,
    AuditType,
    OperationalLogEvent,
    OperationalType,
    Outcome,
    Stage,
    log,
)


def _capture(event):
    buf = io.StringIO()
    with redirect_stdout(buf):
        log(event)
    return buf.getvalue()


class TestEmit(unittest.TestCase):
    def test_emits_one_parseable_json_line(self):
        e = OperationalLogEvent(
            adw_id="adw-1", issue_id="42", description="model call",
            stage=Stage.BUILD, type=OperationalType.LLM_CALL,
            payload={"model": "sonnet", "tokens": 12},
        )
        out = _capture(e)
        self.assertEqual(out.count("\n"), 1)  # exactly one line
        parsed = json.loads(out)
        self.assertEqual(parsed["adw_id"], "adw-1")
        self.assertEqual(parsed["description"], "model call")
        self.assertEqual(parsed["stage"], "build")  # StrEnum serialised as str
        self.assertEqual(parsed["payload"]["model"], "sonnet")
        self.assertTrue(parsed["log_id"])
        self.assertTrue(parsed["ts"].endswith("+00:00"))

    def test_audit_event_serialises(self):
        e = AuditLogEvent(
            adw_id="adw-1", issue_id="42", description="branch created",
            stage=Stage.PLAN, type=AuditType.OPERATION, outcome=Outcome.SUCCESS,
        )
        parsed = json.loads(_capture(e))
        self.assertEqual(parsed["outcome"], "success")
        self.assertEqual(parsed["type"], "operation")

    def test_best_effort_swallows_serialisation_failure(self):
        # A set is not JSON-serialisable; log() must not raise.
        e = OperationalLogEvent(
            adw_id="a", issue_id="1", description="x",
            stage=Stage.PLAN, type=OperationalType.STEP_FAILURE,
            payload={"bad": {1, 2, 3}},
        )
        out = _capture(e)  # should not raise
        self.assertEqual(out, "")  # nothing emitted, but no crash


if __name__ == "__main__":
    unittest.main()
