"""Command-line entry point: registers the commands and runs the chosen one."""

from __future__ import annotations

import argparse

from tokensguru import __version__
from tokensguru.cli.commands import dashboard, info, observability, version

PROG = "tokensguru"

# (name, help text, function that runs it)
COMMANDS = [
    ("version", "Show version information", version.run),
    ("info", "Show package information", info.run),
    ("dashboard", "Open the full-screen dashboard", dashboard.run),
    ("observability", "Open the observability view", observability.run),
]

# (short flag, long flag, help text, function that runs it)
SHORTCUTS = [
    ("-d", "--dashboard", "open the dashboard (same as 'dashboard')", dashboard.run),
    (
        "-o",
        "--observability",
        "open observability (same as 'observability')",
        observability.run,
    ),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG, description="Reduce LLM token usage and cost."
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    for short, long, help_text, run in SHORTCUTS:
        parser.add_argument(
            short, long, dest="run", action="store_const", const=run, help=help_text
        )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for name, help_text, run in COMMANDS:
        subparsers.add_parser(name, help=help_text).set_defaults(run=run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    run = parser.parse_args(argv).run
    if run is None:
        parser.print_help()
        return 0
    exit_code: int = run()
    return exit_code
