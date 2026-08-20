"""Tests for appender fan-out and decentralized filtering (Phase 4)."""

import json
import unittest

from modules.lib.log import (
    Appender,
    AuditLogEvent,
    AuditType,
    Level,
    OperationalLogEvent,
    OperationalType,
    Outcome,
    Sink,
    Stage,
    is_audit,
    is_operational,
    log,
    min_level,
    reset_appenders,
    set_appenders,
)


class RecordingSink(Sink):
    def __init__(self):
        self.lines = []

    def write(self, formatted):
        self.lines.append(formatted)


class FailingSink(Sink):
    def write(self, formatted):
        raise IOError("sink down")


def _op(desc="x", level=Level.INFO):
    return OperationalLogEvent(
        adw_id="a", issue_id="1", description=desc,
        stage=Stage.BUILD, type=OperationalType.LLM_CALL, level=level,
    )


def _audit(desc="done"):
    return AuditLogEvent(
        adw_id="a", issue_id="1", description=desc,
        stage=Stage.PLAN, type=AuditType.OPERATION, outcome=Outcome.SUCCESS,
    )


class AppenderTestCase(unittest.TestCase):
    def tearDown(self):
        reset_appenders()  # restore default registry after each test


class TestFanOut(AppenderTestCase):
    def test_event_reaches_every_appender(self):
        a, b = RecordingSink(), RecordingSink()
        set_appenders([Appender(a), Appender(b)])
        log(_op("hi"))
        self.assertEqual(len(a.lines), 1)
        self.assertEqual(len(b.lines), 1)

    def test_no_appenders_is_silent(self):
        set_appenders([])
        log(_op("nowhere"))  # must not raise


class TestDecentralizedFiltering(AppenderTestCase):
    def test_routing_by_event_type(self):
        op_sink, audit_sink = RecordingSink(), RecordingSink()
        set_appenders([
            Appender(op_sink, filter=is_operational),
            Appender(audit_sink, filter=is_audit),
        ])
        log(_op("debugging"))
        log(_audit("branch created"))
        self.assertEqual(len(op_sink.lines), 1)
        self.assertEqual(len(audit_sink.lines), 1)
        self.assertEqual(json.loads(op_sink.lines[0])["type"], "llm_call")
        self.assertEqual(json.loads(audit_sink.lines[0])["type"], "operation")

    def test_min_level_filter(self):
        sink = RecordingSink()
        set_appenders([Appender(sink, filter=min_level(Level.WARN))])
        log(_op("noise", level=Level.INFO))   # dropped
        log(_op("problem", level=Level.ERROR))  # kept
        self.assertEqual(len(sink.lines), 1)
        self.assertEqual(json.loads(sink.lines[0])["description"], "problem")

    def test_min_level_rejects_audit_without_level(self):
        sink = RecordingSink()
        set_appenders([Appender(sink, filter=min_level(Level.DEBUG))])
        log(_audit())  # audit has no level -> rejected
        self.assertEqual(sink.lines, [])


class TestBestEffort(AppenderTestCase):
    def test_failing_appender_does_not_stop_others(self):
        good = RecordingSink()
        set_appenders([Appender(FailingSink()), Appender(good)])
        log(_op("resilient"))  # must not raise
        self.assertEqual(len(good.lines), 1)  # good appender still got it


if __name__ == "__main__":
    unittest.main()
