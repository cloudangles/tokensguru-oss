# ruff: noqa: E501
import copy
import json
import random
import string
import time

import pytest

from tokensguru.governance import (
    ApiKeyDetector,
    EmailDetector,
    Guardrail,
    GuardrailResult,
    PiiDetector,
    PiiRedactor,
    RedactionResult,
)

redactor = PiiRedactor()
RNG = random.Random(99)  # noqa: S311
KEY = "ghp_" + "".join(
    RNG.choice(string.ascii_letters + string.digits) for _ in range(36)
)
SAMPLE = (
    "Hi, I'm jane@example.com (phone (212) 555-0147). Card 4111 1111 1111 1111, "
    "host 192.168.1.10, SSN 123-45-6789, DOB: 12/03/1990, "
    "IBAN GB82 WEST 1234 5698 7654 32, passport: X1234567."
)


def test_placeholder_mode_is_the_default():
    result = redactor.check(SAMPLE)
    assert result.redacted_text == (
        "Hi, I'm [EMAIL] (phone [PHONE]). Card [CREDIT_CARD], host [IP_ADDRESS], "
        "SSN [SSN], DOB: [DATE_OF_BIRTH], IBAN [IBAN], passport: [PASSPORT]."
    )
    assert result.mode == "placeholder"
    assert (result.decision, result.count) == ("redact", 8)
    assert result.replacements == {
        "EMAIL": 1, "PHONE": 1, "CREDIT_CARD": 1, "IP_ADDRESS": 1,
        "SSN": 1, "DATE_OF_BIRTH": 1, "IBAN": 1, "PASSPORT": 1,
    }  # fmt: skip


def test_mask_mode_keeps_a_little_context():
    text = PiiRedactor(mode="mask").check(SAMPLE).redacted_text
    assert "j***@example.com" in text
    assert "(XXX) XXX-0147" in text
    assert "**** **** **** 1111" in text
    assert "192.168.*.*" in text
    assert "***-**-6789" in text
    assert "**/**/****" in text
    assert "GB** **** **** **** **54 32" in text
    assert "passport: ******67" in text


def test_pseudonym_mode_numbers_each_distinct_value():
    text = "jane@example.com wrote to bob@corp.io, then Jane@Example.com replied"
    out = PiiRedactor(mode="pseudonym").check(text).redacted_text
    assert out == "<EMAIL_1> wrote to <EMAIL_2>, then <EMAIL_1> replied"


def test_pseudonyms_for_numbers_ignore_formatting():
    text = "call (212) 555-0147 or 212.555.0147 or 212-555-0199"
    out = PiiRedactor(mode="pseudonym").check(text).redacted_text
    assert out == "call <PHONE_1> or <PHONE_1> or <PHONE_2>"


def test_pseudonym_numbers_are_counted_per_type():
    text = "a@b.com 8.8.8.8 c@d.com 1.1.1.1"
    out = PiiRedactor(mode="pseudonym").check(text).redacted_text
    assert out == "<EMAIL_1> <IP_ADDRESS_1> <EMAIL_2> <IP_ADDRESS_2>"


@pytest.mark.parametrize("mode", ["placeholder", "mask", "pseudonym"])
def test_redacting_again_changes_nothing(mode):
    once = PiiRedactor(mode=mode).check(SAMPLE)
    twice = PiiRedactor(mode=mode).check(once.redacted_text)
    assert (twice.decision, twice.count) == ("pass", 0)
    assert twice.redacted_text == once.redacted_text


@pytest.mark.parametrize("mode", ["placeholder", "mask", "pseudonym"])
def test_the_original_personal_data_is_gone_from_the_output(mode):
    out = (
        PiiRedactor(mode=mode, include_secrets=True)
        .check(SAMPLE + " " + KEY)
        .redacted_text
    )
    for gone in (
        "jane@example.com",
        "555-0147",
        "4111 1111",
        "123-45-6789",
        "12/03/1990",
        "X1234567",
        KEY,
    ):
        assert gone not in out, (mode, gone)
    assert PiiDetector().check(out).count == 0
    assert ApiKeyDetector().check(out).count == 0


def test_text_around_the_findings_is_kept_exactly():
    text = "  a\n\tjane@example.com\r\né中 x  "
    out = redactor.redact(text)
    assert out == "  a\n\t[EMAIL]\r\né中 x  "


