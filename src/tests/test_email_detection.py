import json
import random
import string
import time

import pytest

from tokensguru.governance import EmailDetector, Finding, Guardrail, GuardrailResult

detector = EmailDetector()

ZWSP, ZWNJ, ZWJ = chr(0x200B), chr(0x200C), chr(0x200D)
WORD_JOINER, BOM, SOFT_HYPHEN = chr(0x2060), chr(0xFEFF), chr(0x00AD)
SMALL_AT, IDEOGRAPHIC_STOP = chr(0xFE6B), chr(0x3002)


def wide(text):
    return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in text)


def found(text, **options):
    result = EmailDetector(**options).check(text)
    return [text[f.start : f.end] for f in result.findings]


@pytest.mark.parametrize(
    "address",
    [
        "jane@example.com",
        "jane.doe@example.com",
        "jane+news@example.com",
        "JANE@EXAMPLE.COM",
        "j@example.co.uk",
        "first_last@sub.domain.example.org",
        "a1.b2-c3@x-y.example.io",
        "user%tag@example.net",
        "o'brien@example.ie",
        "!$%'*+^_`{|}~-@example.com",
        "x@a-b.com",
        "x@123.example.com",
        "mixed.Case+tag@Sub.Example.COM",
        "josé@exemple.fr",
        "用户@例子.广告",
        "user@xn--bcher-kva.example",
        "user@example.xn--p1ai",
    ],
)
def test_finds_valid_addresses(address):
    assert found(f"Contact {address} today.") == [address]
    assert found(address) == [address]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<jane@example.com>", ["jane@example.com"]),
        ("(jane@example.com)", ["jane@example.com"]),
        ('"jane@example.com"', ["jane@example.com"]),
        ("jane@example.com.", ["jane@example.com"]),
        ("jane@example.com, bob@example.org;", ["jane@example.com", "bob@example.org"]),
        ("mailto:jane@example.com", ["jane@example.com"]),
        ("email:jane@example.com", ["jane@example.com"]),
        ("a@b.com\nc@d.com", ["a@b.com", "c@d.com"]),
        ("[jane@example.com]", ["jane@example.com"]),
        ("jane@example.com?subject=hi", ["jane@example.com"]),
        ("see jane@example.com/path", ["jane@example.com"]),
        (".jane@example.com", ["jane@example.com"]),
        ("jane@example.com...", ["jane@example.com"]),
    ],
)
def test_finds_addresses_in_real_text(text, expected):
    assert found(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "no email here",
        "@handle",
        "@",
        "@@@@",
        "jane@",
        "@example.com",
        "jane@example",
        "jane@localhost",
        "jane@@example.com",
        "jane@example..com",
        "jane@-example.com",
        "jane@example-.com",
        "jane@.example.com",
        "jane@example.c",
        "jane@example.123",
        "jane@192.168.0.1",
        "a..b@example.com",
        "jane.@example.com",
        "jane@exa mple.com",
        "jane @example.com",
        "a@b@c",
        "price 5@10 each",
        "logo@2x.png",
        "icon@3x.jpg",
        "style@2x.css",
        "bundle@1.js",
        "git@github.com:user/repo.git",
        "git@gitlab.com:/group/repo",
        "https://user:secret@host.com/path",
        "ftp://admin:hunter2@files.example.com",
        "x" * 65 + "@example.com",
        "jane@" + "a" * 64 + ".com",
        "jane@" + ".".join(["a" * 60] * 5) + ".com",
    ],
)
def test_ignores_things_that_only_look_like_emails(text):
    assert found(text) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("mailto:a@b.com?cc=jane@example.com", ["a@b.com", "jane@example.com"]),
        ("//jane@example.com", ["jane@example.com"]),
        ("?to=jane@example.com&x=1", ["jane@example.com"]),
        ("#jane@example.com", ["jane@example.com"]),
        ("see=/jane@example.com", ["jane@example.com"]),
        ("a/b@example.com", ["b@example.com"]),
    ],
)
def test_url_punctuation_marks_where_an_address_starts(text, expected):
    assert found(text) == expected


def test_a_login_in_a_url_without_a_password_is_still_an_email():
    assert found("https://jane@example.com/path") == ["jane@example.com"]


def test_the_longest_valid_local_part_and_label_are_accepted():
    local = "a" * 64
    label = "b" * 63
    assert found(f"{local}@{label}.com") == [f"{local}@{label}.com"]


def test_an_email_that_looks_like_a_url_login_with_a_space_is_found():
    assert found("see https://x.com then bob:bob@example.com") == ["bob@example.com"]


def test_two_at_signs_do_not_create_overlapping_findings():
    assert found("a@b.com@c.com") == ["a@b.com"]


def test_offsets_point_at_the_exact_address():
    text = "x  jane@example.com  y"
    (finding,) = detector.check(text).findings
    assert (finding.start, finding.end) == (3, 19)
    assert text[finding.start : finding.end] == "jane@example.com"


