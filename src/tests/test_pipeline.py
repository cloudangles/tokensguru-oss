import pytest

from tokensguru import TokenCounter
from tokensguru.optimizers import (
    BulletDeduplicator,
    JsonMinifier,
    OptimizationResult,
    ParagraphDeduplicator,
    Pipeline,
    PipelineResult,
    WhitespaceCleaner,
)

TEXT = "Rules:\n- be  concise\n- be concise   \n\n\n\n- cite   sources\n"


def test_default_pipeline_runs_every_builtin_optimizer_in_order():
    pipeline = Pipeline()
    assert [type(o) for o in pipeline.optimizers] == [
        JsonMinifier,
        WhitespaceCleaner,
        ParagraphDeduplicator,
        BulletDeduplicator,
    ]


def test_order_matters_whitespace_first_lets_near_duplicates_match():
    result = Pipeline().optimize(TEXT)
    assert result.optimized_text == "Rules:\n- be concise\n\n- cite sources\n"
    only_dedupe = BulletDeduplicator().optimize(TEXT)
    assert "- be  concise\n" in only_dedupe.optimized_text


def test_each_step_gets_the_previous_steps_output():
    result = Pipeline(WhitespaceCleaner(), BulletDeduplicator()).optimize(TEXT)
    first, second = result.steps
    assert first.original_text == TEXT
    assert second.original_text == first.optimized_text
    assert result.optimized_text == second.optimized_text


def test_chosen_optimizers_and_order_are_respected():
    result = Pipeline(BulletDeduplicator()).optimize(TEXT)
    assert [s.optimizer_id for s in result.steps] == ["exact_bullet_item_deduplication"]


def test_combined_result_is_measured_from_start_to_finish():
    result = Pipeline().optimize(TEXT)
    assert isinstance(result, PipelineResult)
    assert isinstance(result, OptimizationResult)
    assert result.original_text == TEXT
    assert result.original_tokens == result.steps[0].original_tokens
    assert result.optimized_tokens == result.steps[-1].optimized_tokens
    assert result.saved_tokens == result.original_tokens - result.optimized_tokens
    assert result.saved_chars == len(TEXT) - len(result.optimized_text)
    assert result.changed is True
    assert result.optimizer_id == "pipeline"
    assert "Prose whitespace cleanup" in result.optimizer_name
    assert result.duration_ms == pytest.approx(
        sum(step.duration_ms for step in result.steps), abs=0.01
    )


def test_pipeline_saves_more_than_either_optimizer_alone():
    both = Pipeline().optimize(TEXT).saved_tokens
    assert both > WhitespaceCleaner().optimize(TEXT).saved_tokens
    assert both > BulletDeduplicator().optimize(TEXT).saved_tokens


def test_reason_lists_the_optimizers_that_changed_the_text():
    result = Pipeline().optimize(TEXT)
    assert result.reason.startswith("Applied: ")
    assert "Prose whitespace cleanup" in result.reason
    only_spaces = Pipeline().optimize("a   b\n")
    assert only_spaces.reason == "Applied: Prose whitespace cleanup"


def test_unchanged_text():
    result = Pipeline().optimize("clean text\n")
    assert result.changed is False
    assert result.reason == "No optimizer found a safe change."
    assert result.saved_tokens == 0


def test_context_is_passed_to_every_optimizer():
    seen = []

    class Spy(WhitespaceCleaner):
        def transform(self, text, context=None):
            seen.append(context)
            return super().transform(text, context)

    Pipeline(Spy(), Spy()).optimize("a", {"k": 1})
    assert seen == [{"k": 1}, {"k": 1}]


def test_to_dict_includes_every_step():
    data = Pipeline().optimize(TEXT).to_dict()
    assert data["optimizer_id"] == "pipeline"
    assert len(data["steps"]) == 4
    assert data["steps"][1]["optimizer_id"] == "prose_whitespace_cleanup"
    assert data["original_text"] == TEXT


def test_printing_shows_the_summary_and_every_step():
    shown = str(Pipeline().optimize(TEXT))
    assert "optimizer" in shown
    assert "steps" in shown
    assert "2. prose_whitespace_cleanup: changed" in shown
    assert "3. exact_paragraph_deduplication: unchanged" in shown
    assert "4. exact_bullet_item_deduplication: changed" in shown
    assert "tokens" in shown


def test_calling_the_pipeline_is_the_same_as_optimize():
    assert Pipeline()(TEXT).optimized_text == Pipeline().optimize(TEXT).optimized_text


def test_a_custom_counter_is_used_by_the_steps():
    result = Pipeline(WhitespaceCleaner(counter=TokenCounter(model="gpt-4"))).optimize(
        "a   b"
    )
    assert result.tokenizer == "gpt-4"


def test_tokenizer_failure_does_not_stop_the_pipeline():
    class Broken(TokenCounter):
        def count(self, text):
            raise OSError("offline")

    result = Pipeline(WhitespaceCleaner(counter=Broken())).optimize("a   b")
    assert result.optimized_text == "a b"
    assert result.original_tokens is None
    assert result.saved_tokens is None
    assert result.token_error == "OSError: offline"  # noqa: S105
    assert "tokens unavailable" in str(result)


def test_rejects_non_optimizers_and_non_text():
    with pytest.raises(TypeError, match="takes optimizers"):
        Pipeline("whitespace")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Pipeline().optimize(None)  # type: ignore[arg-type]


def test_passing_a_result_instead_of_text_gives_a_helpful_error():
    result = WhitespaceCleaner().optimize("a  b")
    with pytest.raises(TypeError, match=r"use its \.optimized_text"):
        BulletDeduplicator().optimize(result)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"use its \.optimized_text"):
        Pipeline().optimize(result)  # type: ignore[arg-type]


def test_empty_text():
    result = Pipeline().optimize("")
    assert result.optimized_text == ""
    assert result.changed is False