def test_nothing_found_returns_the_same_text():
    result = redactor.check("nothing personal here")
    assert result.redacted_text == "nothing personal here"
    assert (result.decision, result.count, result.reason) == (
        "pass",
        0,
        "Nothing to redact",
    )
    assert result.replacements == {}


def test_empty_text():
    assert redactor.check("").redacted_text == ""


def test_secrets_are_only_redacted_when_asked():
    text = f"key {KEY} mail a@b.com"
    assert redactor.redact(text) == f"key {KEY} mail [EMAIL]"
    both = PiiRedactor(include_secrets=True)
    assert both.redact(text) == "key [SECRET] mail [EMAIL]"
    assert (
        PiiRedactor(mode="mask", include_secrets=True).redact(text)
        == "key ghp_[SECRET] mail a***@b.com"
    )
    assert (
        PiiRedactor(mode="pseudonym", include_secrets=True).redact(text)
        == "key <SECRET_1> mail <EMAIL_1>"
    )


def test_a_private_key_block_becomes_one_placeholder():
    body = "\n".join(
        "".join(RNG.choice(string.ascii_letters) for _ in range(64)) for _ in range(3)
    )
    block = (
        "-----BEGIN " + "PRIVATE KEY-----\n" + body + "\n-----END " + "PRIVATE KEY-----"
    )
    out = PiiRedactor(include_secrets=True).redact(f"before\n{block}\nafter")
    assert out == "before\n[PRIVATE_KEY]\nafter"


def test_chosen_types_and_allowed_domains():
    text = "a@x.com b@corp.io 8.8.8.8"
    assert PiiRedactor(types=["email"]).redact(text) == "[EMAIL] [EMAIL] 8.8.8.8"
    assert (
        PiiRedactor(allowed_domains=["corp.io"]).redact(text)
        == "[EMAIL] b@corp.io [IP_ADDRESS]"
    )
    assert (
        PiiRedactor(include_private_ips=False).redact("10.0.0.1 8.8.8.8")
        == "10.0.0.1 [IP_ADDRESS]"
    )


def test_disguised_values_are_redacted():
    zw = chr(0x200B)
    assert redactor.redact(f"j{zw}ane@example.com") == "[EMAIL]"
    assert redactor.redact("jane[at]example[dot]com") == "[EMAIL]"
    assert PiiRedactor(mode="mask").redact("jane[at]example[dot]com") == "[EMAIL]"


def test_overlapping_findings_from_two_detectors_are_redacted_once():
    text = f"Authorization: Bearer {KEY} and a@b.com"
    out = PiiRedactor(include_secrets=True).redact(text)
    assert out == "Authorization: Bearer [SECRET] and [EMAIL]"


def test_result_details_and_privacy():
    result = redactor.check(SAMPLE)
    assert isinstance(result, RedactionResult)
    assert isinstance(result, GuardrailResult)
    assert isinstance(redactor, Guardrail)
    assert result.guardrail_id == "pii_redaction"
    assert result.reason == "Redacted 8 items"
    assert PiiRedactor().check("a@b.com").reason == "Redacted 1 item"
    data = result.to_dict()
    json.dumps(data)
    assert data["mode"] == "placeholder"
    assert data["redacted_text"] == result.redacted_text
    assert "jane@example.com" not in json.dumps(data)
    assert "mode" in str(result)


def test_invalid_mode_and_input():
    with pytest.raises(ValueError, match="mode"):
        PiiRedactor(mode="hash")
    with pytest.raises(TypeError):
        redactor.check(None)
    with pytest.raises(TypeError):
        redactor.redact_messages("hello")


MESSAGES = [
    {"role": "system", "content": "You help jane@example.com"},
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "My card is 4111 1111 1111 1111"},
            {"type": "image_url", "image_url": {"url": "http://x/jane@example.com"}},
        ],
    },
    {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "1",
                "function": {
                    "name": "send_email",
                    "arguments": '{"to": "jane@example.com", "n": 3, "nested": {"cc": ["bob@corp.io"], "ok": true}}',
                },
            }
        ],
    },
    {"role": "tool", "content": "sent to 8.8.8.8"},
    "not a message",
    {"role": "user"},
]


