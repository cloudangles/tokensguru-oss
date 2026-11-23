"""TokensGuru wordmark (from media/public/tokensguru_logo.png) and its shimmer."""

import sys
import time

from tokensguru.cli.style import BRAND, RESET, WHITE_BOLD, cursor_up

SHIMMER_WIDTH = 2
FRAME_DELAY = 0.015

LOGO = """\
   ▄               ▄
   ██              ██                                       ▄
   ██▄▄▄   ▄▄▄▄    ██   ▄▄   ▄▄▄      ▄▄▄     ▄▄▄▄▄    ▄▄▄▄ ▀  ▄    ▄▄   ▄▄▄  ▄    ▄▄
   ██▀▀▀ ▄██▀▀▀▄▄  ██ ▄██  ██▀▀▀██  ▄█▀▀▀█▄ ▄█▀▀▀▀▀  ▄██▀▀██▄  ██   ██  ██▀▀  █▀   ██
   ██    ██     ██ ██▄█▀  ██▄▄▄▄███ ██   ██ ▀██▄▄▄▄  █▀    ██  ██   ██ ██     ██   ██
   ██    ██    ▄█▀ ██▀██  ███▀▀▀▄█  ██   ██   ▀▀▀▀█▄ ██    ██  ██   ██ ██     █▄   ██
    ▀███  ▀ ████▀  ██  ▀█▄ ▀█████▀  ██   ██ ▄██████  ▀█████▀   ▀█████  ██     ▀████▀
                                                     ▄▄    ▄▄
                                                     ▀█▄▄▄▄█▀
                                                       ▀▀▀▀
"""


def _frame(lines: list[str], x: int) -> list[str]:
    rows = []
    for line in lines:
        cells = [
            f"{WHITE_BOLD if abs(i - x) <= SHIMMER_WIDTH else BRAND}{ch}"
            for i, ch in enumerate(line)
        ]
        rows.append("".join(cells) + RESET)
    return rows


def show_logo(color: bool) -> None:
    if not color:
        print(LOGO, end="")
        return
    lines = LOGO.splitlines()
    width = max(len(line) for line in lines)
    for x in range(-SHIMMER_WIDTH, width + SHIMMER_WIDTH):
        if x > -SHIMMER_WIDTH:
            print(cursor_up(len(lines)), end="")
        print("\n".join(_frame(lines, x)))
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)
