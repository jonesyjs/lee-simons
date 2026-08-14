"""Tests for schema evolution / upcasting (Phase 5)."""

import unittest

from modules.lib.log.models.schema import CURRENT_VERSION, register_upcaster, upcast


class TestUpcast(unittest.TestCase):
    def test_current_version_is_identity(self):
        raw = {"schema_version": CURRENT_VERSION, "description": "x"}
        self.assertEqual(upcast(raw), raw)

    def test_missing_upcaster_raises(self):
        with self.assertRaises(ValueError):
            upcast({"schema_version": "0.9"}, target="1.0")

    def test_registered_chain_migrates(self):
        # 1.0 -> 1.1 adds a field and bumps the version.
        def to_1_1(d):
            d = {**d, "schema_version": "1.1", "new_field": True}
            return d

        register_upcaster("1.0", to_1_1)
        out = upcast({"schema_version": "1.0", "description": "x"}, target="1.1")
        self.assertEqual(out["schema_version"], "1.1")
        self.assertTrue(out["new_field"])
        self.assertEqual(out["description"], "x")  # additive; original preserved

    def test_non_advancing_upcaster_raises(self):
        register_upcaster("2.0", lambda d: d)  # forgets to bump
        with self.assertRaises(ValueError):
            upcast({"schema_version": "2.0"}, target="2.1")


if __name__ == "__main__":
    unittest.main()
