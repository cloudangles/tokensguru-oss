"""Repeated-content collapse: the one optimization stage in OSS.

Verifies the three properties the design promises:
1. An obvious 3+ consecutive repeat gets collapsed with a non-zero token
   saving and an honest marker (not silently vanished).
2. Fenced code blocks are never touched, even if they contain repeated
   lines internally.
3. Ordinary non-repeated prose is returned completely unchanged.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from optimize.repeated_content import collapse_repeated_content  # noqa: E402


class RepeatedContentCollapseTests(unittest.TestCase):
    def test_collapses_an_obvious_repeat(self) -> None:
        text = "Please fix the bug.\n" + ("Error: connection refused\n" * 5)
        out, saved = collapse_repeated_content(text)
        self.assertIn("Error: connection refused", out)
        self.assertIn("repeated 4 more time(s)", out)
        self.assertGreater(saved, 0)
        # The redundant copies are gone, not just marked -- content shrank.
        self.assertLess(len(out), len(text))

    def test_leaves_fenced_code_untouched_even_with_internal_repeats(self) -> None:
        code = "```python\nfor i in range(3):\n    print(i)\n    print(i)\n    print(i)\n```"
        out, saved = collapse_repeated_content(code)
        self.assertEqual(out, code)
        self.assertEqual(saved, 0)

    def test_non_repeated_prose_is_unchanged(self) -> None:
        text = "This is a normal prompt.\nIt has several different lines.\nNone of them repeat."
        out, saved = collapse_repeated_content(text)
        self.assertEqual(out, text)
        self.assertEqual(saved, 0)

    def test_two_repeats_is_not_enough_to_collapse(self) -> None:
        text = "line one\nsame line\nsame line\nline four"
        out, saved = collapse_repeated_content(text)
        self.assertEqual(out, text)
        self.assertEqual(saved, 0)

    def test_mixed_prose_and_code_only_collapses_the_prose_part(self) -> None:
        text = (
            "note\nnote\nnote\n"
            "```\nx = 1\nx = 1\nx = 1\n```"
        )
        out, saved = collapse_repeated_content(text)
        self.assertIn("```\nx = 1\nx = 1\nx = 1\n```", out)
        self.assertIn("repeated 2 more time(s)", out)
        self.assertGreater(saved, 0)


if __name__ == "__main__":
    unittest.main()
