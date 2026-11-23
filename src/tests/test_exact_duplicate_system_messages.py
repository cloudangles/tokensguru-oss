import copy
import random

import pytest

from tokensguru import TokenCounter
from tokensguru.optimizers import (
    MessageOptimizationResult,
    MessageOptimizer,
    OptimizationResult,
    SystemMessageDeduplicator,
)

dedupe = SystemMessageDeduplicator()


def system(text, **extra):
    return {"role": "system", "content": text, **extra}


def user(text):
    return {"role": "user", "content": text}


def assistant(text):
    return {"role": "assistant", "content": text}


def kept(messages):
    return dedupe.optimize(messages).optimized_messages


def test_removes_an_adjacent_identical_system_message_and_keeps_the_first():
    messages = [system("Be concise."), system("Be concise."), user("Hi")]
    assert kept(messages) == [system("Be concise."), user("Hi")]


def test_removes_a_run_of_identical_system_messages():
    messages = [system("A")] * 4 + [user("Hi")]
    assert kept(messages) == [system("A"), user("Hi")]


def test_different_system_messages_are_all_kept():
    messages = [system("A"), system("B"), system("A")]
    assert kept(messages) == messages


def test_identical_system_messages_separated_by_another_message_are_both_kept():
    for between in (user("x"), assistant("x"), {"role": "tool", "content": "x"}):
        messages = [system("A"), between, system("A")]
        assert kept(messages) == messages


def test_a_non_dict_item_between_them_separates_them():
    messages = [system("A"), None, system("A")]
    assert kept(messages) == messages
    messages = [system("A"), "text", 5, system("A")]
    assert kept(messages) == messages


def test_only_the_system_role_is_deduplicated():
    for role in ("user", "assistant", "tool", "developer", "System", "SYSTEM", ""):
        messages = [{"role": role, "content": "same"}] * 2
        assert kept(messages) == messages


def test_content_must_match_exactly():
    for other in ("be concise.", "Be concise. ", " Be concise.", "Be  concise."):
        messages = [system("Be concise."), system(other)]
        assert kept(messages) == messages


def test_extra_fields_must_match():
    same = [system("A", name="x"), system("A", name="x")]
    assert kept(same) == [system("A", name="x")]
    different = [system("A", name="x"), system("A", name="y")]
    assert kept(different) == different
    one_extra = [system("A"), system("A", name="x")]
    assert kept(one_extra) == one_extra


def test_field_order_does_not_matter():
    first = {"role": "system", "content": "A", "name": "n"}
    second = {"name": "n", "content": "A", "role": "system"}
    assert kept([first, second]) == [first]


def test_values_of_different_types_are_not_the_same():
    messages = [system("A", n=1), system("A", n=True)]
    assert kept(messages) == messages
    messages = [system("A", n=1), system("A", n=1.0)]
    assert kept(messages) == messages


def test_nested_extra_fields_are_compared_deeply():
    same = [system("A", meta={"k": [1, 2]}), system("A", meta={"k": [1, 2]})]
    assert len(kept(same)) == 1
    different = [system("A", meta={"k": [1, 2]}), system("A", meta={"k": [2, 1]})]
    assert len(kept(different)) == 2


def test_system_messages_without_plain_text_content_are_kept():
    parts = [{"type": "text", "text": "A"}]
    for content in (parts, None, 5, {"a": 1}):
        messages = [
            {"role": "system", "content": content},
            {"role": "system", "content": content},
        ]
        assert kept(messages) == messages


def test_messages_missing_role_or_content_are_kept():
    for message in ({}, {"role": "system"}, {"content": "A"}):
        assert kept([message, message]) == [message, message]


def test_values_that_cannot_be_serialized_are_kept():
    odd = system("A", obj=object())
    assert kept([odd, odd]) == [odd, odd]
    loop = system("A")
    loop["self"] = loop
    assert kept([loop, loop]) == [loop, loop]


def test_unicode_and_emoji_content():
    text = "Résumé 日本語 \U0001f600"
    assert kept([system(text), system(text)]) == [system(text)]


def test_system_message_at_any_position():
    messages = [user("a"), system("S"), system("S"), assistant("b"), system("S")]
    assert kept(messages) == [user("a"), system("S"), assistant("b"), system("S")]


def test_removed_indexes_and_count():
    result = dedupe.optimize([system("A"), system("A"), user("x"), system("A")])
    assert result.removed_indexes == (1,)
    assert result.removed_count == 1
    result = dedupe.optimize([system("A")] * 3)
    assert result.removed_indexes == (1, 2)
    assert result.removed_count == 2


def test_nothing_to_remove():
    messages = [system("A"), user("x")]
    result = dedupe.optimize(messages)
    assert result.removed_count == 0
    assert result.changed is False
    assert result.optimized_messages == messages
    assert result.reason == SystemMessageDeduplicator.skipped_reason


def test_empty_and_single_message_lists():
    assert kept([]) == []
    assert kept([system("A")]) == [system("A")]


def test_the_input_list_and_messages_are_never_changed():
    messages = [system("A"), system("A"), user("x")]
    snapshot = copy.deepcopy(messages)
    result = dedupe.optimize(messages)
    assert messages == snapshot
    assert result.original_messages == snapshot
    assert result.optimized_messages is not messages


def test_the_result_holds_the_same_message_objects():
    first = system("A")
    result = dedupe.optimize([first, system("A")])
    assert result.optimized_messages[0] is first


