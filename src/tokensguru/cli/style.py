"""Terminal colours and styles (ANSI escape codes) shared by every screen."""

import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
REVERSE = "\033[7m"
PURPLE = "\033[38;5;98m"
PURPLE_BG = "\033[48;5;98m"
RED_BG = "\033[48;5;160m"
WHITE_BOLD = "\033[1;38;5;231m"


def use_color() -> bool:
    """Colour only when writing to a terminal and NO_COLOR is not set."""
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def cursor_up(lines: int) -> str:
    """Escape code that moves the cursor up by `lines` rows."""
    return f"\033[{lines}A"
