"""Tests for the log event model (Phase 1)."""

import unittest
from dataclasses import FrozenInstanceError  # noqa: F401  (kept for parity if frozen later)

from modules.lib.log import (
    SCHEMA_VERSION,
    AuditLogEvent,
    AuditType,
    Level,
    LogEvent,
    OperationalLogEvent,
    OperationalType,
    Outcome,
    Stage,
)


class TestBaseEnvelope(unittest.TestCase):
    def test_identity_fields_are_stamped(self):
        e = LogEvent(adw_id="adw-1", issue_id="42", description="hi")
        self.assertEqual(e.schema_version, SCHEMA_VERSION)
        self.assertTrue(e.log_id)  # a uuid string
        self.assertIn("T", e.ts)  # ISO-8601
        self.assertTrue(e.ts.endswith("+00:00"))  # UTC
        self.assertEqual(e.payload, {})

    def test_log_ids_are_unique(self):
        a = LogEvent(adw_id="x", issue_id="1", description="a")
        b = LogEvent(adw_id="x", issue_id="1", description="b")
        self.assertNotEqual(a.log_id, b.log_id)


class TestOperationalEvent(unittest.TestCase):
    def test_requires_stage_and_type_defaults_info(self):
        e = OperationalLogEvent(
            adw_id="adw-1",
            issue_id="42",
            description="model call",
            stage=Stage.BUILD,
            type=OperationalType.LLM_CALL,
            payload={"model": "sonnet", "tokens": 12},
        )
        self.assertEqual(e.level, Level.INFO)  # default
        self.assertEqual(e.stage, "build")  # StrEnum == str
        self.assertEqual(e.payload["model"], "sonnet")

    def test_is_a_logevent(self):
        e = OperationalLogEvent(
            adw_id="a", issue_id="1", description="x",
            stage=Stage.PLAN, type=OperationalType.STEP_FAILURE,
        )
        self.assertIsInstance(e, LogEvent)


class TestAuditEvent(unittest.TestCase):
    def test_requires_outcome(self):
        e = AuditLogEvent(
            adw_id="adw-1",
            issue_id="42",
            description="branch created",
            stage=Stage.PLAN,
            type=AuditType.OPERATION,
            outcome=Outcome.SUCCESS,
        )
        self.assertEqual(e.outcome, "success")
        self.assertEqual(e.type, "operation")

    def test_missing_outcome_is_error(self):
        with self.assertRaises(TypeError):
            AuditLogEvent(
                adw_id="a", issue_id="1", description="x",
                stage=Stage.REVIEW, type=AuditType.STEP,
            )


class TestEnumsAreStrings(unittest.TestCase):
    def test_strenum_values(self):
        self.assertEqual(Stage.DOCUMENT, "document")
        self.assertEqual(Level.ERROR, "error")
        self.assertEqual(Outcome.STATE_TRANSITION, "state_transition")

    def test_operational_and_audit_types_disjoint(self):
        op = {t.value for t in OperationalType}
        au = {t.value for t in AuditType}
        self.assertEqual(op & au, set())  # domains never share a type


if __name__ == "__main__":
    unittest.main()