def test_changing_the_result_list_does_not_change_the_original_list():
    messages = [system("A"), user("x")]
    result = dedupe.optimize(messages)
    result.optimized_messages.append(user("y"))
    assert len(messages) == 2
    assert len(result.original_messages) == 2


def test_the_same_object_listed_twice_is_removed_by_position():
    message = system("A")
    result = dedupe.optimize([message, message])
    assert result.removed_indexes == (1,)
    assert result.optimized_messages == [message]


def test_tuples_are_accepted_and_a_list_is_returned():
    result = dedupe.optimize((system("A"), system("A")))
    assert result.optimized_messages == [system("A")]


@pytest.mark.parametrize("value", [None, "text", 5, {"role": "system"}, b"x"])
def test_rejects_input_that_is_not_a_list(value):
    with pytest.raises(TypeError, match="messages must be a list"):
        dedupe.optimize(value)


def test_a_generator_is_rejected():
    with pytest.raises(TypeError):
        dedupe.optimize(system(x) for x in "ab")


def test_accepts_context_and_is_callable():
    messages = [system("A"), system("A")]
    assert dedupe.optimize(messages, {"x": 1}).removed_count == 1
    assert dedupe(messages).removed_count == 1


def test_tokens_are_counted_on_the_whole_message_list():
    result = dedupe.optimize([system("Be concise."), system("Be concise.")])
    assert isinstance(result, MessageOptimizationResult)
    assert isinstance(result, OptimizationResult)
    assert isinstance(dedupe, MessageOptimizer)
    assert result.original_tokens > result.optimized_tokens
    assert result.saved_tokens == result.original_tokens - result.optimized_tokens
    assert result.saved_chars == len(result.original_text) - len(result.optimized_text)
    assert result.original_text.startswith('[{"role":"system"')


def test_result_details():
    result = dedupe.optimize([system("A"), system("A")])
    assert result.optimizer_id == "exact_duplicate_system_messages"
    assert result.optimizer_name == "Exact duplicate system messages"
    assert result.reason == SystemMessageDeduplicator.applied_reason
    assert result.changed is True
    assert result.tokenizer == "o200k_base"
    assert result.token_error is None
    assert len(result.id) == 32


def test_to_dict_has_the_messages_too():
    data = dedupe.optimize([system("A"), system("A")]).to_dict()
    assert data["optimizer_id"] == "exact_duplicate_system_messages"
    assert data["removed_count"] == 1
    assert data["removed_indexes"] == [1]
    assert data["original_messages"] == [system("A"), system("A")]
    assert data["optimized_messages"] == [system("A")]
    assert "saved_tokens" in data


def test_printing_shows_what_was_removed():
    shown = str(dedupe.optimize([user("x"), system("A"), system("A")]))
    assert "exact_duplicate_system_messages" in shown
    assert "messages removed : 1 of 3 (positions [2])" in shown
    assert "tokens" in shown


def test_printing_when_nothing_is_removed():
    assert "messages removed : 0 of 1" in str(dedupe.optimize([system("A")]))


def test_a_custom_counter_and_a_failing_counter():
    result = SystemMessageDeduplicator(TokenCounter(model="gpt-4")).optimize([])
    assert result.tokenizer == "gpt-4"

    class Broken(TokenCounter):
        def count(self, text):
            raise OSError("offline")

    result = SystemMessageDeduplicator(Broken()).optimize([system("A"), system("A")])
    assert result.removed_count == 1
    assert result.original_tokens is None
    assert result.saved_tokens is None
    assert result.token_error == "OSError: offline"  # noqa: S105


def test_large_message_lists_are_handled():
    messages = [system("same")] * 50000 + [user("end")]
    result = dedupe.optimize(messages)
    assert result.optimized_messages == [system("same"), user("end")]
    assert result.removed_count == 49999


def test_is_idempotent():
    messages = [system("A"), system("A"), user("x"), system("A"), system("A")]
    once = dedupe.optimize(messages).optimized_messages
    assert dedupe.optimize(once).optimized_messages == once


def test_message_optimizer_cannot_be_used_directly():
    with pytest.raises(TypeError):
        MessageOptimizer()


POOL = [
    system("A"),
    system("B"),
    system("A", name="n"),
    user("x"),
    assistant("y"),
    {"role": "tool", "content": "t"},
    {"role": "system", "content": [{"type": "text", "text": "A"}]},
    None,
    "text",
    {},
]


def test_fuzz_only_adjacent_identical_system_messages_are_removed():
    rng = random.Random(1357)  # noqa: S311
    for _ in range(6000):
        messages = [rng.choice(POOL) for _ in range(rng.randint(0, 12))]
        result = dedupe.optimize(messages)
        out = result.optimized_messages
        assert result.removed_count == len(messages) - len(out)
        kept_indexes = [
            i for i in range(len(messages)) if i not in result.removed_indexes
        ]
        assert out == [messages[i] for i in kept_indexes]
        for index in result.removed_indexes:
            assert index > 0
            assert messages[index] == messages[index - 1] or any(
                messages[index] == messages[j] for j in kept_indexes if j < index
            )
            assert messages[index]["role"] == "system"
        assert dedupe.optimize(out).optimized_messages == out
        assert result.saved_chars >= 0
        for left, right in zip(out, out[1:]):
            both_system_text = all(
                isinstance(m, dict)
                and m.get("role") == "system"
                and isinstance(m.get("content"), str)
                for m in (left, right)
            )
            assert not (both_system_text and left == right)
