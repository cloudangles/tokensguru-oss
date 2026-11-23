import random

import pytest

from tokensguru.optimizers import (
    BulletDeduplicator,
    Optimizer,
    WhitespaceCleaner,
)
from tokensguru.optimizers.exact_bullet_item_deduplication import (
    _bullet_key,
    _continues_item,
    _indent_width,
)
from tokensguru.optimizers.utils import split_lines

dedupe = BulletDeduplicator()


def test_removes_an_adjacent_duplicate_and_keeps_the_first():
    assert dedupe.transform("- a\n- a\n- b\n") == "- a\n- b\n"


def test_removes_a_run_of_duplicates():
    assert dedupe.transform("- a\n- a\n- a\n- a\n- b\n") == "- a\n- b\n"


def test_works_with_every_marker():
    assert dedupe.transform("+ a\n+ a\n") == "+ a\n"
    assert dedupe.transform("* a\n* a\n") == "* a\n"


def test_keeps_duplicates_that_are_not_adjacent():
    text = "- a\n- b\n- a\n"
    assert dedupe.transform(text) == text


def test_a_blank_line_or_text_between_keeps_both():
    assert dedupe.transform("- a\n\n- a\n") == "- a\n\n- a\n"
    assert dedupe.transform("- a\nnote\n- a\n") == "- a\nnote\n- a\n"


def test_different_marker_indent_or_text_are_not_duplicates():
    for text in ["- a\n* a\n", "- a\n  - a\n", "- a\n- A\n", "- a\n- a b\n"]:
        assert dedupe.transform(text) == text


def test_tab_and_space_indentation_are_different():
    text = "\t- a\n    - a\n"
    assert dedupe.transform(text) == text


def test_nested_lists():
    text = "- a\n  - x\n  - x\n- a\n"
    assert dedupe.transform(text) == "- a\n  - x\n- a\n"


def test_trailing_spaces_are_ignored_when_comparing():
    assert dedupe.transform("- a  \n- a\n- a\t\n") == "- a  \n"


def test_inline_markup_and_task_items():
    assert dedupe.transform("- [ ] do it\n- [ ] do it\n") == "- [ ] do it\n"
    mixed = "- [ ] do it\n- [x] do it\n"
    assert dedupe.transform(mixed) == mixed
    assert dedupe.transform("- use `x`\n- use `x`\n") == "- use `x`\n"


def test_numbered_lists_are_left_alone():
    text = "1. a\n1. a\n"
    assert dedupe.transform(text) == text


def test_bullet_needs_a_space_after_the_marker():
    text = "-a\n-a\n**bold**\n**bold**\n"
    assert dedupe.transform(text) == text


def test_empty_bullets_are_left_alone():
    text = "- \n- \n-\n-\n"
    assert dedupe.transform(text) == text


def test_horizontal_rules_are_left_alone():
    text = "- - -\n- - -\n* * *\n* * *\n"
    assert dedupe.transform(text) == text


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_keeps_each_line_ending(ending):
    assert dedupe.transform(f"- a{ending}- a{ending}- b{ending}") == (
        f"- a{ending}- b{ending}"
    )


def test_last_line_without_an_ending():
    assert dedupe.transform("- a\n- a") == "- a"
    assert dedupe.transform("- a\r\n- a") == "- a"
    assert dedupe.transform("- b\n- a\n- a") == "- b\n- a"


def test_leaves_fenced_code_unchanged():
    text = "- a\n- a\n```\n- b\n- b\n```\n- c\n- c\n"
    assert dedupe.transform(text) == "- a\n```\n- b\n- b\n```\n- c\n"


def test_leaves_html_pre_blocks_unchanged():
    text = "<pre>\n- b\n- b\n</pre>\n- c\n- c\n"
    assert dedupe.transform(text) == "<pre>\n- b\n- b\n</pre>\n- c\n"


def test_leaves_yaml_front_matter_unchanged():
    text = "---\n- a\n- a\n---\n- b\n- b\n"
    assert dedupe.transform(text) == "---\n- a\n- a\n---\n- b\n"


