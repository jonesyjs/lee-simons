"""Tests for git_ops branch-name derivation.

_generate_branch_name asks the model for a bare kebab-case name, but the reply
often arrives wrapped in backticks/quotes or trailed by prose. _slugify_branch_name
is the guard that turns whatever comes back into a valid branch name.
"""

import unittest

from modules.git_ops import _slugify_branch_name


class TestSlugifyBranchName(unittest.TestCase):
    def test_passes_through_a_clean_name(self):
        self.assertEqual(_slugify_branch_name("fix-readme-stale-paths"), "fix-readme-stale-paths")

    def test_strips_markdown_backticks(self):
        # the bug that shipped a `...`-wrapped branch to git
        self.assertEqual(_slugify_branch_name("`fix-readme-stale-paths`"), "fix-readme-stale-paths")

    def test_strips_quotes(self):
        self.assertEqual(_slugify_branch_name('"fix-login"'), "fix-login")

    def test_lowercases_and_collapses_separators(self):
        self.assertEqual(_slugify_branch_name("Fix: README Stale Paths"), "fix-readme-stale-paths")

    def test_takes_only_the_first_line(self):
        self.assertEqual(_slugify_branch_name("add-logging\n\nHere's the name above."), "add-logging")

    def test_trims_surrounding_whitespace(self):
        self.assertEqual(_slugify_branch_name("  update-deps  "), "update-deps")

    def test_raises_when_nothing_usable_remains(self):
        for junk in ("", "   ", "```", "!!!"):
            with self.assertRaises(ValueError):
                _slugify_branch_name(junk)


if __name__ == "__main__":
    unittest.main()
