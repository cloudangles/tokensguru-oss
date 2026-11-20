"""`tokensguru observability`: trace table. Select a row and press Enter for its graph and tree."""

from __future__ import annotations

from collections.abc import Callable

from tokensguru.cli.screen import (
    DOWN_KEYS,
    ENTER_KEYS,
    EXIT_KEYS,
    UP_KEYS,
    Screen,
    open_screen,
)
from tokensguru.cli.style import PURPLE_BG, RED_BG, RESET, REVERSE
from tokensguru.observability import render, store
from tokensguru.observability.models import Trace

TITLE = "TokensGuru Observability"
NO_TRACES = "No traces yet."
BACK = "b"
GRAPH = "g"
TREE = "t"
SIDE_MARGIN = 6  # space kept free on each side of the table
# Rows around the detail body: frame (2) + title/blank/blank/buttons (4)
# + summary and its blank line (3) + breathing room (5).
DETAIL_OVERHEAD_ROWS = 14

LIST_BUTTONS = [
    ("↑↓  Select", PURPLE_BG),
    ("Enter  Open", PURPLE_BG),
    ("B  Back", PURPLE_BG),
    ("Ctrl+X  Exit", RED_BG),
]
DETAIL_BUTTONS = [
    ("G  Graph", PURPLE_BG),
    ("T  Tree", PURPLE_BG),
    ("↑↓  Scroll", PURPLE_BG),
    ("B  Back", PURPLE_BG),
    ("Ctrl+X  Exit", RED_BG),
]


def view() -> bool:
    """Show the observability screens. True means the user asked to exit the app."""
    with open_screen() as screen:
        return _list(screen) in EXIT_KEYS


def _highlight(row: str) -> str:
    return f"{REVERSE}{row}{RESET}"


def _list(screen: Screen) -> str:
    traces = store.list_traces()
    selected = 0
    while True:
        cols, _ = screen.size
        table = render.table(traces, cols - SIDE_MARGIN)
        rows = [
            _highlight(row) if screen.interactive and index == selected else row
            for index, row in enumerate(table.rows)
        ]
        key = screen.ask(TITLE, [*table.header, *(rows or [NO_TRACES])], LIST_BUTTONS)
        if key in EXIT_KEYS or key == BACK:
            return key
        if key in UP_KEYS:
            selected = max(0, selected - 1)
        elif key in DOWN_KEYS and traces:
            selected = min(len(traces) - 1, selected + 1)
        elif key in ENTER_KEYS and traces:
            result = _detail(screen, traces[selected])
            if result in EXIT_KEYS:
                return result


def _detail(screen: Screen, trace: Trace) -> str:
    _, rows = screen.size
    window = max(1, rows - DETAIL_OVERHEAD_ROWS)
    draw: Callable[[Trace], list[str]] = render.graph
    offset = 0
    while True:
        lines = draw(trace)
        max_offset = max(0, len(lines) - window)
        offset = min(offset, max_offset)
        body = [*render.summary(trace), "", *lines[offset : offset + window]]
        key = screen.ask(f"Trace {trace.id[:8]}", body, DETAIL_BUTTONS)
        if key in EXIT_KEYS or key == BACK:
            return key
        if key == GRAPH:
            draw, offset = render.graph, 0
        elif key == TREE:
            draw, offset = render.tree, 0
        elif key in DOWN_KEYS:
            offset = min(offset + 1, max_offset)
        elif key in UP_KEYS:
            offset = max(0, offset - 1)


def run() -> int:
    view()
    return 0
