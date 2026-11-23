"""Turns traces into lines of plain text for the observability screens."""

from __future__ import annotations

from typing import NamedTuple

from tokensguru.observability.models import Trace

SEP = " "
INDENT = "    "
MIN_PROMPT_WIDTH = 16
BOX_INNER = 20
GAUGE_CELLS = 4
FULL_CELL = "█"
EMPTY_CELL = "░"
# (header, width) for the columns after the prompt. Each cell is built in _cells().
METRIC_COLUMNS = [
    ("Models", 12),
    ("Latency", 8),
    ("Tokens", 10),
    ("Cost", 10),
    ("Saved", 10),
]


class Table(NamedTuple):
    header: list[str]
    rows: list[str]


def _fit(text: str, width: int) -> str:
    if len(text) > width:
        text = text[: width - 1] + "…"
    return f"{text:<{width}}"


def _row(cells: list[str], widths: list[int]) -> str:
    return SEP.join(_fit(cell, width) for cell, width in zip(cells, widths))


def _gauge(fraction: float) -> str:
    """A small bar that is filled in proportion to `fraction` (0 to 1)."""
    clamped = min(1.0, max(0.0, fraction))
    filled = round(clamped * GAUGE_CELLS)
    return FULL_CELL * filled + EMPTY_CELL * (GAUGE_CELLS - filled)


def _cells(trace: Trace, max_tokens: int) -> list[str]:
    """Metric cells for one trace. Tokens show a bar relative to the busiest trace."""
    share = trace.tokens / max_tokens if max_tokens else 0.0
    if trace.saved_pct is None:
        saved = "n/a"
    else:
        saved = f"{trace.saved_pct:4.1f}% {_gauge(trace.saved_pct / 100)}"
    return [
        trace.model,
        f"{trace.latency_ms / 1000:.2f}s",
        f"{_gauge(share)} {trace.tokens:,}",
        f"${trace.cost:.6f}",
        saved,
    ]


def table(traces: list[Trace], width: int) -> Table:
    """Header and one row per trace, sized to fit `width` columns."""
    gaps = len(SEP) * len(METRIC_COLUMNS)
    metric_width = sum(w for _, w in METRIC_COLUMNS)
    prompt_width = max(MIN_PROMPT_WIDTH, width - metric_width - gaps - len(SEP))
    widths = [prompt_width, *(w for _, w in METRIC_COLUMNS)]
    header = _row(["Input", *(name for name, _ in METRIC_COLUMNS)], widths)
    rule = "─" * (sum(widths) + gaps)
    max_tokens = max((t.tokens for t in traces), default=0)
    rows = [_row([t.prompt, *_cells(t, max_tokens)], widths) for t in traces]
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
