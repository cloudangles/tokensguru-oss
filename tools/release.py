"""Release helper used by the publish workflow.

Reads the package version, decides whether it should be published, and extracts
the release notes for a version from CHANGELOG.md.

Usage:
    python tools/release.py check            # sets action/version for GitHub Actions
    python tools/release.py notes VERSION    # prints the changelog section
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "src" / "tokensguru" / "version.py"
CHANGELOG = ROOT / "CHANGELOG.md"
PACKAGE = "tokensguru"
PYPI_JSON = "https://pypi.org/pypi/{package}/json"
HTTP_NOT_FOUND = 404
NOTES_ARGUMENT_COUNT = 2


class ReleaseError(Exception):
    """The release cannot proceed. The message says why."""


def read_version(text: str) -> str:
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise ReleaseError("__version__ is not set in src/tokensguru/version.py")
    return match.group(1)


def fetch_pypi_versions(package: str) -> set[str] | None:
    """Versions already on PyPI, or None if the project does not exist yet."""
    try:
        url = PYPI_JSON.format(package=package)  # fixed https URL, not user input
        with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310
            data = json.load(r)
    except urllib.error.HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            return None
        raise
    return set(data["releases"])


def changelog_section(changelog: str, version: str) -> str:
    """The text under '## [version]' up to the next version heading."""
    heading = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n", changelog, re.MULTILINE
    )
    if heading is None:
        raise ReleaseError(f"CHANGELOG.md has no '## [{version}]' entry")
    rest = changelog[heading.end() :]
    following = re.search(r"^## \[", rest, re.MULTILINE)
    body = rest[: following.start()] if following else rest
    return body.strip() + "\n"


def decide(version: str, published: set[str] | None, changelog: str) -> str:
    """Return 'skip' if this version is already on PyPI, otherwise 'publish'.

    Raises ReleaseError for a new version that would not be the newest release,
    or that has no changelog entry.
    """
    if published is not None and version in published:
        return "skip"
    if published:
        newest = max(Version(v) for v in published)
        if Version(version) < newest:
            raise ReleaseError(
                f"{version} is older than the newest release on PyPI ({newest})"
            )
    changelog_section(changelog, version)  # raises if the entry is missing
    return "publish"


def _write_outputs(values: dict[str, str]) -> None:
    lines = "".join(f"{key}={value}\n" for key, value in values.items())
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(lines)
    else:
        sys.stdout.write(lines)


def _write_summary(text: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")


def cmd_check() -> int:
    version = read_version(VERSION_FILE.read_text(encoding="utf-8"))
    changelog = CHANGELOG.read_text(encoding="utf-8")
    action = decide(version, fetch_pypi_versions(PACKAGE), changelog)
    _write_outputs({"version": version, "action": action})
    if action == "skip":
        _write_summary(f"Version {version} is already on PyPI. Nothing to publish.")
    else:
        _write_summary(f"Version {version} is new. It will be published to PyPI.")
    return 0


def cmd_notes(version: str) -> int:
    changelog = CHANGELOG.read_text(encoding="utf-8")
    sys.stdout.write(changelog_section(changelog, version))
    return 0


def main(argv: list[str]) -> int:
    try:
        if argv == ["check"]:
            return cmd_check()
        if len(argv) == NOTES_ARGUMENT_COUNT and argv[0] == "notes":
            return cmd_notes(argv[1])
    except ReleaseError as error:
        sys.stdout.write(f"::error::{error}\n")
        return 1
    sys.stdout.write(__doc__ or "")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
