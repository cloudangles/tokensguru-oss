import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tokensight_oss.cost import calculate_cost  # noqa: E402


class CostCalculationTests(unittest.TestCase):
    def test_exact_match(self) -> None:
        in_cost, out_cost = calculate_cost("openai", "gpt-4o-mini", 1_000_000, 1_000_000)
        self.assertEqual(in_cost, Decimal("0.15"))
        self.assertEqual(out_cost, Decimal("0.60"))

    def test_versioned_model_name_strips_date_suffix(self) -> None:
        in_cost, _ = calculate_cost("openai", "gpt-4o-mini-2024-07-18", 1_000_000, 0)
        self.assertEqual(in_cost, Decimal("0.15"))

    def test_unknown_model_returns_zero_not_a_guess(self) -> None:
        in_cost, out_cost = calculate_cost("openai", "totally-made-up-model", 1000, 1000)
        self.assertEqual(in_cost, Decimal("0"))
        self.assertEqual(out_cost, Decimal("0"))

    def test_zero_tokens_is_zero_cost(self) -> None:
        in_cost, out_cost = calculate_cost("anthropic", "claude-sonnet-4-5", 0, 0)
        self.assertEqual(in_cost, Decimal("0"))
        self.assertEqual(out_cost, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
