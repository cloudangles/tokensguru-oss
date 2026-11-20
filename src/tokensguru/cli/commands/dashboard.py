"""`tokensguru dashboard`: full-screen dashboard. Press o for observability, Ctrl+X to exit."""

from __future__ import annotations

from tokensguru.cli.commands import observability
from tokensguru.cli.screen import EXIT_KEYS, show_screen
from tokensguru.cli.style import PURPLE_BG, RED_BG

OPEN_OBSERVABILITY_KEY = "o"


def run() -> int:
    while True:
        key = show_screen(
            "TokensGuru Dashboard",
            ["This is the dashboard."],
            [("O  Observability", PURPLE_BG), ("Ctrl+X  Exit", RED_BG)],
        )
        if key in EXIT_KEYS:
            return 0
        if key == OPEN_OBSERVABILITY_KEY and observability.view():
            return 0
