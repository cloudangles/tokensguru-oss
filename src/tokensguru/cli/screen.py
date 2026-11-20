"""Shared full-screen view: double-border frame, coloured buttons, one key."""

from __future__ import annotations

import os
import re
import select
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager

from tokensguru.cli.style import BOLD, PURPLE, RESET, WHITE_BOLD, use_color

try:
    import termios
    import tty
except ImportError:  # Windows: no raw key input, so screens are only printed
    termios = None  # type: ignore[assignment]

ENTER_SCREEN = "\033[?1049h\033[2J\033[H"  # alternate buffer, clear, home
LEAVE_SCREEN = "\033[?1049l"
CURSOR_HOME = "\033[H"

CTRL_X = "\x18"
CTRL_C = "\x03"
EXIT_KEYS = (CTRL_X, CTRL_C)
UP_KEYS = ("\x1b[A", "k")
DOWN_KEYS = ("\x1b[B", "j")
ENTER_KEYS = ("\r", "\n")

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
FALLBACK_SIZE = (80, 24)

Button = tuple[str, str]  # (label, background colour code)


def _read_key() -> str:
    """Read one key. Arrow keys arrive as three bytes and are returned whole."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = os.read(fd, 1)
        if key == b"\x1b" and select.select([fd], [], [], 0.05)[0]:
            key += os.read(fd, 2)
        return key.decode(errors="ignore")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _center(text: str, width: int) -> str:
    visible = len(ANSI.sub("", text))
    left = max(0, (width - visible) // 2)
    return " " * left + text + " " * max(0, width - visible - left)


def _frame(
    title: str,
    body: list[str],
    buttons: list[Button],
    color: bool,
    size: tuple[int, int],
) -> list[str]:
    cols, rows = size
    inner = cols - 2
    height = rows - 2
    if color:
        button_row = "   ".join(
            f"{bg}{WHITE_BOLD}  {label}  {RESET}" for label, bg in buttons
        )
        title_line = f"{BOLD}{PURPLE}{title}{RESET}"
    else:
        button_row = "   ".join(f"[ {label} ]" for label, _ in buttons)
        title_line = title

    content = [title_line, "", *body, "", button_row]
    top_pad = max(0, (height - len(content)) // 2)
    lines = ([""] * top_pad + content + [""] * height)[:height]

    frame = ["╔" + "═" * inner + "╗"]
    frame += ["║" + _center(line, inner) + "║" for line in lines]
    frame.append("╚" + "═" * inner + "╝")
    return frame


class Screen:
    """Draws frames and reads keys while the terminal's alternate screen is open.

    Get one from `open_screen`. When keys cannot be read (piped output, no
    terminal) it prints one frame and returns CTRL_X, so callers exit instead of
    waiting forever.
    """

    def __init__(self) -> None:
        self.interactive = (
            termios is not None and sys.stdin.isatty() and sys.stdout.isatty()
        )

    @property
    def size(self) -> tuple[int, int]:
        """Terminal (columns, rows)."""
        if not self.interactive:
            return FALLBACK_SIZE
        cols, rows = shutil.get_terminal_size(FALLBACK_SIZE)
        return cols, rows

    def ask(self, title: str, body: list[str], buttons: list[Button]) -> str:
        color = self.interactive and use_color()
        frame = _frame(title, body, buttons, color, self.size)
        if not self.interactive:
            print("\n".join(frame))
            return CTRL_X
        sys.stdout.write(CURSOR_HOME + "\n".join(frame))
        sys.stdout.flush()
        return _read_key()


@contextmanager
def open_screen() -> Iterator[Screen]:
    """Take over the terminal's alternate screen for the duration of the block."""
    screen = Screen()
    if screen.interactive:
        sys.stdout.write(ENTER_SCREEN)
        sys.stdout.flush()
    try:
        yield screen
    finally:
        if screen.interactive:
            sys.stdout.write(LEAVE_SCREEN)
            sys.stdout.flush()


def show_screen(title: str, body: list[str], buttons: list[Button]) -> str:
    """Draw one screen and return the key pressed."""
    with open_screen() as screen:
        return screen.ask(title, body, buttons)
