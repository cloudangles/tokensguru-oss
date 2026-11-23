import sys
import types

import pytest

from tokensguru import TokenCounter
from tokensguru import tokens as tokens_module
from tokensguru.optimizers import (
    BulletDeduplicator,
    OptimizationResult,
    Optimizer,
    WhitespaceCleaner,
)


class FakeEncoding:
    def encode_ordinary(self, text):
        return text.split()


def make_fake_tiktoken(calls):
    module = types.ModuleType("tiktoken")

    def get_encoding(name):
        calls.append(("encoding", name))
        if name == "nope":
            raise ValueError(name)
        return FakeEncoding()

    def encoding_for_model(name):
        calls.append(("model", name))
        if name == "nope":
            raise KeyError(name)
        return FakeEncoding()

    module.get_encoding = get_encoding
    module.encoding_for_model = encoding_for_model
    return module


@pytest.fixture
def fake_tiktoken(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "tiktoken", make_fake_tiktoken(calls))
    tokens_module._load_encoder.cache_clear()
    tokens_module.default_counter.cache_clear()
    yield calls
    tokens_module._load_encoder.cache_clear()
    tokens_module.default_counter.cache_clear()


def test_counts_tokens(fake_tiktoken):
    assert TokenCounter().count("one two three") == 3


def test_empty_text_is_zero_without_loading_a_tokenizer(monkeypatch):
    monkeypatch.setitem(sys.modules, "tiktoken", None)
    assert TokenCounter().count("") == 0


def test_default_encoding_and_custom_encoding(fake_tiktoken):
    TokenCounter().count("a")
    TokenCounter(encoding="cl100k_base").count("a")
    assert fake_tiktoken == [("encoding", "o200k_base"), ("encoding", "cl100k_base")]


def test_model_name_picks_the_tokenizer(fake_tiktoken):
    assert TokenCounter(model="gpt-4").count("a b") == 2
    assert fake_tiktoken == [("model", "gpt-4")]


def test_tokenizer_is_loaded_once(fake_tiktoken):
    counter = TokenCounter()
    counter.count("a")
    counter.count("b")
    assert len(fake_tiktoken) == 1


def test_unknown_encoding_and_model_give_clear_errors(fake_tiktoken):
    with pytest.raises(ValueError, match="Unknown encoding"):
        TokenCounter(encoding="nope").count("a")
    with pytest.raises(ValueError, match="Unknown model"):
        TokenCounter(model="nope").count("a")


@pytest.mark.parametrize("value", [None, 5, b"a", ["a"]])
def test_rejects_non_string_input(value):
    with pytest.raises(TypeError):
        TokenCounter().count(value)


def test_counter_name_is_the_model_or_the_encoding():
    assert TokenCounter().name == "o200k_base"
    assert TokenCounter(encoding="cl100k_base").name == "cl100k_base"
    assert TokenCounter(model="gpt-4").name == "gpt-4"


def test_real_tiktoken_counts_known_text():
    pytest.importorskip("tiktoken")
    tokens_module._load_encoder.cache_clear()
    counter = TokenCounter()
    try:
        assert counter.count("hello world") == 2
    except Exception as error:
        pytest.skip(f"tokenizer could not be loaded (offline?): {error}")
    assert counter.count("<|endoftext|>") > 1
    assert counter.count("a" * 5) < counter.count("a b c d e f")


def test_optimize_returns_a_full_result_without_importing_a_counter():
    text = "- a b\n- a b\n- c\n"
    result = BulletDeduplicator().optimize(text)
    assert isinstance(result, OptimizationResult)
    assert result.optimizer_id == "exact_bullet_item_deduplication"
    assert result.optimizer_name == "Exact repeated bullet cleanup"
    assert result.original_text == text
    assert result.optimized_text == "- a b\n- c\n"
    assert result.changed is True
    assert result.reason == BulletDeduplicator.applied_reason
    assert result.tokenizer == "o200k_base"
    assert (result.original_tokens, result.optimized_tokens) == (8, 5)
    assert result.saved_tokens == 3
    assert result.saved_tokens_percent == 37.5
    assert (result.original_chars, result.optimized_chars) == (16, 10)
    assert result.saved_chars == 6
    assert result.saved_chars_percent == 37.5
    assert result.duration_ms >= 0
    assert result.token_error is None


def test_unchanged_text_uses_the_skipped_reason():
    result = WhitespaceCleaner().optimize("clean text")
    assert result.changed is False
    assert result.reason == WhitespaceCleaner.skipped_reason
    assert result.saved_tokens == 0
    assert result.saved_tokens_percent == 0.0
    assert result.saved_chars == 0


def test_every_run_gets_its_own_id_and_timestamp():
    first = WhitespaceCleaner().optimize("a  b")
    second = WhitespaceCleaner().optimize("a  b")
    assert first.id != second.id
    assert len(first.id) == 32
    assert first.created_at.endswith("+00:00")


def test_to_dict_has_every_detail():
    data = BulletDeduplicator().optimize("- a\n- a\n").to_dict()
    assert set(data) == {
        "id", "created_at", "optimizer_id", "optimizer_name", "changed", "reason",
        "tokenizer", "original_text", "optimized_text", "original_tokens",
        "optimized_tokens", "saved_tokens", "saved_tokens_percent",
        "original_chars", "optimized_chars", "saved_chars", "saved_chars_percent",
        "duration_ms", "token_error",
    }  # fmt: skip
    assert data["saved_tokens"] == 2
    assert data["original_text"] == "- a\n- a\n"


def test_printing_a_result_shows_the_details():
    shown = str(BulletDeduplicator().optimize("- a\n- a\n"))
    for label in ("id", "optimizer", "tokens", "characters", "reason", "duration",
                  "original text", "optimized text", "changed"):  # fmt: skip
        assert label in shown
    assert "exact_bullet_item_deduplication" in shown
    assert "4 -> 2, saved 2 (50.0%)" in shown


def test_long_text_is_shortened_in_the_printed_summary():
    shown = str(WhitespaceCleaner().optimize("word  " * 200))
    assert "..." in shown
    assert len(shown) < 1500


def test_optimizer_can_use_a_specific_tokenizer(fake_tiktoken):
    counter = TokenCounter(model="gpt-4")
    result = WhitespaceCleaner(counter=counter).optimize("a   b  ")
    assert result.tokenizer == "gpt-4"
    assert fake_tiktoken == [("model", "gpt-4")]
    assert BulletDeduplicator(counter).optimize("- a\n- a\n").tokenizer == "gpt-4"


def test_optimization_still_works_when_the_tokenizer_fails():
    class Broken(TokenCounter):
        def count(self, text):
            raise OSError("no internet")

    result = BulletDeduplicator(Broken()).optimize("- a\n- a\n")
    assert result.optimized_text == "- a\n"
    assert result.original_tokens is None
    assert result.optimized_tokens is None
    assert result.saved_tokens is None
    assert result.saved_tokens_percent is None
    assert result.token_error == "OSError: no internet"  # noqa: S105
    assert "unavailable (OSError: no internet)" in str(result)


def test_calling_the_object_is_the_same_as_optimize():
    result = WhitespaceCleaner()("a   b")
    assert isinstance(result, OptimizationResult)
    assert result.optimized_text == "a b"


def test_optimize_rejects_non_string_input():
    with pytest.raises(TypeError):
        BulletDeduplicator().optimize(None)


def test_both_optimizers_share_the_base_class():
    assert isinstance(BulletDeduplicator(), Optimizer)
    assert isinstance(WhitespaceCleaner(), Optimizer)
    with pytest.raises(TypeError):
        Optimizer()
