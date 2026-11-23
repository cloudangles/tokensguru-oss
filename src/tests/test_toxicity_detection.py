import json
import random
import time

import pytest

from tokensguru.governance import ToxicityDetector

detector = ToxicityDetector()
ZWSP = chr(0x200B)


class FakeModel:
    name = "fake"

    def __init__(self, scores):
        self._scores = scores

    def scores(self, text):
        return self._scores


def types_of(text, **options):
    return [f.type for f in ToxicityDetector(**options).check(text).findings]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("You are an idiot", "insult"),
        ("you're such a worthless loser", "insult"),
        ("Shut up", "insult"),
        ("I will kill you", "threat"),
        ("I'm going to hurt your family", "threat"),
        ("You will regret this", "threat"),
        ("You should kill yourself", "self_harm"),
        ("go kill yourself", "self_harm"),
        ("all immigrants should die", "hate"),
        ("I hate all muslims", "hate"),
    ],
)
def test_toxic_language_is_found(text, expected):
    result = detector.check(text)
    assert result.decision == "flag"
    assert expected in [f.type for f in result.findings]


@pytest.mark.parametrize(
    "text",
    [
        "Have a nice day",
        "The class discussed the assassin and the scuttle of the ship.",
        "I will kill the process and restart the server",
        "Please shut the door",
        "Scunthorpe and Cockburn are places; a classic assessment",
        "You are an engineer",
        "",
    ],
)
def test_ordinary_text_passes(text):
    assert detector.check(text).decision == "pass"


def test_profanity_is_only_reported_at_high_sensitivity():
    assert types_of("What the fuck is this") == []
    assert types_of("What the fuck is this", sensitivity="high") == ["profanity"]
    assert types_of("this is bullshit", sensitivity="high") == ["profanity"]
    assert types_of("You are an idiot", sensitivity="low") == []
    assert types_of("I will kill you", sensitivity="low") == ["threat"]


def test_hiding_tricks_and_case_are_handled():
    assert types_of(f"YOU ARE AN ID{ZWSP}IOT") == ["insult"]
    wide = "".join(chr(ord(c) + 0xFEE0) for c in "fuck")
    assert types_of(f"what the {wide}", sensitivity="high") == ["profanity"]
    for disguised in ["fuuuck", "f.u.c.k", "f u c k", "FUCK", "fvck"]:
        found = types_of(f"oh {disguised} that", sensitivity="high")
        assert found in (["profanity"], []), disguised
    assert types_of("sh1t happens", sensitivity="high") == ["profanity"]
    assert types_of("you are an 1d1ot".replace("1d1ot", "idiot")) == ["insult"]


def test_harmless_words_that_contain_a_swear_are_not_reported():
    for text in ["I assume the class passed", "a classic assessment", "Scunthorpe"]:
        assert types_of(text, sensitivity="high") == []


def test_findings_point_at_the_original_text_and_do_not_store_it():
    text = "ok. You are an idiot. bye"
    result = detector.check(text)
    (finding,) = result.findings
    assert text[finding.start : finding.end].lower().startswith("you are")
    assert "idiot" not in json.dumps(result.to_dict()).lower()
    assert "idiot" not in str(result).lower()
    swear = ToxicityDetector(sensitivity="high").check("what the fuck")
    assert swear.findings[0].preview == "f***"


def test_overlapping_rules_keep_the_strongest():
    findings = (
        ToxicityDetector(sensitivity="high")
        .check("you should kill yourself you fucking idiot")
        .findings
    )
    spans = [(f.start, f.end) for f in findings]
    assert spans == sorted(spans)
    assert all(a.end <= b.start for a, b in zip(findings, findings[1:]))


def test_block_action():
    blocker = ToxicityDetector(action="block")
    assert blocker.check("I will kill you").decision == "block"


def test_model_backend_reports_labels_over_the_threshold():
    model = FakeModel({"toxic": 0.95, "insult": 0.85, "threat": 0.2, "non-toxic": 0.99})
    result = ToxicityDetector(backend=model).check("neutral text")
    assert [f.type for f in result.findings] == ["toxicity_model"]
    assert (
        ToxicityDetector(backend=model, threshold=0.97).check("neutral text").count == 0
    )


def test_rules_can_be_turned_off_when_a_model_is_used():
    detector = ToxicityDetector(use_rules=False, backend=FakeModel({"toxic": 0.1}))
    assert detector.check("you are an idiot").decision == "pass"


@pytest.mark.parametrize(
    "options",
    [{"threshold": 0}, {"threshold": 2}, {"action": "z"}, {"sensitivity": "max"}],
)
def test_invalid_options(options):
    with pytest.raises(ValueError):
        ToxicityDetector(**options)


def test_messages_are_checked_with_paths():
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "You are an idiot"},
    ]
    result = detector.check_messages(messages)
    assert [f.path for f in result.findings] == ["messages[1].content"]
    only_user = detector.check_messages(messages, roles=["assistant"])
    assert only_user.decision == "pass"


def test_hostile_input_is_fast_and_never_crashes():
    inputs = [
        "you " * 30000 + "are",
        "I " * 30000 + "will kill",
        " " * 100000 + "shut up",
        "f" * 100000,
    ]
    for text in inputs:
        started = time.perf_counter()
        detector.check(text)
        assert time.perf_counter() - started < 2


def test_random_text_never_crashes():
    rng = random.Random(9)  # noqa: S311
    alphabet = "you are idiot i will kill shut up fuck \n" + ZWSP
    for _ in range(300):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120)))
        for f in detector.check(text).findings:
            assert 0 <= f.start <= f.end <= len(text)


def test_result_has_overall_score():
    clean = ToxicityDetector().check("What a lovely day")
    threat = ToxicityDetector().check("I will kill you")
    assert clean.score == 0.0
    assert threat.score == max(f.confidence for f in threat.findings) > 0.9
    assert threat.to_dict()["score"] == threat.score
