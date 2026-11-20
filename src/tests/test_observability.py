from __future__ import annotations

from tokensguru.cli.commands import observability
from tokensguru.observability import render, store
from tokensguru.observability.models import Span, Trace

SPANS = (
    Span("User input", 0, "", 0),
    Span("LLM call", 0, "", 120),
    Span("output guard", 1, "applied", 0),
)


def _trace(prompt: str, saved_pct: float | None = 50.0) -> Trace:
    return Trace(
        id="test-trace-id",
        prompt=prompt,
        model="test-model",
        start="Jan 1, 12:00:00 PM",
        latency_ms=1000,
        tokens=10,
        cost=0.001,
        saved_pct=saved_pct,
        spans=SPANS,
    )


def test_store_has_no_traces_until_a_source_is_connected():
    assert store.list_traces() == []


def test_table_has_header_and_one_row_per_trace():
    table = render.table([_trace("first"), _trace("second")], 90)
    assert table.header[0].startswith("Input")
    assert len(table.rows) == 2


def test_table_rows_fit_the_requested_width():
    table = render.table([_trace("a very long prompt " * 10)], 74)
    assert all(len(line) <= 74 for line in [*table.header, *table.rows])


def test_table_shows_na_when_savings_are_unavailable():
    table = render.table([_trace("first", saved_pct=None)], 90)
    assert "n/a" in table.rows[0]


def test_span_detail_defaults_status_to_ok():
    assert Span("x", 0, "", 5).detail == "ok · 5ms"
    assert Span("x", 0, "applied", 5).detail == "applied · 5ms"


def test_graph_and_tree_show_every_span():
    trace = _trace("first")
    graph_text = "\n".join(render.graph(trace))
    tree_text = "\n".join(render.tree(trace))
    for span in trace.spans:
        assert span.name in graph_text
        assert span.name in tree_text


def test_observability_view_asks_to_exit_when_not_interactive(capsys):
    assert observability.view() is True
    assert "No traces yet." in capsys.readouterr().out
