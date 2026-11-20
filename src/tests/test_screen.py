from __future__ import annotations

import io

import pytest

from tokensguru.cli import screen
from tokensguru.cli.screen import CTRL_X, Screen, _center, _frame, show_screen
from tokensguru.cli.style import RED_BG


def test_center_pads_visible_text_and_ignores_colour_codes():
    text = "\x1b[1mhi\x1b[0m"
    centred = _center(text, 6)
    assert len(centred) == len(text) + 4  # 2 spaces each side, colours untouched
    assert centred.strip() == text


def test_frame_has_double_border_and_fills_size():
    frame = _frame("Title", ["body"], [("Exit", "")], False, (40, 10))
    assert len(frame) == 10
    assert frame[0] == "╔" + "═" * 38 + "╗"
    assert frame[-1] == "╚" + "═" * 38 + "╝"
    assert all(len(line) == 40 for line in frame)


def test_frame_without_colour_shows_bracketed_buttons():
    frame = "\n".join(_frame("T", [], [("Go", "")], False, (40, 10)))
    assert "[ Go ]" in frame


def test_non_interactive_screen_prints_once_and_asks_to_exit(capsys, monkeypatch):
    monkeypatch.setattr(screen.sys, "stdin", io.StringIO())
    s = Screen()
    assert s.interactive is False
    assert s.size == (80, 24)
    assert s.ask("Hello", ["line"], [("Exit", "")]) == CTRL_X
    assert "Hello" in capsys.readouterr().out


def test_show_screen_returns_the_key_from_a_screen(monkeypatch, capsys):
    monkeypatch.setattr(screen.Screen, "ask", lambda self, t, b, k: "o")
    assert show_screen("T", [], []) == "o"


def test_interactive_ask_writes_frame_and_reads_key(monkeypatch):
    out = io.StringIO()
    monkeypatch.setattr(screen.sys, "stdout", out)
    monkeypatch.setattr(screen, "_read_key", lambda: "q")
    s = Screen()
    s.interactive = True
    monkeypatch.setattr(screen.shutil, "get_terminal_size", lambda fallback: (50, 12))
    assert s.size == (50, 12)
    assert s.ask("T", ["x"], [("Exit", RED_BG)]) == "q"
    assert out.getvalue().startswith(screen.CURSOR_HOME + "╔")


def test_open_screen_enters_and_leaves_alternate_buffer(monkeypatch):
    out = io.StringIO()
    monkeypatch.setattr(screen.sys, "stdout", out)
    monkeypatch.setattr(
        screen.Screen, "__init__", lambda self: setattr(self, "interactive", True)
    )
    with screen.open_screen() as s:
        assert s.interactive is True
    written = out.getvalue()
    assert written.startswith(screen.ENTER_SCREEN)
    assert written.endswith(screen.LEAVE_SCREEN)


class _FakeTermios:
    TCSADRAIN = 1

    def tcgetattr(self, fd):
        return "saved"

    def tcsetattr(self, fd, when, attrs):
        self.restored = attrs


class _FakeTty:
    @staticmethod
    def setraw(fd: int) -> None:  # noqa: ARG004 - signature matches tty.setraw
        return None


@pytest.fixture
def fake_terminal(monkeypatch):
    fake = _FakeTermios()
    monkeypatch.setattr(screen, "termios", fake, raising=False)
    monkeypatch.setattr(screen, "tty", _FakeTty, raising=False)
    monkeypatch.setattr(
        screen.sys, "stdin", io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    )
    return fake


def test_read_key_returns_plain_key_and_restores_terminal(fake_terminal, monkeypatch):
    monkeypatch.setattr(screen.os, "read", lambda fd, n: b"o")
    monkeypatch.setattr(screen.sys.stdin, "fileno", lambda: 0, raising=False)
    assert screen._read_key() == "o"
    assert fake_terminal.restored == "saved"


def test_read_key_joins_arrow_key_sequence(fake_terminal, monkeypatch):
    chunks = iter([b"\x1b", b"[A"])
    monkeypatch.setattr(screen.os, "read", lambda fd, n: next(chunks))
    monkeypatch.setattr(screen.select, "select", lambda r, w, x, t: (r, [], []))
    monkeypatch.setattr(screen.sys.stdin, "fileno", lambda: 0, raising=False)
    assert screen._read_key() == "\x1b[A"


def test_read_key_lone_escape_does_not_wait_for_more(fake_terminal, monkeypatch):
    monkeypatch.setattr(screen.os, "read", lambda fd, n: b"\x1b")
    monkeypatch.setattr(screen.select, "select", lambda r, w, x, t: ([], [], []))
    monkeypatch.setattr(screen.sys.stdin, "fileno", lambda: 0, raising=False)
    assert screen._read_key() == "\x1b"
