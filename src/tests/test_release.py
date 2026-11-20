from __future__ import annotations

import io
import urllib.error

import pytest

from tools import release
from tools.release import ReleaseError

CHANGELOG = """# Changelog

## [1.1.0] - 2026-12-01

### Added
- Something new.

## [1.0.0] - 2026-11-20

### Added
- The first release.
"""


def test_read_version_finds_the_version_string():
    assert release.read_version('__version__ = "1.2.3"\n') == "1.2.3"


def test_read_version_fails_when_missing():
    with pytest.raises(ReleaseError):
        release.read_version("nothing here\n")


def test_changelog_section_returns_only_that_version():
    notes = release.changelog_section(CHANGELOG, "1.1.0")
    assert "Something new." in notes
    assert "first release" not in notes


def test_changelog_section_for_last_version_runs_to_end():
    assert "first release" in release.changelog_section(CHANGELOG, "1.0.0")


def test_changelog_section_fails_for_unknown_version():
    with pytest.raises(ReleaseError):
        release.changelog_section(CHANGELOG, "9.9.9")


def test_decide_skips_a_version_already_on_pypi():
    assert release.decide("1.0.0", {"1.0.0"}, CHANGELOG) == "skip"


def test_decide_publishes_a_new_version_with_a_changelog_entry():
    assert release.decide("1.1.0", {"1.0.0"}, CHANGELOG) == "publish"


def test_decide_publishes_the_first_release():
    assert release.decide("1.0.0", None, CHANGELOG) == "publish"
    assert release.decide("1.0.0", set(), CHANGELOG) == "publish"


def test_decide_refuses_a_new_version_without_changelog_entry():
    with pytest.raises(ReleaseError, match="CHANGELOG"):
        release.decide("1.2.0", {"1.0.0"}, CHANGELOG)


def test_decide_refuses_a_version_older_than_the_newest_release():
    with pytest.raises(ReleaseError, match="older"):
        release.decide("1.0.0", {"1.1.0"}, CHANGELOG)


def test_decide_allows_pre_releases_ahead_of_the_newest():
    changelog = CHANGELOG + "\n## [1.2.0rc1] - 2026-12-10\n\n- Candidate.\n"
    assert release.decide("1.2.0rc1", {"1.1.0"}, changelog) == "publish"


def test_fetch_returns_none_for_a_project_that_does_not_exist(monkeypatch):
    def not_found(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())

    monkeypatch.setattr(release.urllib.request, "urlopen", not_found)
    assert release.fetch_pypi_versions("tokensguru") is None


def test_fetch_reads_release_names(monkeypatch):
    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    body = b'{"releases": {"1.0.0": [], "1.1.0": []}}'
    monkeypatch.setattr(
        release.urllib.request, "urlopen", lambda url, timeout: Response(body)
    )
    assert release.fetch_pypi_versions("tokensguru") == {"1.0.0", "1.1.0"}


def test_fetch_reraises_other_http_errors(monkeypatch):
    def server_error(url, timeout):
        raise urllib.error.HTTPError(url, 500, "Oops", {}, io.BytesIO())

    monkeypatch.setattr(release.urllib.request, "urlopen", server_error)
    with pytest.raises(urllib.error.HTTPError):
        release.fetch_pypi_versions("tokensguru")