def test_findings_are_in_order():
    text = "z@z.org a@a.org m@m.org"
    starts = [f.start for f in detector.check(text).findings]
    assert starts == sorted(starts)
    assert len(starts) == 3


@pytest.mark.parametrize(
    "text",
    [
        wide("jane@example.com"),
        "jane" + SMALL_AT + "example.com",
        "jane@example" + IDEOGRAPHIC_STOP + "com",
        f"ja{ZWSP}ne@exam{ZWSP}ple.com",
        f"j{ZWSP}a{ZWNJ}n{ZWJ}e{WORD_JOINER}@{BOM}example.com",
        f"ja{SOFT_HYPHEN}ne@example.com",
    ],
)
def test_finds_disguised_addresses_and_maps_back_to_the_original(text):
    (finding,) = detector.check(text).findings
    assert (finding.start, finding.end) == (0, len(text))


def test_invisible_characters_around_an_address_are_not_part_of_it():
    text = f"{ZWSP}{ZWSP}jane@example.com{ZWSP}"
    (finding,) = detector.check(text).findings
    assert text[finding.start : finding.end] == "jane@example.com"


def test_obfuscated_forms_are_found_with_lower_confidence():
    for text in (
        "jane[at]example[dot]com",
        "jane (at) example (dot) com",
        "jane{at}example{dot}co{dot}uk",
        "jane[ at ]example[ dot ]com",
        "JANE[AT]EXAMPLE[DOT]COM",
        "jane@example[dot]com",
        "jane[at]example.com",
    ):
        (finding,) = detector.check(f"mail {text} now").findings
        assert finding.confidence == 0.8, text
        assert finding.preview.lower().startswith("j***@"), text


def test_obfuscated_detection_can_be_turned_off():
    off = EmailDetector(detect_obfuscated=False)
    assert off.check("jane[at]example[dot]com").findings == ()
    assert found("jane@example.com", detect_obfuscated=False) == ["jane@example.com"]


def test_plain_words_called_at_and_dot_are_not_treated_as_a_disguise():
    assert found("jane at example dot com") == []
    assert found("meet at 5 dot com") == []


def test_normal_addresses_have_high_confidence():
    (finding,) = detector.check("jane@example.com").findings
    assert finding.confidence == 0.95
    assert (finding.type, finding.category) == ("email", "pii")


def test_the_preview_hides_the_local_part_and_keeps_the_domain():
    (finding,) = detector.check("jane.doe@example.com").findings
    assert finding.preview == "j***@example.com"


def test_allowed_domains_are_ignored_including_subdomains():
    options = {"allowed_domains": ["Example.com", "@corp.io", " .acme.org "]}
    assert found("a@example.com b@mail.example.com c@other.com", **options) == [
        "c@other.com"
    ]
    assert found("a@corp.io b@x.corp.io c@notcorp.io", **options) == ["c@notcorp.io"]
    assert found("a@acme.org", **options) == []
    assert found("a@badexample.com", allowed_domains=["example.com"]) == [
        "a@badexample.com"
    ]


def test_blank_allowed_domains_are_ignored():
    assert found("a@example.com", allowed_domains=["", "  "]) == ["a@example.com"]


def test_default_action_is_flag_and_block_can_be_chosen():
    assert detector.check("a@example.com").decision == "flag"
    assert EmailDetector(action="block").check("a@example.com").decision == "block"
    assert EmailDetector(action="block").check("nothing").decision == "pass"


@pytest.mark.parametrize("action", ["allow", "", "BLOCK", "redact", None.__class__])
def test_invalid_actions_are_rejected(action):
    with pytest.raises(ValueError, match="action"):
        EmailDetector(action=action)


def test_result_details():
    result = detector.check("write to a@example.com or b@example.org")
    assert isinstance(result, GuardrailResult)
    assert isinstance(detector, Guardrail)
    assert result.guardrail_id == "email_detection"
    assert result.guardrail_name == "Email detection"
    assert result.detected is True
    assert result.count == 2
    assert result.types == {"email": 2}
    assert result.reason == "Found 2 email addresses"
    assert result.input_length == len("write to a@example.com or b@example.org")
    assert result.duration_ms >= 0
    assert len(result.id) == 32
    assert result.created_at.endswith("+00:00")
    assert all(isinstance(f, Finding) for f in result.findings)


def test_reasons():
    assert detector.check("a@example.com").reason == "Found 1 email address"
    assert detector.check("nothing here").reason == "No email address found"
    clean = detector.check("nothing here")
    assert (clean.decision, clean.detected, clean.count, clean.types) == (
        "pass",
        False,
        0,
        {},
    )


def test_the_address_itself_is_never_stored_anywhere_in_the_result():
    secret_local = "very.private.person"  # noqa: S105
    text = f"mail {secret_local}@example.com please"
    result = detector.check(text)
    assert secret_local not in str(result)
    assert secret_local not in json.dumps(result.to_dict())
    assert secret_local not in repr(result)
    assert text not in json.dumps(result.to_dict())


