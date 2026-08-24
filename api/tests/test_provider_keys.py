"""Provider key masking and validation -- never echo a raw key back.

Also locks in a real bug found during manual testing: deleting a key
(implemented as inserting an empty-string api_key row, since
ReplacingMergeTree has no direct DELETE) must make it disappear from the
list -- it must not resurface with a blank masked_key.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import provider_keys  # noqa: E402
from provider_keys import _mask, _VALID_PROVIDERS  # noqa: E402


class MaskTests(unittest.TestCase):
    def test_long_key_shows_only_first_and_last_four(self) -> None:
        masked = _mask("sk-abcdefghijklmnopqrstuvwxyz")
        self.assertEqual(masked, "sk-a…wxyz")
        self.assertNotIn("efghijk", masked)

    def test_short_key_is_fully_redacted(self) -> None:
        masked = _mask("short")
        self.assertEqual(masked, "•" * 5)
        self.assertNotIn("s", masked)
        self.assertNotIn("h", masked)


class ValidProvidersTests(unittest.TestCase):
    def test_known_providers_present(self) -> None:
        for p in ("openai", "anthropic", "groq", "deepseek", "google", "ollama"):
            self.assertIn(p, _VALID_PROVIDERS)

    def test_self_hosted_alias_excluded(self) -> None:
        # "self-hosted" is an alias of "ollama" in the registry -- only one
        # canonical name should be offered in the Settings dropdown.
        self.assertNotIn("self-hosted", _VALID_PROVIDERS)


class ListQueryFiltersDeletedKeysTests(unittest.TestCase):
    def test_list_query_excludes_empty_api_key_rows(self) -> None:
        """A deleted key (empty-string row) must not appear in the list --
        assert the WHERE clause actually filters it, not just that the
        Python-side response shape looks right."""
        ch = MagicMock()
        ch.query.return_value = MagicMock(result_rows=[])
        with patch.object(provider_keys, "get_client", return_value=ch):
            provider_keys.list_provider_keys(auth={"tenant_id": "default"})

        query_arg = ch.query.call_args.args[0]
        self.assertIn("api_key != ''", query_arg)


if __name__ == "__main__":
    unittest.main()
