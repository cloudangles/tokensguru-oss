import random

import pytest

from tokensguru.optimizers import CleanupResult, WhitespaceCleaner
from tokensguru.optimizers.utils import (
    BlockTracker,
    front_matter_length,
    is_json_document,
    split_line_ending,
    split_lines,
)

cleaner = WhitespaceCleaner()


def test_removes_trailing_spaces_and_tabs():
    assert cleaner.optimize("hello   \nworld\t\t\n") == "hello\nworld\n"


def test_collapses_repeated_spaces_inside_a_line():
    assert cleaner.optimize("hello      world") == "hello world"
    assert cleaner.optimize("a \t  b") == "a b"


def test_keeps_single_spaces_and_single_tabs():
    assert cleaner.optimize("a b\tc") == "a b\tc"


def test_keeps_leading_indentation():
    assert cleaner.optimize("  indented   text  \n") == "  indented text\n"


def test_keeps_non_ascii_spaces():
    text = "a\u00a0\u00a0b\u3000\u3000c\u2003\u2003d \n"
    assert cleaner.optimize(text) == "a\u00a0\u00a0b\u3000\u3000c\u2003\u2003d\n"


def test_form_feed_and_unicode_separators_are_not_line_endings():
    text = "a  b\x0cc  d\u2028e  f\x85g  h\n"
    assert cleaner.optimize(text) == "a b\x0cc d\u2028e f\x85g h\n"


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_keeps_each_line_ending(ending):
    assert cleaner.optimize(f"a  {ending}b  {ending}") == f"a{ending}b{ending}"


def test_no_trailing_line_ending():
    assert cleaner.optimize("a  \nb  ") == "a\nb"


def test_keeps_mixed_line_endings():
    assert cleaner.optimize("a \r\nb \nc \rd ") == "a\r\nb\nc\rd"


def test_keeps_byte_order_mark():
    assert cleaner.optimize("﻿hello   world\n") == "﻿hello world\n"


def test_collapses_blank_line_runs_to_one():
    assert cleaner.optimize("a\n\n\n\n\nb\n") == "a\n\nb\n"


def test_whitespace_only_lines_count_as_blank():
    assert cleaner.optimize("a\n   \n\t\n  \nb\n") == "a\n\nb\n"


def test_keeps_a_single_blank_line():
    assert cleaner.optimize("a\n\nb\n") == "a\n\nb\n"


def test_max_blank_lines_option():
    assert WhitespaceCleaner(max_blank_lines=2).optimize("a\n\n\n\nb") == "a\n\n\nb"
    assert WhitespaceCleaner(max_blank_lines=0).optimize("a\n\n\nb") == "a\nb"


def test_trailing_blank_lines_are_collapsed():
    assert cleaner.optimize("a\n\n\n\n") == "a\n\n"


def test_max_blank_lines_is_validated():
    with pytest.raises(ValueError):
        WhitespaceCleaner(max_blank_lines=-1)
    with pytest.raises(TypeError):
        WhitespaceCleaner(max_blank_lines="1")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        WhitespaceCleaner(max_blank_lines=True)


def test_hard_breaks_are_stripped_by_default():
    assert cleaner.optimize("one   \ntwo\n") == "one\ntwo\n"


def test_keep_markdown_line_breaks_keeps_exactly_two_spaces():
    keep = WhitespaceCleaner(keep_markdown_line_breaks=True)
    assert keep.optimize("one     \ntwo\n") == "one  \ntwo\n"


def test_keep_markdown_line_breaks_ignores_the_last_line_and_blank_next():
    keep = WhitespaceCleaner(keep_markdown_line_breaks=True)
    assert keep.optimize("one  \n\ntwo  ") == "one\n\ntwo"


def test_keep_markdown_line_breaks_needs_spaces_not_a_tab():
    keep = WhitespaceCleaner(keep_markdown_line_breaks=True)
    assert keep.optimize("one\t\t\ntwo") == "one\ntwo"


def test_cleans_headings_lists_and_quotes_line_by_line():
    text = "# Title      here  \n- item    one  \n> quote    two  \n"
    assert cleaner.optimize(text) == "# Title here\n- item one\n> quote two\n"


def test_cleans_prose_around_a_masked_email():
    text = "Mail  j***@example.com   now.   \n"
    assert cleaner.optimize(text) == "Mail j***@example.com now.\n"


@pytest.mark.parametrize(
    "text",
    [
        "code `x    y`   \n",
        "| a    | b |   \n",
        "    indented    code   \n",
        "\tcode    here\n",
    ],
)
def test_leaves_protected_lines_unchanged(text):
    assert cleaner.optimize(text) == text


def test_leaves_fenced_code_unchanged():
    text = "intro   text\n```\nx    =   1   \n\n\n\ny = 2\n```\nafter   text  \n"
    expected = "intro text\n```\nx    =   1   \n\n\n\ny = 2\n```\nafter text\n"
    assert cleaner.optimize(text) == expected


def test_tilde_fence_and_language_tag():
    text = "~~~python\nx    =   1\n~~~\nb    c\n"
    assert cleaner.optimize(text) == "~~~python\nx    =   1\n~~~\nb c\n"


def test_longer_outer_fence_is_not_closed_by_a_shorter_inner_one():
    text = "````\n```\nx    y\n```\nz    w\n````\nok    done\n"
    assert cleaner.optimize(text) == "````\n```\nx    y\n```\nz    w\n````\nok done\n"


def test_fence_is_closed_only_by_the_same_character():
    text = "```\na    b\n~~~\nc    d\n```\ne    f\n"
    assert cleaner.optimize(text) == "```\na    b\n~~~\nc    d\n```\ne f\n"