def test_to_dict_is_json_serializable_and_complete():
    data = detector.check("a@example.com").to_dict()
    json.dumps(data)
    assert set(data) == {
        "id", "created_at", "guardrail_id", "guardrail_name", "decision", "detected",
        "reason", "count", "score", "types", "findings", "input_length", "duration_ms",
    }  # fmt: skip
    assert data["findings"][0]["preview"] == "a***@example.com"


def test_printing_a_result_lists_each_finding():
    shown = str(detector.check("x a@example.com"))
    assert "email_detection (Email detection)" in shown
    assert "decision     : flag" in shown
    assert "email at 2-15" in shown


def test_calling_the_object_is_the_same_as_check():
    assert detector("a@example.com").count == 1
    assert detector("a@example.com", {"anything": 1}).count == 1


@pytest.mark.parametrize("value", [None, 5, b"a@b.com", ["a@b.com"]])
def test_rejects_non_string_input(value):
    with pytest.raises(TypeError):
        detector.check(value)


def test_unicode_and_emoji_text_around_addresses():
    text = "\U0001f600 jane@example.com 你好 \U0001f680"
    assert found(text) == ["jane@example.com"]


def test_many_addresses_are_all_found():
    text = " ".join(f"user{i}@example.com" for i in range(5000))
    assert len(found(text)) == 5000


@pytest.mark.parametrize(
    "hostile",
    [
        "a" * 200_000 + "@",
        "@" * 200_000,
        "@a" * 100_000,
        "a@" * 100_000,
        ("a." * 100_000) + "@x",
        "@" + ("a." * 100_000),
        "a@" + ("b." * 100_000),
        ("a@b." * 50_000),
        "[at]" * 50_000,
        "a[at]" * 50_000,
        "x[at]" + "y[dot]" * 50_000,
        "x" * 200_000,
        ZWSP * 200_000,
        wide("@") * 100_000,
        f"a{ZWSP}" * 100_000 + "@example.com",
        "-" * 200_000 + "@" + "-" * 200_000,
        ("a" * 64 + "@") * 20_000,
    ],
)
def test_hostile_inputs_are_handled_quickly(hostile):
    started = time.perf_counter()
    detector.check(hostile)
    assert time.perf_counter() - started < 3


def test_a_huge_document_is_handled():
    text = "Lorem ipsum dolor sit amet, contact ops@example.com for help. " * 20_000
    started = time.perf_counter()
    result = detector.check(text)
    assert result.count == 20_000
    assert time.perf_counter() - started < 5


def test_is_idempotent_and_does_not_change_the_input():
    text = "a@example.com b[at]example[dot]org"
    first = detector.check(text)
    second = detector.check(text)
    assert [f.to_dict() for f in first.findings] == [
        f.to_dict() for f in second.findings
    ]
    assert text == "a@example.com b[at]example[dot]org"


ALPHABET = [
    *string.ascii_letters,
    *string.digits,
    *"@.-_+ []()\n",
    ZWSP,
    wide("@"),
    chr(0xE9),
    "[at]",
    "[dot]",
    "(at)",
    "example.com",
    "@x.org",
    "..",
    IDEOGRAPHIC_STOP,
]


def test_fuzz_findings_are_always_valid():
    rng = random.Random(8675309)  # noqa: S311
    for _ in range(4000):
        text = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 60)))
        result = detector.check(text)
        last_end = 0
        for finding in result.findings:
            assert 0 <= finding.start < finding.end <= len(text), repr(text)
            assert finding.start >= last_end, repr(text)
            last_end = finding.end
            chunk = text[finding.start : finding.end]
            assert chunk.strip(ZWSP) == chunk, repr(text)
            assert 0 < finding.confidence <= 1
            assert "@" in finding.preview
        assert detector.check(text).count == result.count


def random_address(rng):
    local_chars = string.ascii_lowercase + string.digits + "._+-"
    local = "".join(rng.choice(local_chars) for _ in range(rng.randint(1, 20)))
    local = local.strip(".-") or "a"
    domain = "".join(
        rng.choice(string.ascii_lowercase) for _ in range(rng.randint(1, 12))
    )
    return f"{local}@{domain}.com"


def test_fuzz_detected_addresses_survive_surrounding_noise():
    rng = random.Random(24601)  # noqa: S311
    noise = string.ascii_letters + string.digits + " .,;:!?()[]<>\n\t" + chr(0xE9)
    for _ in range(1500):
        address = random_address(rng)
        if ".." in address:
            continue
        left = "".join(rng.choice(noise) for _ in range(rng.randint(0, 12))) + " "
        right = " " + "".join(rng.choice(noise) for _ in range(rng.randint(0, 12)))
        assert address in found(left + address + right), repr(left + address + right)
