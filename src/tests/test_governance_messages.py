import copy

import pytest

from tokensguru.governance import ApiKeyDetector, EmailDetector, PiiDetector
from tokensguru.governance.messages import JSON, TEXT, iter_slots, rewrite_texts

MESSAGES = [
    {"role": "system", "content": "admin@corp.io"},
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "me@corp.io"},
            {"type": "image_url", "image_url": {"url": "x"}},
            "plain string part",
            {"type": "text"},
        ],
    },
    {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"function": {"arguments": '{"a": 1}'}},
            "junk",
            {"function": "nope"},
        ],
    },
    {"role": "assistant", "function_call": {"name": "f", "arguments": '{"b": 2}'}},
    {"role": 5, "content": "numeric role"},
    "not a message",
    None,
    {"content": "no role"},
]


def test_slots_cover_every_kind_of_text_and_skip_the_rest():
    slots = list(iter_slots(MESSAGES))
    assert [(s.path, s.role, s.kind) for s in slots] == [
        ("messages[0].content", "system", TEXT),
        ("messages[1].content[0].text", "user", TEXT),
        ("messages[2].tool_calls[0].function.arguments", "assistant", JSON),
        ("messages[3].function_call.arguments", "assistant", JSON),
        ("messages[4].content", None, TEXT),
        ("messages[7].content", None, TEXT),
    ]
    assert [s.text for s in slots][:2] == ["admin@corp.io", "me@corp.io"]


def test_rewrite_works_on_a_copy():
    original = copy.deepcopy(MESSAGES)
    out = rewrite_texts(MESSAGES, lambda slot: slot.text.upper())
    assert original == MESSAGES
    assert out[0]["content"] == "ADMIN@CORP.IO"
    assert out[1]["content"][0]["text"] == "ME@CORP.IO"
    assert out[1]["content"][2] == "plain string part"
    assert out[5] == "not a message"


def test_check_messages_finds_things_with_their_paths():
    result = EmailDetector().check_messages(MESSAGES)
    assert [(f.type, f.path) for f in result.findings] == [
        ("email", "messages[0].content"),
        ("email", "messages[1].content[0].text"),
    ]
    assert result.input_length == len("admin@corp.io") + len("me@corp.io") + len(
        '{"a": 1}'
    ) + len('{"b": 2}') + len("numeric role") + len("no role")
    assert result.decision == "flag"


def test_check_messages_can_be_limited_to_roles():
    result = EmailDetector().check_messages(MESSAGES, roles=["user"])
    assert [f.path for f in result.findings] == ["messages[1].content[0].text"]
    assert result.input_length == len("me@corp.io")
    assert EmailDetector().check_messages(MESSAGES, roles=[]).findings == ()


def test_offsets_are_relative_to_each_text_field():
    messages = [{"role": "user", "content": "x " * 10 + "a@b.com"}]
    (finding,) = EmailDetector().check_messages(messages).findings
    assert finding.start == 20
    assert finding.to_dict()["path"] == "messages[0].content"


def test_a_clean_chat_passes_and_the_list_is_untouched():
    clean = [{"role": "user", "content": "hello"}]
    before = copy.deepcopy(clean)
    result = PiiDetector().check_messages(clean)
    assert (result.decision, result.count) == ("pass", 0)
    assert clean == before
    assert PiiDetector().check_messages([]).count == 0


def test_tuples_are_accepted_and_other_types_are_not():
    assert (
        EmailDetector().check_messages(({"role": "user", "content": "a@b.com"},)).count
        == 1
    )
    for bad in (None, "text", {"role": "user"}, 5):
        with pytest.raises(TypeError, match="messages must be a list"):
            EmailDetector().check_messages(bad)


def test_tool_call_arguments_are_scanned_as_text():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [{"function": {"arguments": '{"to": "a@b.com"}'}}],
        }
    ]
    (finding,) = EmailDetector().check_messages(messages).findings
    assert finding.path == "messages[0].tool_calls[0].function.arguments"


def test_secrets_are_found_in_messages_too():
    key = "ghp_" + "Ab1" * 12
    result = ApiKeyDetector().check_messages(
        [{"role": "user", "content": f"key {key}"}]
    )
    assert result.decision == "block"
    assert "ghp_" in result.findings[0].preview
    assert key not in str(result)


def test_printing_shows_the_path():
    shown = str(
        EmailDetector().check_messages([{"role": "user", "content": "a@b.com"}])
    )
    assert "in messages[0].content" in shown