def test_messages_are_redacted_in_every_text_field():
    original = copy.deepcopy(MESSAGES)
    result = redactor.redact_messages(MESSAGES)
    out = result.redacted_messages
    assert original == MESSAGES
    assert out[0]["content"] == "You help [EMAIL]"
    assert out[1]["content"][0]["text"] == "My card is [CREDIT_CARD]"
    assert out[1]["content"][1] == MESSAGES[1]["content"][1]
    assert out[3]["content"] == "sent to [IP_ADDRESS]"
    assert out[4:] == MESSAGES[4:]
    assert result.decision == "redact"


def test_tool_call_arguments_stay_valid_json_with_the_same_shape():
    out = redactor.redact_messages(MESSAGES).redacted_messages
    arguments = out[2]["tool_calls"][0]["function"]["arguments"]
    assert json.loads(arguments) == {
        "to": "[EMAIL]",
        "n": 3,
        "nested": {"cc": ["[EMAIL]"], "ok": True},
    }
    assert out[2]["tool_calls"][0]["function"]["name"] == "send_email"


def test_invalid_json_arguments_are_redacted_as_text():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [{"function": {"arguments": "to=jane@example.com"}}],
        }
    ]
    out = redactor.redact_messages(messages).redacted_messages
    assert out[0]["tool_calls"][0]["function"]["arguments"] == "to=[EMAIL]"


def test_message_findings_say_where_they_were_found():
    result = redactor.redact_messages(MESSAGES)
    assert [f.path for f in result.findings] == [
        "messages[0].content",
        "messages[1].content[0].text",
        "messages[2].tool_calls[0].function.arguments",
        "messages[2].tool_calls[0].function.arguments",
        "messages[3].content",
    ]
    assert result.to_dict()["redacted_messages"] == result.redacted_messages


def test_pseudonyms_stay_consistent_across_messages():
    messages = [
        {"role": "user", "content": "from a@b.com"},
        {"role": "assistant", "content": "to c@d.com"},
        {"role": "user", "content": "again a@b.com"},
    ]
    out = PiiRedactor(mode="pseudonym").redact_messages(messages).redacted_messages
    assert [m["content"] for m in out] == [
        "from <EMAIL_1>",
        "to <EMAIL_2>",
        "again <EMAIL_1>",
    ]


def test_only_chosen_roles_are_redacted():
    messages = [
        {"role": "system", "content": "admin@corp.io"},
        {"role": "user", "content": "me@corp.io"},
    ]
    result = redactor.redact_messages(messages, roles=["user"])
    assert [m["content"] for m in result.redacted_messages] == [
        "admin@corp.io",
        "[EMAIL]",
    ]
    assert result.input_length == len("me@corp.io")


def test_an_empty_message_list():
    result = redactor.redact_messages([])
    assert (result.redacted_messages, result.decision) == ([], "pass")


def test_hostile_and_large_inputs_are_handled_quickly():
    started = time.perf_counter()
    redactor.check("1 " * 250_000)
    redactor.check("a@" * 100_000)
    big = redactor.check("Contact ops@example.com for help. " * 20_000)
    assert big.count == 20_000
    assert "@" not in big.redacted_text
    assert time.perf_counter() - started < 8


def test_fuzz_redaction_is_idempotent_and_never_leaves_detectable_data():
    rng = random.Random(7)  # noqa: S311
    pieces = [
        "a@b.com",
        "4111 1111 1111 1111",
        "123-45-6789",
        "(212) 555-0147",
        "8.8.8.8",
        "DOB: 12/03/1990",
        " ",
        "x",
        "\n",
        "jane[at]x[dot]org",
        "1234",
        "passport: A1234567",
    ]
    for mode in ("placeholder", "mask", "pseudonym"):
        subject = PiiRedactor(mode=mode)
        for _ in range(600):
            text = " ".join(rng.choice(pieces) for _ in range(rng.randint(0, 12)))
            once = subject.check(text)
            twice = subject.check(once.redacted_text)
            assert twice.count == 0, (mode, text, once.redacted_text)
            assert twice.redacted_text == once.redacted_text
            assert subject.check(text).redacted_text == once.redacted_text


def test_the_email_detector_ignores_masked_addresses():
    assert EmailDetector().check("j***@example.com").count == 0
    assert EmailDetector().check("jane@example.com").count == 1
