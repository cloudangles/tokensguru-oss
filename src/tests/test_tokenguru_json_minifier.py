import json
import random
import re

import pytest

from tokensguru.optimizers import (
    JsonMinifier,
    OptimizationResult,
    Optimizer,
    Pipeline,
)

minify = JsonMinifier()
LEXICAL = (
    r'"(?:\\.|[^"\\])*"|true|false|null|'
    r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|[{}\[\],:]"
)


def tokens(text):
    return re.findall(LEXICAL, text)


def test_minifies_a_pretty_printed_object():
    text = '{\n  "a": 1,\n  "b": [1, 2, 3],\n  "c": {"d": null}\n}\n'
    assert minify.transform(text) == '{"a":1,"b":[1,2,3],"c":{"d":null}}'


def test_minifies_arrays_and_nested_structures():
    assert (
        minify.transform('[\n  1,\n  [2, 3],\n  {"a": []}\n]') == '[1,[2,3],{"a":[]}]'
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  123  ", "123"),
        ('\n"hello"\n', '"hello"'),
        ("\ttrue\r\n", "true"),
        (" null ", "null"),
        (" -1.5e3 ", "-1.5e3"),
        ("  []  ", "[]"),
        ("{ }", "{}"),
    ],
)
def test_minifies_single_values_and_surrounding_whitespace(text, expected):
    assert minify.transform(text) == expected


def test_keeps_whitespace_inside_strings():
    text = '{ "a b": "x   y\\n  z\\t", "k": " padded " }'
    assert minify.transform(text) == '{"a b":"x   y\\n  z\\t","k":" padded "}'


def test_keeps_escapes_quotes_and_unicode_inside_strings_exactly():
    text = (
        '{ "q": "say \\"hi\\"  now", "u": "\\u0061 \\ud83d\\ude00", "s": "\\\\ \\/" }'
    )
    out = minify.transform(text)
    assert (
        out == '{"q":"say \\"hi\\"  now","u":"\\u0061 \\ud83d\\ude00","s":"\\\\ \\/"}'
    )


def test_a_string_that_ends_in_a_backslash_pair_closes_correctly():
    text = '{ "a": "x\\\\" , "b": "y" }'
    assert minify.transform(text) == '{"a":"x\\\\","b":"y"}'


def test_number_formats_and_key_order_are_kept_as_written():
    text = '{ "z": 1.00, "a": 1E5, "m": -0, "big": 123456789012345678901234567890 }'
    assert minify.transform(text) == (
        '{"z":1.00,"a":1E5,"m":-0,"big":123456789012345678901234567890}'
    )


def test_duplicate_keys_are_kept():
    assert minify.transform('{ "a": 1, "a": 2 }') == '{"a":1,"a":2}'


def test_only_json_whitespace_is_removed():
    out = minify.transform('{\r\n\t"a"\t:\t1\r\n}')
    assert out == '{"a":1}'


def test_every_other_character_stays_exactly_the_same():
    text = json.dumps(
        {"name": "x  y", "list": [1, 2.50, True, None], "nested": {"k": "v"}},
        indent=4,
    )
    assert tokens(minify.transform(text)) == tokens(text)
    assert json.loads(minify.transform(text)) == json.loads(text)


@pytest.mark.parametrize(
    "text",
    [
        '{"a":1}',
        "[1,2,3]",
        "123",
        '"text"',
        "true",
        "null",
        "[]",
        "{}",
    ],
)
def test_compact_json_is_unchanged(text):
    assert minify.transform(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "plain text with   spaces",
        "{ not json }",
        "{ 'a': 1 }",
        '{ "a": 1, }',
        "[1, 2, ]",
        '{ "a": 1 } { "b": 2 }',
        '{ "a": 1 }\n{ "b": 2 }',
        '{ "a": 1 } trailing',
        '// comment\n{ "a": 1 }',
        '{ /* c */ "a": 1 }',
        '{ "a": NaN }',
        "[ Infinity ]",
        "[ -Infinity ]",
        '{ "a": 01 }',
        '{ "a": .5 }',
        '{ "a": "line\nbreak" }',
        '{ "a": "tab\there" }',
        '{ "a": 1',
        '"unterminated',
        '\ufeff{ "a": 1 }',
        '{ "a":\u00a01 }',
        '```json\n{ "a": 1 }\n```',
        'Result: { "a": 1 }',
    ],
)
def test_text_that_is_not_one_valid_json_document_is_unchanged(text):
    assert minify.transform(text) == text


def test_very_deeply_nested_json_does_not_crash():
    text = "[" * 5000 + "]" * 5000
    assert minify.transform(text) == text


def test_deeply_nested_json_within_limits_is_minified():
    text = "[ " * 100 + "] " * 100
    assert minify.transform(text) == "[" * 100 + "]" * 100


def test_huge_integers_do_not_break_validation():
    digits = "9" * 6000
    text = f'{{ "n": {digits} }}'
    assert minify.transform(text) == f'{{"n":{digits}}}'


def test_unicode_and_emoji_keys_and_values():
    text = '{ "\u00e9\u00e8": "\U0001f600  ok", "\u65e5\u672c": [ "\u8a9e" ] }'
    assert (
        minify.transform(text)
        == '{"\u00e9\u00e8":"\U0001f600  ok","\u65e5\u672c":["\u8a9e"]}'
    )


