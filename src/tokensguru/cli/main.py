"""Command-line entry point: registers the commands and runs the chosen one."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from tokensguru import __version__
from tokensguru.cli.commands import docs, info, models, version

PROG = "tokensguru"

Run = Callable[[argparse.Namespace], int]
AddArguments = Callable[[argparse.ArgumentParser], None]


def _without_options(command: Callable[[], int]) -> Run:
    def run(args: argparse.Namespace) -> int:
        del args
        return command()

    return run


# (name, help text, function that runs it, function that adds its options or None)
COMMANDS: list[tuple[str, str, Run, AddArguments | None]] = [
    ("version", "Show version information", _without_options(version.run), None),
    ("info", "Show package information", _without_options(info.run), None),
    (
        "docs",
        "Open the docs and playground in your browser",
        docs.run,
        docs.add_arguments,
    ),
    (
        "models",
        "Show or download the models the guardrails use",
        models.run,
        models.add_arguments,
    ),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG, description="Reduce LLM token usage and cost."
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    parser.set_defaults(run=None)

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for name, help_text, run, add_arguments in COMMANDS:
        subparser = subparsers.add_parser(name, help=help_text)
        subparser.set_defaults(run=run)
        if add_arguments is not None:
            add_arguments(subparser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.run is None:
        parser.print_help()
        return 0
    exit_code: int = args.run(args)
    return exit_code
