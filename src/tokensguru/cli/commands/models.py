"""`tokensguru models`: see which guardrail models are saved, or save them now."""

# ruff: noqa: E501
from __future__ import annotations

import argparse

from tokensguru.governance import models


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "action",
        nargs="?",
        choices=("status", "download"),
        default="status",
        help="status shows what is saved on this machine, download saves the models",
    )


def run(args: argparse.Namespace) -> int:
    if args.action == "download":
        print(
            "Downloading the guardrail models. This happens once; they are then kept on this machine."
        )
        rows = models.download()
    else:
        rows = models.status()
    for row in rows:
        mark = "saved" if row["saved"] else "not saved yet"
        print(f"  {row['guardrail']:<28} {row['model']}  [{mark}]")
        if row.get("error"):
            print(f"    {row['error']}")
    if args.action == "status" and not all(row["saved"] for row in rows):
        print(
            "They are downloaded automatically the first time they are needed, or run: tokensguru models download"
        )
    return 0 if all(row["saved"] for row in rows) or args.action == "status" else 1