def test_a_fence_between_duplicates_separates_them():
    text = "- a\n```\nx\n```\n- a\n"
    assert dedupe.transform(text) == text


def test_deep_indentation_inside_a_list_is_deduplicated():
    assert dedupe.transform("- x\n        - a\n        - a\n") == ("- x\n        - a\n")


def test_long_unicode_text():
    assert dedupe.transform("- café ☃\n- café ☃\n") == ("- café ☃\n")


def test_empty_and_plain_text():
    assert dedupe.transform("") == ""
    assert dedupe.transform("no bullets here\n") == "no bullets here\n"


@pytest.mark.parametrize("value", [None, 5, b"- a", ["- a"]])
def test_rejects_non_string_input(value):
    with pytest.raises(TypeError):
        dedupe.transform(value)  # type: ignore[arg-type]


def test_accepts_context():
    assert dedupe.transform("- a\n- a\n", {"x": 1}) == "- a\n"


def test_large_input_is_handled():
    text = "- same item\n" * 20000 + "- last\n"
    assert dedupe.transform(text) == "- same item\n- last\n"


def test_is_idempotent():
    once = dedupe.transform("- a\n- a\n  - b\n  - b\n- a\n")
    assert dedupe.transform(once) == once


def test_fuzz_only_whole_lines_are_removed_and_cleaning_is_stable():
    rng = random.Random(4321)  # noqa: S311
    alphabet = ["- a", "- b", "* a", "  - a", "    - a", "\t- a", "a", "  more", "",
                "```", "~~~", "---", "<pre>", "</pre>", "- - -", "- ", "1. a",
                "  1. a", "- a  ", "• a", "# h", "> q", "> - a"]  # fmt: skip
    endings = ["\n", "\r\n", "\r"]
    for _ in range(6000):
        count = rng.randint(0, 14)
        ending = rng.choice(endings)
        lines = [rng.choice(alphabet) for _ in range(count)]
        text = ending.join(lines) + (ending if rng.random() < 0.5 else "")
        out = dedupe.transform(text)
        assert len(out) <= len(text), repr(text)
        assert dedupe.transform(out) == out, repr(text)
        cursor = iter([line.rstrip("\r\n") for line in split_lines(text)])
        wanted = [line.rstrip("\r\n") for line in split_lines(out)]
        assert all(any(item == line for line in cursor) for item in wanted), repr(text)


def test_keeps_a_duplicate_that_has_sub_bullets():
    text = "- a\n- a\n  - child\n"
    assert dedupe.transform(text) == text


def test_keeps_a_duplicate_that_has_an_indented_follow_on_line():
    text = "- a\n- a\n  more detail\n"
    assert dedupe.transform(text) == text


def test_keeps_a_duplicate_with_a_lazy_continuation_line():
    text = "- a\n- a\ncontinues here\n"
    assert dedupe.transform(text) == text


def test_keeps_a_duplicate_followed_by_a_deeper_numbered_item():
    text = "- a\n- a\n  1. first\n"
    assert dedupe.transform(text) == text


def test_removes_a_duplicate_when_the_next_line_is_a_sibling_or_parent():
    assert dedupe.transform("- a\n- a\n- b\n") == "- a\n- b\n"
    assert dedupe.transform("- p\n  - a\n  - a\n- q\n") == "- p\n  - a\n- q\n"
    assert dedupe.transform("1. p\n- a\n- a\n2. q\n") == "1. p\n- a\n2. q\n"


@pytest.mark.parametrize(
    "after",
    ["", "\n", "# Heading\n", "## Heading\n", "> quote\n", "```\ncode\n```\n",
     "~~~\n", "---\n", "***\n", "- - -\n", "* * *\n", "\t\n", "   \n"],
)  # fmt: skip
def test_removes_a_duplicate_before_things_that_cannot_continue_it(after):
    assert dedupe.transform("- a\n- a\n" + after) == "- a\n" + after