def test_lone_surrogate_escapes_are_valid_and_kept():
    assert minify.transform('{ "a": "\\ud800" }') == '{"a":"\\ud800"}'


def test_large_input_is_handled():
    data = [{"id": i, "name": f"item {i}", "tags": ["a", "b"]} for i in range(20000)]
    text = json.dumps(data, indent=2)
    out = minify.transform(text)
    assert len(out) < len(text)
    assert json.loads(out) == data
    assert tokens(out) == tokens(text)


def test_string_heavy_input_is_fast():
    text = json.dumps({"k": "word  " * 200000}, indent=2)
    assert minify.transform(text) == '{"k":"' + "word  " * 200000 + '"}'


def test_is_idempotent():
    once = minify.transform('{\n  "a": [1,  2]\n}\n')
    assert minify.transform(once) == once


@pytest.mark.parametrize("value", [None, 5, b"{}", ["a"], {"a": 1}])
def test_rejects_non_string_input(value):
    with pytest.raises(TypeError):
        minify.transform(value)


def test_accepts_context():
    assert minify.transform('{ "a": 1 }', {"x": 1}) == '{"a":1}'


def test_optimize_returns_a_full_result():
    text = '{\n    "a": 1,\n    "b": [\n        1,\n        2\n    ]\n}\n'
    result = minify.optimize(text)
    assert isinstance(result, OptimizationResult)
    assert isinstance(minify, Optimizer)
    assert result.optimizer_id == "tokenguru_json_minifier"
    assert result.optimizer_name == "JSON minifier"
    assert result.optimized_text == '{"a":1,"b":[1,2]}'
    assert result.reason == JsonMinifier.applied_reason
    assert result.saved_chars == len(text) - len(result.optimized_text)
    assert result.changed is True


def test_unchanged_text_uses_the_skipped_reason():
    result = minify.optimize("just words")
    assert result.changed is False
    assert result.reason == JsonMinifier.skipped_reason


def test_json_is_minified_first_in_the_default_pipeline():
    text = '{\n  "a": "x  y",\n\n\n  "b": [1, 2]\n}\n'
    result = Pipeline().optimize(text)
    assert result.optimized_text == '{"a":"x  y","b":[1,2]}'
    assert result.steps[0].optimizer_id == "tokenguru_json_minifier"
    assert result.steps[0].changed is True
    assert not any(step.changed for step in result.steps[1:])


def test_prose_passes_through_the_json_step_untouched():
    result = Pipeline().optimize("Hello   world\n")
    assert result.steps[0].changed is False
    assert result.optimized_text == "Hello world\n"


SCALARS = [
    lambda rng: rng.randint(-(10**6), 10**6),
    lambda rng: rng.choice([1.0, 2.50, -3.25e10, 0.1, 1e-7]),
    lambda rng: rng.choice(["", " ", "a  b", 'q"uote']),
    lambda rng: rng.choice(["back\\slash", "tab\t", "\u00e9"]),
    lambda rng: rng.choice(["\U0001f600", "new\nline"]),
    lambda rng: rng.choice([True, False]),
    lambda rng: None,
]  # fmt: skip
KEYS = ["a", "b c", "k", "\u00e9", ""]


def random_json(rng, depth=0):
    if depth >= 3 or rng.random() < 0.5:
        return rng.choice(SCALARS)(rng)
    size = rng.randint(0, 4)
    if rng.random() < 0.5:
        return [random_json(rng, depth + 1) for _ in range(size)]
    return {rng.choice(KEYS): random_json(rng, depth + 1) for _ in range(size)}


def test_fuzz_output_is_the_same_json_token_for_token():
    rng = random.Random(97531)  # noqa: S311
    for _ in range(3000):
        value = random_json(rng)
        text = json.dumps(
            value,
            indent=rng.choice([None, 0, 1, 2, 4, "\t"]),
            separators=rng.choice([None, (", ", ": "), (",", ":"), (" , ", " : ")]),
            ensure_ascii=rng.random() < 0.5,
            sort_keys=rng.random() < 0.5,
        )
        text = (
            rng.choice(["", " ", "\n", "\r\n\t"]) + text + rng.choice(["", " ", "\n"])
        )
        out = minify.transform(text)
        assert len(out) <= len(text), repr(text)
        assert tokens(out) == tokens(text), repr(text)
        assert json.loads(out) == json.loads(text), repr(text)
        assert minify.transform(out) == out, repr(text)
        if out != text:
            assert not re.search(r"^[ \t\r\n]|[ \t\r\n]$", out)


def test_fuzz_damaged_json_is_never_corrupted():
    rng = random.Random(24680)  # noqa: S311
    junk = ['"', "{", "}", "[", "]", ",", ":", " ", "\n", "\\", "x", "1", "\u00a0"]
    for _ in range(4000):
        text = json.dumps(random_json(rng), indent=rng.choice([None, 2]))
        for _ in range(rng.randint(1, 3)):
            position = rng.randint(0, len(text))
            if rng.random() < 0.5 and text:
                text = text[:position] + text[position + 1 :]
            else:
                text = text[:position] + rng.choice(junk) + text[position:]
        out = minify.transform(text)
        assert len(out) <= len(text), repr(text)
        assert minify.transform(out) == out, repr(text)
        if out != text:
            assert json.loads(out) == json.loads(text), repr(text)
            assert tokens(out) == tokens(text), repr(text)
