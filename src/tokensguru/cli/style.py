"""Terminal colours and styles (ANSI escape codes) shared by the commands."""

import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
# Brand gold, hsla(42, 100%, 40%, 1) = rgb(204, 143, 0), as a 24-bit colour code.
BRAND = "\033[38;2;204;143;0m"
WHITE_BOLD = "\033[1;38;5;231m"


def use_color() -> bool:
    """Colour only when writing to a terminal and NO_COLOR is not set."""
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def cursor_up(lines: int) -> str:
    """Escape code that moves the cursor up by `lines` rows."""
    return f"\033[{lines}A"
