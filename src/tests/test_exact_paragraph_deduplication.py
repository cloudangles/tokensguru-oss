import random

import pytest

from tokensguru.optimizers import (
    OptimizationResult,
    Optimizer,
    ParagraphDeduplicator,
    Pipeline,
)
from tokensguru.optimizers.utils import split_lines

dedupe = ParagraphDeduplicator()
LONG = "The customer submitted a request to update his residential address."
OTHER = "Our team will review the submitted information and reply soon."


def test_removes_a_repeated_paragraph_and_keeps_the_first():
    assert dedupe.transform(f"{LONG}\n\n{LONG}\n") == f"{LONG}\n"


def test_removes_a_run_of_repeats():
    text = f"{LONG}\n\n\n{LONG}\n\n{LONG}\n\n{OTHER}\n"
    assert dedupe.transform(text) == f"{LONG}\n\n\n{OTHER}\n"


def test_removes_repeats_that_are_not_adjacent():
    text = f"{LONG}\n\n{OTHER}\n\n{LONG}\n"
    assert dedupe.transform(text) == f"{LONG}\n\n{OTHER}\n"


def test_unique_paragraphs_are_untouched():
    text = f"{LONG}\n\n{OTHER}\n"
    assert dedupe.transform(text) == text


def test_spacing_before_a_removed_paragraph_is_kept():
    text = f"{OTHER}\n\n\n\n{LONG}\n\n{LONG}\n\n\n\nEnd of the document here ok.\n"
    expected = f"{OTHER}\n\n\n\n{LONG}\n\nEnd of the document here ok.\n"
    assert dedupe.transform(text) == expected


def test_repeat_at_the_very_end_removes_the_blank_line_before_it():
    assert dedupe.transform(f"{LONG}\n\n{OTHER}\n\n{LONG}\n") == f"{LONG}\n\n{OTHER}\n"


def test_repeat_at_the_end_without_a_line_ending():
    assert dedupe.transform(f"{LONG}\n\n{LONG}") == LONG
    assert dedupe.transform(f"{LONG}\r\n\r\n{OTHER}\r\n\r\n{LONG}") == (
        f"{LONG}\r\n\r\n{OTHER}"
    )


def test_trailing_blank_lines_after_a_removed_last_paragraph():
    assert dedupe.transform(f"{LONG}\n\n{LONG}\n\n\n") == f"{LONG}\n\n"


def test_multi_line_paragraphs():
    para = "line one of the paragraph\nline two of the paragraph\nline three here"
    assert dedupe.transform(f"{para}\n\n{para}\n") == f"{para}\n"


def test_a_paragraph_that_differs_by_one_line_is_kept():
    first = "line one of the paragraph\nline two of the paragraph"
    second = "line one of the paragraph\nline TWO of the paragraph"
    text = f"{first}\n\n{second}\n"
    assert dedupe.transform(text) == text


def test_matching_is_case_sensitive():
    text = f"{LONG}\n\n{LONG.upper()}\n"
    assert dedupe.transform(text) == text


def test_spaces_around_a_paragraph_do_not_matter():
    assert dedupe.transform(f"{LONG}\n\n   {LONG}   \n") == f"{LONG}\n"
    assert dedupe.transform(f"{LONG}   \n\n{LONG}\n") == f"{LONG}   \n"


def test_tab_indented_text_is_treated_as_code():
    text = f"{LONG}\n\n\t{LONG}\t\n"
    assert dedupe.transform(text) == text


def test_whitespace_only_lines_separate_paragraphs():
    assert dedupe.transform(f"{LONG}\n   \n{LONG}\n") == f"{LONG}\n"


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_keeps_each_line_ending(ending):
    text = f"{LONG}{ending}{ending}{LONG}{ending}{ending}{OTHER}{ending}"
    assert dedupe.transform(text) == f"{LONG}{ending}{ending}{OTHER}{ending}"


def test_mixed_line_endings_still_match():
    first = "first line of the paragraph here\r\nsecond line of the paragraph here"
    second = first.replace("\r\n", "\n")
    text = f"{first}\r\n\r\n{second}\n"
    assert dedupe.transform(text) == f"{first}\r\n"


def test_short_paragraphs_are_never_removed_by_default():
    text = "Thank you.\n\nThank you.\n\nCustomer:\n\nCustomer:\n"
    assert dedupe.transform(text) == text


def test_min_length_option():
    short = ParagraphDeduplicator(min_length=0)
    assert short.transform("Thank you.\n\nThank you.\n") == "Thank you.\n"
    longer = ParagraphDeduplicator(min_length=200)
    text = f"{LONG}\n\n{LONG}\n"
    assert longer.transform(text) == text


