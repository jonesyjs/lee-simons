"""Tests for Layout + Sink directly (Phase 3)."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from modules.lib.log import (
    ConsoleSink,
    FileSink,
    JsonLinesLayout,
    OperationalLogEvent,
    OperationalType,
    Stage,
)


def _event(desc="x", payload=None):
    return OperationalLogEvent(
        adw_id="adw-1", issue_id="42", description=desc,
        stage=Stage.BUILD, type=OperationalType.LLM_CALL, payload=payload or {},
    )


class TestLayout(unittest.TestCase):
    def test_jsonlines_is_single_line_parseable(self):
        out = JsonLinesLayout().format(_event("hello"))
        self.assertNotIn("\n", out)
        self.assertEqual(json.loads(out)["description"], "hello")


class TestSinks(unittest.TestCase):
    def test_console_sink_writes_stdout(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ConsoleSink().write('{"a": 1}')
        self.assertEqual(buf.getvalue(), '{"a": 1}\n')

    def test_file_sink_appends_jsonl(self):
        with tempfile.TemporaryDirectory() as root:
            s = FileSink("adw-1", root=root)
            s.write('{"n": 1}')
            s.write('{"n": 2}')
            path = os.path.join(root, "adw-1", "events.jsonl")
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertEqual([json.loads(x)["n"] for x in lines], [1, 2])


if __name__ == "__main__":
    unittest.main()
