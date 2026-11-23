"""`tokensguru docs`: start the local docs site and open it in your browser."""

from __future__ import annotations

import argparse
import sys

from tokensguru.server import serve

MAX_PORT = 65535


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a port number") from None
    if not 0 <= port <= MAX_PORT:
        raise argparse.ArgumentTypeError(f"the port must be between 0 and {MAX_PORT}")
    return port


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--port",
        type=_port,
        default=None,
        help="port to listen on (default: 8765, or a free port if it is busy)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="start the server without opening a browser",
    )


def run(args: argparse.Namespace) -> int:
    try:
        return serve(port=args.port, open_browser=not args.no_open)
    except OSError as error:
        print(f"Could not start the docs server: {error}", file=sys.stderr)
        return 1
