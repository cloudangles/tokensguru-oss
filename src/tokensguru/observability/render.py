"""Turns traces into lines of plain text for the observability screens."""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

from tokensguru.observability.models import Trace

SEP = " "
INDENT = "    "
MIN_PROMPT_WIDTH = 16
BOX_INNER = 20


class Column(NamedTuple):
    header: str
    width: int
    value: Callable[[Trace], str]


class Table(NamedTuple):
    header: list[str]
    rows: list[str]


def _saved(trace: Trace) -> str:
    return "n/a" if trace.saved_pct is None else f"{trace.saved_pct:.1f}%"


COLUMNS = [
    Column("Spans", 5, lambda t: str(len(t.spans))),
    Column("Models", 12, lambda t: t.model),
    Column("Latency", 8, lambda t: f"{t.latency_ms / 1000:.2f}s"),
    Column("Tokens", 7, lambda t: f"{t.tokens:,}"),
    Column("Cost", 10, lambda t: f"${t.cost:.6f}"),
    Column("Saved", 6, _saved),
]


def _fit(text: str, width: int) -> str:
    if len(text) > width:
        text = text[: width - 1] + "…"
    return f"{text:<{width}}"


def _row(cells: list[str], widths: list[int]) -> str:
    return SEP.join(_fit(cell, width) for cell, width in zip(cells, widths))


def table(traces: list[Trace], width: int) -> Table:
    """Header lines and one row per trace, sized to fit `width` columns."""
    gaps = len(SEP) * len(COLUMNS)
    prompt_width = max(MIN_PROMPT_WIDTH, width - sum(c.width for c in COLUMNS) - gaps)
    widths = [prompt_width, *(c.width for c in COLUMNS)]
    header = _row(["Input", *(c.header for c in COLUMNS)], widths)
    rule = "─" * (sum(widths) + gaps)
    rows = [_row([t.prompt, *(c.value(t) for c in COLUMNS)], widths) for t in traces]
    return Table([header, rule], rows)


def summary(trace: Trace) -> list[str]:
    details = (
        f"{len(trace.spans)} spans · {trace.start} · "
        f"{trace.latency_ms / 1000:.2f}s · {trace.tokens:,} tokens · ${trace.cost:.6f}"
    )
    return [trace.prompt, details]


def graph(trace: Trace) -> list[str]:
    """Each span as a box, indented by its depth."""
    border = "─" * (BOX_INNER + 2)
    lines: list[str] = []
    for span in trace.spans:
        indent = INDENT * span.depth
        lines += [
            f"{indent}╭{border}╮",
            f"{indent}│ {_fit(span.name, BOX_INNER)} │",
            f"{indent}│ {_fit(span.detail, BOX_INNER)} │",
            f"{indent}╰{border}╯",
        ]
    return lines


def tree(trace: Trace) -> list[str]:
    """Each span as one indented line."""
    return [f"{INDENT * s.depth}├── {s.name} · {s.detail}" for s in trace.spans]