def test_unclosed_fence_protects_the_rest():
    text = "a   b\n```\nx    y\n\n\nz\n"
    assert cleaner.optimize(text) == "a b\n```\nx    y\n\n\nz\n"


def test_backtick_in_a_fence_info_string_is_not_a_fence():
    text = "``` a`b\nc    d\n\n\n\ne\n"
    assert cleaner.optimize(text) == "``` a`b\nc d\n\ne\n"


def test_leaves_html_pre_block_unchanged():
    text = "a   b\n<pre>\nx    y\n\n\nz\n</pre>\nc    d\n"
    assert cleaner.optimize(text) == "a b\n<pre>\nx    y\n\n\nz\n</pre>\nc d\n"


def test_one_line_html_raw_block_is_protected_and_closed():
    text = "<style>a    b</style>\nc    d\n"
    assert cleaner.optimize(text) == "<style>a    b</style>\nc d\n"


def test_leaves_yaml_front_matter_unchanged():
    text = "---\ntitle:    My   doc\n\n\nkey:  v\n---\n\n\n\nBody    text\n"
    expected = "---\ntitle:    My   doc\n\n\nkey:  v\n---\n\nBody text\n"
    assert cleaner.optimize(text) == expected


def test_dashes_without_a_closing_line_are_not_front_matter():
    assert cleaner.optimize("---\na    b\n") == "---\na b\n"


@pytest.mark.parametrize(
    "text",
    [
        '{"a":   "x    y",\n\n\n "b": 1}',
        "[1,    2,\n\n\n3]\n",
        '  {"k":  "v"}  ',
    ],
)
def test_json_documents_are_left_unchanged(text):
    assert cleaner.optimize(text) == text


def test_text_that_only_starts_like_json_is_cleaned():
    assert cleaner.optimize("[note]   hello    there") == "[note] hello there"


def test_empty_text():
    assert cleaner.optimize("") == ""


def test_only_whitespace():
    assert cleaner.optimize("   \t  ") == ""
    assert cleaner.optimize("\n\n\n") == "\n"


def test_unchanged_when_nothing_to_remove():
    assert cleaner.optimize("clean\ntext\n") == "clean\ntext\n"


@pytest.mark.parametrize("value", [None, 5, b"bytes", ["a"]])
def test_rejects_non_string_input(value):
    with pytest.raises(TypeError):
        cleaner.optimize(value)  # type: ignore[arg-type]


def test_accepts_context_argument():
    assert cleaner.optimize("a  ", {"query": "x"}) == "a"


def test_object_is_callable():
    assert cleaner("a  \n") == "a\n"


def test_large_input_is_handled():
    text = ("word   " * 50 + "\n\n\n") * 2000
    out = cleaner.optimize(text)
    assert "  " not in out
    assert out.count("\n\n\n") == 0


def test_report_counts_savings():
    result = cleaner.report("a    b  \n")
    assert isinstance(result, CleanupResult)
    assert result.text == "a b\n"
    assert (result.original_length, result.cleaned_length) == (9, 4)
    assert result.saved_chars == 5
    assert result.saved_percent == 55.56
    assert result.changed is True


def test_report_when_nothing_changes():
    result = cleaner.report("clean")
    assert result.saved_chars == 0
    assert result.changed is False


def test_report_of_empty_text():
    assert cleaner.report("").saved_percent == 0.0


def test_is_idempotent():
    once = cleaner.optimize("a   b  \n\n\n\nc\t\td\n")
    assert cleaner.optimize(once) == once


def test_fuzz_only_whitespace_changes_and_cleaning_is_stable():
    rng = random.Random(1234)  # noqa: S311
    alphabet = ["a", "b", " ", "  ", "\t", "\n", "\r\n", "\r", "`", "```", "~~~",
                "|", "#", "\u00a0", "\x0c", "---", "<pre>", "</pre>", "{", "[", "."]  # fmt: skip # noqa: E501
    for _ in range(4000):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
        for option in (cleaner, WhitespaceCleaner(0, True)):
            out = option.optimize(text)
            assert "".join(out.split()) == "".join(text.split()), repr(text)
            assert len(out) <= len(text), repr(text)
            assert option.optimize(out) == out, repr(text)


def test_metadata():
    assert cleaner.id == "prose_whitespace_cleanup"
    assert cleaner.name
    assert cleaner.applied_reason
    assert cleaner.skipped_reason


def test_split_line_ending():
    assert split_line_ending("a\r\n") == ("a", "\r\n")
    assert split_line_ending("a\n") == ("a", "\n")
    assert split_line_ending("a\r") == ("a", "\r")
    assert split_line_ending("a") == ("a", "")


def test_split_lines_only_splits_on_real_line_endings():
    assert split_lines("a\r\nb\rc\nd\x0ce") == ["a\r\n", "b\r", "c\n", "d\x0ce"]
    assert split_lines("") == []


def test_is_json_document():
    assert is_json_document(' {"a": 1} ')
    assert is_json_document("[1, 2]")
    assert not is_json_document("[not json]")
    assert not is_json_document("plain text")


def test_front_matter_length():
    assert front_matter_length(["---\n", "a: 1\n", "---\n", "text\n"]) == 3
    assert front_matter_length(["---\n", "a: 1\n"]) == 0
    assert front_matter_length([]) == 0
    assert front_matter_length(["text\n", "---\n", "---\n"]) == 0


def test_block_tracker_protects_code_and_table_lines():
    tracker = BlockTracker()
    assert tracker.protects("use `x`")
    assert tracker.protects("| a | b |")
    assert tracker.protects("    code")
    assert not tracker.protects("  two-space indent")
    assert not tracker.protects("   \t")