def test_options_are_validated():
    with pytest.raises(ValueError):
        ParagraphDeduplicator(min_length=-1)
    with pytest.raises(TypeError):
        ParagraphDeduplicator(min_length="40")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ParagraphDeduplicator(min_length=True)


def test_adjacent_only_removes_only_back_to_back_repeats():
    adjacent = ParagraphDeduplicator(adjacent_only=True)
    assert adjacent.transform(f"{LONG}\n\n{LONG}\n\n{OTHER}\n") == (
        f"{LONG}\n\n{OTHER}\n"
    )
    spread = f"{LONG}\n\n{OTHER}\n\n{LONG}\n"
    assert adjacent.transform(spread) == spread


def test_adjacent_only_is_broken_by_a_protected_block_or_heading():
    adjacent = ParagraphDeduplicator(adjacent_only=True)
    text = f"{LONG}\n\n```\ncode\n```\n\n{LONG}\n"
    assert adjacent.transform(text) == text
    text = f"{LONG}\n\n# Heading\n\n{LONG}\n"
    assert adjacent.transform(text) == text


@pytest.mark.parametrize(
    "paragraph",
    [
        "# A heading that is long enough to count here",
        "## A second level heading that is long enough",
        "Heading with an underline that is long enough\n=====",
        "Another title that is long enough to be counted\n-----",
        "-----------------------------------------------------",
        "* * * * * * * * * * * * * * * * * * * * * * * * * *",
        "| column one | column two | column three | col four |",
        "a | b | c | d | e | f | g | h | i | j\n--|--|--|--|--|--|--|--|--|--",
        "- a bullet item that is long enough to be counted ok",
        "1. a numbered item that is long enough to be counted",
        "• a glyph bullet that is long enough to be counted",
        "> a quoted paragraph that is long enough to be counted",
        "    indented code that is long enough to be counted ok",
        "\tindented code that is long enough to be counted ok",
        "<div>html that is long enough to be counted here</div>",
        "[ref]: https://example.com/a-long-link-definition-here",
        "[^1]: a footnote that is long enough to be counted here",
        "........................................................",
        "Here is a long lead in sentence that introduces a list:",
        "Here is a long lead in sentence with a wide colon\N{FULLWIDTH COLON}",
    ],
)
def test_structural_paragraphs_are_never_removed(paragraph):
    text = f"{paragraph}\n\nIntro text that sits between the two.\n\n{paragraph}\n"
    assert dedupe.transform(text) == text


def test_text_that_only_looks_a_little_like_structure_is_still_deduplicated():
    for para in [
        "*emphasis* starts this paragraph and it is long enough",
        "-5 degrees is the temperature at the start of the day",
        "1.5 million customers were served during the last year",
        "a paragraph with a pipe | inside it that is long enough",
    ]:
        assert dedupe.transform(f"{para}\n\n{para}\n") == f"{para}\n"


def test_fenced_code_is_left_alone_and_never_counted():
    code = "```\nprint('a line of code that is long enough here')\n```"
    text = f"{code}\n\n{code}\n"
    assert dedupe.transform(text) == text


def test_blank_lines_inside_code_do_not_split_it():
    text = f"```\n{LONG}\n\n{LONG}\n```\n"
    assert dedupe.transform(text) == text


def test_repeat_after_a_code_block_is_removed():
    text = f"{LONG}\n\n```\ncode\n```\n\n{LONG}\n"
    assert dedupe.transform(text) == f"{LONG}\n\n```\ncode\n```\n"


def test_html_pre_block_and_front_matter_are_left_alone():
    text = (
        f"---\ntitle: {LONG}\n\n{LONG}\n---\n\n{LONG}\n\n"
        f"<pre>\n{LONG}\n\n{LONG}\n</pre>\n"
    )
    assert dedupe.transform(text) == text


def test_a_paragraph_touching_a_code_block_is_its_own_paragraph():
    text = f"{LONG}\n```\ncode\n```\n{LONG}\n"
    assert dedupe.transform(text) == f"{LONG}\n```\ncode\n```\n"


def test_non_latin_text():
    para = "これはテストの段落です。" * 4
    assert dedupe.transform(f"{para}\n\n{para}\n") == f"{para}\n"
    emoji = "\U0001f600 " * 25 + "ok"
    assert dedupe.transform(f"{emoji}\n\n{emoji}\n") == f"{emoji}\n"


def test_empty_and_blank_text():
    assert dedupe.transform("") == ""
    assert dedupe.transform("\n\n\n") == "\n\n\n"
    assert dedupe.transform("   ") == "   "


