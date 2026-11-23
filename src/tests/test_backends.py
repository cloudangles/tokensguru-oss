import pytest

from tokensguru.governance import HuggingFaceClassifier, backends
from tokensguru.governance.backends import ML_HINT, chunk_text


def fake(output, calls=None):
    def classify(text, **options):
        if calls is not None:
            calls.append((text, options))
        return output

    return classify


def test_scores_are_lowercased_and_the_best_per_label_wins():
    output = [[{"label": "Toxic", "score": 0.4}, {"label": "THREAT", "score": 0.1}]]
    classifier = HuggingFaceClassifier("m", pipeline=fake(output))
    assert classifier.scores("hello") == {"toxic": 0.4, "threat": 0.1}
    assert classifier.name == "m"


def test_a_flat_list_and_a_single_dict_are_accepted():
    flat = [{"label": "a", "score": 0.2}]
    assert HuggingFaceClassifier("m", pipeline=fake(flat)).scores("x") == {"a": 0.2}
    single = {"label": "b", "score": 0.9}
    assert HuggingFaceClassifier("m", pipeline=fake(single)).scores("x") == {"b": 0.9}


def test_long_text_is_split_and_the_highest_score_across_pieces_is_kept():
    scores = iter([0.1, 0.8, 0.3])

    def classify(text, **options):
        return [{"label": "toxic", "score": next(scores)}]

    classifier = HuggingFaceClassifier("m", max_chars=10, overlap=2, pipeline=classify)
    assert classifier.scores("x" * 24) == {"toxic": 0.8}


def test_chunking_covers_the_whole_text_with_overlap():
    text = "abcdefghijklmnopqrstuvwxyz"
    pieces = chunk_text(text, 10, 2)
    assert pieces[0] == text[:10]
    assert pieces[1] == text[8:18]
    assert pieces[-1].endswith("z")
    assert chunk_text("short", 10, 2) == ["short"]


def test_options_are_passed_to_the_model():
    calls = []
    classifier = HuggingFaceClassifier(
        "m", function_to_apply="sigmoid", pipeline=fake([], calls)
    )
    classifier.scores("text")
    assert calls == [
        (
            "text",
            {
                "top_k": None,
                "truncation": True,
                "max_length": 256,
                "function_to_apply": "sigmoid",
            },
        )
    ]
    plain = []
    HuggingFaceClassifier("m", pipeline=fake([], plain)).scores("t")
    assert "function_to_apply" not in plain[0][1]


@pytest.mark.parametrize("size, overlap", [(0, 0), (10, 10), (10, -1), (5, 9)])
def test_invalid_chunk_settings(size, overlap):
    with pytest.raises(ValueError, match="max_chars"):
        HuggingFaceClassifier("m", max_chars=size, overlap=overlap)


def test_a_missing_transformers_package_gives_install_help(monkeypatch):
    def refuse(name):
        raise ImportError(name)

    monkeypatch.setattr(backends, "import_module", refuse)
    with pytest.raises(ImportError, match="pip install") as caught:
        HuggingFaceClassifier("m").scores("text")
    assert str(caught.value) == ML_HINT
