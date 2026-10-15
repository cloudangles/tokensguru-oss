import unittest
import uuid
from unittest.mock import patch

import tokenguru_client as tg


class ChatCompletionsTests(unittest.TestCase):
    def test_package_version(self):
        self.assertEqual(tg.__version__, "0.1.0")

    def setUp(self):
        tg._token = "test-token"

    def tearDown(self):
        tg._token = None

    @patch("tokenguru_client.request")
    def test_optimization_is_enabled_by_default(self, send):
        send.return_value = {"choices": [], "tokensight": {"optimization": {"enabled": True}}}

        response = tg.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
        )

        body = send.call_args.args[2]
        self.assertFalse(body["skip_token_optimizer"])
        self.assertTrue(response.tokensight.optimization.enabled)

    @patch("tokenguru_client.request")
    def test_optimization_can_be_disabled_for_a_baseline(self, send):
        send.return_value = {"choices": []}

        tg.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            optimize=False,
        )

        self.assertTrue(send.call_args.args[2]["skip_token_optimizer"])

    def test_internal_skip_flag_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "optimize=False"):
            tg.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                skip_token_optimizer=True,
            )

    @patch("tokenguru_client.request")
    def test_standalone_calls_use_separate_trace_ids(self, send):
        send.return_value = {"choices": []}

        for _ in range(2):
            tg.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Same prompt"}],
            )

        first_headers = send.call_args_list[0].kwargs["headers_extra"]
        second_headers = send.call_args_list[1].kwargs["headers_extra"]
        uuid.UUID(first_headers["X-TG-Trace-Id"])
        uuid.UUID(second_headers["X-TG-Trace-Id"])
        self.assertNotEqual(
            first_headers["X-TG-Trace-Id"],
            second_headers["X-TG-Trace-Id"],
        )


if __name__ == "__main__":
    unittest.main()