def test_single_paragraph_and_no_trailing_newline():
    assert dedupe.transform(LONG) == LONG


def test_whitespace_inside_a_paragraph_must_match():
    text = f"{LONG}\n\n{LONG.replace(' ', '  ', 1)}\n"
    assert dedupe.transform(text) == text


def test_repeats_across_sections_are_removed_unless_adjacent_only_is_used():
    text = f"# One\n\n{LONG}\n\n# Two\n\n{LONG}\n"
    assert dedupe.transform(text) == f"# One\n\n{LONG}\n\n# Two\n"
    assert ParagraphDeduplicator(adjacent_only=True).transform(text) == text


def test_large_input_is_handled():
    text = "".join(f"{LONG}\n\n" for _ in range(20000)) + f"{OTHER}\n"
    assert dedupe.transform(text) == f"{LONG}\n\n{OTHER}\n"


@pytest.mark.parametrize("value", [None, 5, b"text", ["a"]])
def test_rejects_non_string_input(value):
    with pytest.raises(TypeError):
        dedupe.transform(value)  # type: ignore[arg-type]


def test_accepts_context():
    assert dedupe.transform(f"{LONG}\n\n{LONG}\n", {"x": 1}) == f"{LONG}\n"


def test_optimize_returns_a_full_result():
    result = dedupe.optimize(f"{LONG}\n\n{LONG}\n\n{LONG}\n")
    assert isinstance(result, OptimizationResult)
    assert isinstance(dedupe, Optimizer)
    assert result.optimizer_id == "exact_paragraph_deduplication"
    assert result.optimizer_name == "Exact paragraph deduplication"
    assert result.optimized_text == f"{LONG}\n"
    assert result.reason == ParagraphDeduplicator.applied_reason
    assert result.original_tokens == 3 * len(LONG.split())
    assert result.optimized_tokens == len(LONG.split())
    assert result.saved_tokens == 2 * len(LONG.split())


def test_unchanged_text_uses_the_skipped_reason():
    result = dedupe.optimize(f"{LONG}\n\n{OTHER}\n")
    assert result.changed is False
    assert result.reason == ParagraphDeduplicator.skipped_reason


def test_is_idempotent():
    text = f"{LONG}\n\n\n{OTHER}\n\n{LONG}\n\n{OTHER}\n\n{LONG}"
    once = dedupe.transform(text)
    assert dedupe.transform(once) == once


def test_works_inside_the_default_pipeline():
    text = f"# Title\n\n{LONG}\n\n\n\n{LONG}   \n\n{OTHER}\n"
    result = Pipeline().optimize(text)
    assert result.optimized_text == f"# Title\n\n{LONG}\n\n{OTHER}\n"
    assert "Exact paragraph deduplication" in result.reason


PIECES = [
    "alpha beta gamma delta epsilon zeta eta theta iota kappa",
    "alpha beta gamma delta epsilon zeta eta theta iota kappa ",
    "  alpha beta gamma delta epsilon zeta eta theta iota kappa",
    "other text that is long enough to count here",
    "short",
    "",
    "   ",
    "# heading that is long enough to be counted ok",
    "```",
    "<pre>",
    "</pre>",
    "- bullet item that is long enough to be counted",
    "> quote",
    "intro that is long enough to end with a colon:",
    "---",
    "line one\nline two",
    "\u2022 glyph item long enough to be counted here",
]


def test_fuzz_only_whole_paragraphs_are_removed_and_cleaning_is_stable():
    rng = random.Random(2468)  # noqa: S311
    endings = ["\n", "\r\n", "\r"]
    options = (
        ParagraphDeduplicator(),
        ParagraphDeduplicator(adjacent_only=True),
        ParagraphDeduplicator(min_length=0),
    )
    for _ in range(6000):
        ending = rng.choice(endings)
        body = ending.join(rng.choice(PIECES) for _ in range(rng.randint(0, 12)))
        text = body + (ending if rng.random() < 0.5 else "")
        for option in options:
            out = option.transform(text)
            assert len(out) <= len(text), repr(text)
            assert option.transform(out) == out, repr(text)
            cursor = iter([line.rstrip("\r\n") for line in split_lines(text)])
            wanted = [line.rstrip("\r\n") for line in split_lines(out)]
            assert all(any(w == c for c in cursor) for w in wanted), repr(text)
            before = {line.strip() for line in text.splitlines()} - {""}
            after = {line.strip() for line in out.splitlines()} - {""}
            assert before == after, repr(text)
