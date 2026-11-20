"""`tokensguru info`: show the logo and package details in a table."""

from __future__ import annotations

import platform
from importlib import metadata
from pathlib import Path

import tokensguru
from tokensguru.cli.banner import show_logo
from tokensguru.cli.style import BOLD, PURPLE, RESET, use_color


def _package_field(field: str) -> str:
    try:
        return metadata.metadata("tokensguru")[field] or "unknown"
    except metadata.PackageNotFoundError:
        return "unknown"


def _short_path(path: Path) -> str:
    try:
        return f"~/{path.relative_to(Path.home()).as_posix()}"
    except ValueError:
        return str(path)


def _rows() -> list[tuple[str, str]]:
    return [
        ("Name", "tokensguru"),
        ("Version", tokensguru.__version__),
        ("Description", _package_field("Summary")),
        ("Requires Python", _package_field("Requires-Python")),
        ("Python", platform.python_version()),
        ("Platform", f"{platform.system()} {platform.machine()}"),
        ("Location", _short_path(Path(tokensguru.__file__).parent)),
    ]


def _print_table(rows: list[tuple[str, str]], color: bool) -> None:
    key_w = max(len(key) for key, _ in rows)
    val_w = max(len(val) for _, val in rows)
    key_style = f"{BOLD}{PURPLE}" if color else ""
    reset = RESET if color else ""
    print("╭" + "─" * (key_w + 2) + "┬" + "─" * (val_w + 2) + "╮")
    for key, val in rows:
        print(f"│ {key_style}{key:<{key_w}}{reset} │ {val:<{val_w}} │")
    print("╰" + "─" * (key_w + 2) + "┴" + "─" * (val_w + 2) + "╯")


def run() -> int:
    color = use_color()
    show_logo(color)
    print()
    _print_table(_rows(), color)
    return 0
