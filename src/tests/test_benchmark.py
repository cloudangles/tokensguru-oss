import pytest

from tokensguru import TokenCounter
from tokensguru.benchmark import BENCHMARK_IDS, run_benchmark, summarize
from tokensguru.benchmark.samples import MESSAGE_SAMPLES, TEXT_SAMPLES
from tokensguru.optimizers.registry import MESSAGE_OPTIMIZERS, TEXT_OPTIMIZERS

pytestmark = pytest.mark.usefixtures("whitespace_tokens")


def test_every_registered_optimizer_and_the_pipeline_has_samples():
    registered = {o.id for o in TEXT_OPTIMIZERS} | {o.id for o in MESSAGE_OPTIMIZERS}
    assert set(BENCHMARK_IDS) == registered | {"pipeline"}


@pytest.mark.parametrize("optimizer_id", BENCHMARK_IDS)
def test_each_sample_set_is_honest_and_useful(optimizer_id):
    report = run_benchmark(optimizer_id)
    summary = report["summary"]
    assert report["error"] is None
    assert summary["samples"] >= 5
    assert summary["changed"] >= 1
    assert summary["changed"] < summary["samples"]
    assert summary["min_percent"] == 0.0
    assert 0 < summary["average_percent"] < summary["max_percent"]
    assert summary["max_percent"] < 100
    assert report["tokenizer"] == "o200k_base"


@pytest.mark.parametrize("optimizer_id", BENCHMARK_IDS)
def test_samples_never_get_longer_and_numbers_add_up(optimizer_id):
    report = run_benchmark(optimizer_id)
    for sample in report["samples"]:
        assert sample["saved_tokens"] >= 0
        assert sample["optimized_tokens"] <= sample["original_tokens"]
        assert sample["saved_tokens"] == (
            sample["original_tokens"] - sample["optimized_tokens"]
        )
        assert 0 <= sample["saved_percent"] <= 100
        assert sample["name"]
    names = [sample["name"] for sample in report["samples"]]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("optimizer_id", BENCHMARK_IDS)
def test_results_are_repeatable(optimizer_id):
    assert run_benchmark(optimizer_id) == run_benchmark(optimizer_id)


def test_sample_names_match_the_sample_data():
    for optimizer_id, data in {**TEXT_SAMPLES, **MESSAGE_SAMPLES}.items():
        report = run_benchmark(optimizer_id)
        assert [s["name"] for s in report["samples"]] == list(data)


def _sample(original, optimized):
    saved = original - optimized
    return {
        "original_tokens": original,
        "optimized_tokens": optimized,
        "saved_tokens": saved,
        "saved_percent": round(100 * saved / original, 2),
    }


def test_summarize_math():
    samples = [
        _sample(100, 50),
        _sample(100, 100),
        _sample(20, 10),
    ]
    summary = summarize(samples)
    assert summary == {
        "samples": 3,
        "changed": 2,
        "average_percent": 33.33,
        "min_percent": 0.0,
        "max_percent": 50.0,
        "total_original_tokens": 220,
        "total_optimized_tokens": 160,
        "overall_percent": 27.27,
    }


def test_summarize_of_nothing():
    summary = summarize([])
    assert summary["samples"] == 0
    assert summary["average_percent"] == 0.0
    assert summary["overall_percent"] == 0.0


def test_unknown_optimizer():
    with pytest.raises(KeyError):
        run_benchmark("nope")


def test_a_tokenizer_failure_is_reported_not_raised():
    class Broken(TokenCounter):
        def count(self, text):
            raise OSError("no internet")

    report = run_benchmark("prose_whitespace_cleanup", Broken())
    assert report["error"] == "OSError: no internet"
    assert report["summary"] is None
    assert report["samples"] == []


def test_a_custom_tokenizer_is_named_in_the_report():
    report = run_benchmark("prose_whitespace_cleanup", TokenCounter(model="gpt-4"))
    assert report["tokenizer"] == "gpt-4"