def test_a_run_of_duplicates_where_only_the_last_has_children():
    text = "- a\n- a\n- a\n  child\n"
    assert dedupe.transform(text) == "- a\n- a\n  child\n"
    assert dedupe.transform(dedupe.transform(text)) == dedupe.transform(text)


def test_indented_code_block_is_left_alone():
    text = "Example:\n\n    - a\n    - a\n"
    assert dedupe.transform(text) == text
    tabbed = "Example:\n\n\t- a\n\t- a\n"
    assert dedupe.transform(tabbed) == tabbed


def test_indented_bullets_after_a_paragraph_ends_a_list_are_code():
    text = "- x\n\ntext\n\n    - a\n    - a\n"
    assert dedupe.transform(text) == text


def test_indented_bullets_after_a_blank_line_inside_a_list_are_items():
    text = "- x\n\n    - a\n    - a\n"
    assert dedupe.transform(text) == "- x\n\n    - a\n"


def test_numbered_item_opens_a_list_for_nested_bullets():
    assert dedupe.transform("1. x\n    - a\n    - a\n") == "1. x\n    - a\n"


def test_unicode_bullet_glyphs():
    assert dedupe.transform("• a\n• a\n") == "• a\n"
    assert dedupe.transform("◦ a\n◦ a\n") == "◦ a\n"
    assert dedupe.transform("• a\n- a\n") == "• a\n- a\n"


def test_tab_after_the_marker_counts_as_the_same_bullet():
    assert dedupe.transform("-\ta\n- a\n") == "-\ta\n"


def test_tab_indentation_counts_as_four_spaces_and_must_match_exactly():
    text = "- p\n\t- a\n    - a\n"
    assert dedupe.transform(text) == text
    assert dedupe.transform("- p\n\t- a\n\t- a\n") == "- p\n\t- a\n"


def test_bullets_inside_block_quotes_are_left_alone():
    text = "> - a\n> - a\n"
    assert dedupe.transform(text) == text


def test_ordered_list_markers_are_left_alone():
    text = "1) a\n1) a\n2. b\n2. b\n"
    assert dedupe.transform(text) == text


def test_a_different_item_resets_the_comparison():
    assert dedupe.transform("- a\n- b\n- b\n- a\n- a\n") == "- a\n- b\n- a\n"


def test_emoji_text():
    text = "- \U0001f600 ok\n- \U0001f600 ok\n"
    assert dedupe.transform(text) == "- \U0001f600 ok\n"


def test_very_long_lines():
    item = "- " + "word " * 20000
    assert dedupe.transform(item + "\n" + item + "\n") == item + "\n"


def test_html_block_between_duplicates_separates_them():
    text = "- a\n<pre>\n- b\n</pre>\n- a\n"
    assert dedupe.transform(text) == text


def test_front_matter_resets_the_comparison():
    text = "---\n- a\n---\n- a\n- a\n"
    assert dedupe.transform(text) == "---\n- a\n---\n- a\n"


def test_helpers():
    assert _indent_width("  x") == 2
    assert _indent_width("\tx") == 4
    assert _indent_width("x") == 0
    assert _continues_item(None, 0) is False
    assert _continues_item("   \n", 0) is False
    assert _continues_item("text\n", 0) is True
    assert _continues_item("- b\n", 0) is False
    assert _continues_item("  - b\n", 0) is True
    assert _continues_item("# h\n", 0) is False


def test_bullet_key_helper():
    assert _bullet_key("  - item  ") == ("  ", "-", "item")
    assert _bullet_key("text") is None
    assert _bullet_key("- - -") is None


def test_metadata():
    assert dedupe.id == "exact_bullet_item_deduplication"
    assert dedupe.name
    assert dedupe.applied_reason
    assert dedupe.skipped_reason


def test_both_optimizers_share_the_base_class():
    assert isinstance(dedupe, Optimizer)
    assert isinstance(WhitespaceCleaner(), Optimizer)
    with pytest.raises(TypeError):
        Optimizer()  # type: ignore[abstract]
