from __future__ import annotations

import runpy
import sys
from importlib import metadata

import pytest

from tokensguru.cli import banner, screen
from tokensguru.cli.commands import dashboard, info, observability, version
from tokensguru.cli.main import main
from tokensguru.cli.screen import CTRL_X
from tokensguru.observability.models import Span, Trace

SPANS = (
    Span("User input", 0, "", 0),
    Span("LLM call", 0, "", 120),
    Span("output guard", 1, "applied", 0),
)


def _trace(prompt: str) -> Trace:
    return Trace(
        id="0123456789abcdef",
        prompt=prompt,
        model="test-model",
        start="Jan 1, 12:00:00 PM",
        latency_ms=1000,
        tokens=10,
        cost=0.001,
        saved_pct=50.0,
        spans=SPANS,
    )


class ScriptedScreen:
    """Stands in for a real terminal: returns the keys it is given, in order."""

    interactive = True
    size = (100, 30)

    def __init__(self, keys: list[str]) -> None:
        self.keys = list(keys)
        self.frames: list[tuple[str, list[str]]] = []

    def ask(self, title: str, body: list[str], buttons: list[screen.Button]) -> str:
        self.frames.append((title, body))
        return self.keys.pop(0)


def test_version_command_prints_version_and_runtime(capsys):
    assert version.run() == 0
    out = capsys.readouterr().out
    assert out.startswith("tokensguru ")
    assert "Python" in out


def test_info_fallbacks_when_package_metadata_is_missing(monkeypatch):
    def missing(name):
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(info.metadata, "metadata", missing)
    assert info._package_field("Summary") == "unknown"


def test_info_shortens_paths_under_home(monkeypatch, tmp_path):
    monkeypatch.setattr(info.Path, "home", classmethod(lambda cls: tmp_path))
    assert info._short_path(tmp_path / "project" / "pkg") == "~/project/pkg"
    assert info._short_path(tmp_path.parent / "elsewhere") == str(
        tmp_path.parent / "elsewhere"
    )


def test_info_run_prints_table(capsys):
    assert info.run() == 0
    out = capsys.readouterr().out
    assert "Requires Python" in out
    assert "tokensguru" in out


def test_banner_plain_output_has_no_escape_codes(capsys):
    banner.show_logo(False)
    assert "\x1b[" not in capsys.readouterr().out


def test_banner_animates_with_colour(monkeypatch, capsys):
    monkeypatch.setattr(banner.time, "sleep", lambda s: None)
    banner.show_logo(True)
    out = capsys.readouterr().out
    assert banner.PURPLE in out
    assert "\x1b[10A" in out  # cursor moves back up between frames


def test_dashboard_opens_observability_then_exits(monkeypatch):
    keys = iter(["x", "o", CTRL_X])
    monkeypatch.setattr(dashboard, "show_screen", lambda *a: next(keys))
    monkeypatch.setattr(observability, "view", lambda: "b")
    assert dashboard.run() == 0


def test_dashboard_exits_when_observability_asks_to_exit(monkeypatch):
    keys = iter(["o"])
    monkeypatch.setattr(dashboard, "show_screen", lambda *a: next(keys))
    monkeypatch.setattr(observability, "view", lambda: CTRL_X)
    assert dashboard.run() == 0


def test_observability_list_moves_selection_and_opens_detail(monkeypatch):
    monkeypatch.setattr(
        observability.store, "list_traces", lambda: [_trace("first"), _trace("second")]
    )
    fake = ScriptedScreen(["\x1b[B", "\r", "t", "b", "b"])
    assert observability._list(fake) == "b"
    titles = [title for title, _ in fake.frames]
    assert titles[0] == observability.TITLE
    assert any(title.startswith("Trace ") for title in titles)


def test_observability_list_ignores_selection_keys_when_empty(monkeypatch):
    monkeypatch.setattr(observability.store, "list_traces", lambda: [])
    fake = ScriptedScreen(["\x1b[B", "\r", CTRL_X])
    assert observability._list(fake) == CTRL_X
    assert observability.NO_TRACES in fake.frames[0][1]


def test_observability_detail_scrolls_and_switches_views(monkeypatch):
    trace = _trace("first")
    fake = ScriptedScreen(["\x1b[B", "\x1b[A", "g", "\x1b[A", "b"])
    assert observability._detail(fake, trace) == "b"
    assert len(fake.frames) == 5


def test_observability_detail_exit_key_propagates(monkeypatch):
    fake = ScriptedScreen([CTRL_X])
    assert observability._detail(fake, _trace("first")) == CTRL_X


def test_observability_exit_from_detail_returns_from_list(monkeypatch):
    monkeypatch.setattr(observability.store, "list_traces", lambda: [_trace("first")])
    fake = ScriptedScreen(["\r", CTRL_X])
    assert observability._list(fake) == CTRL_X


def test_observability_view_reports_exit_when_not_a_terminal(capsys):
    assert observability.view() is True
    assert observability.run() == 0


def test_module_entry_point_runs_version(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tokensguru", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tokensguru", run_name="__main__")
    assert exc.value.code == 0
    assert "tokensguru" in capsys.readouterr().out


def test_main_runs_info_through_registry(capsys):
    assert main(["info"]) == 0
    assert "Requires Python" in capsys.readouterr().out
