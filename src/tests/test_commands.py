from __future__ import annotations

import runpy
import sys
from importlib import metadata

import pytest

from tokensguru.cli import banner
from tokensguru.cli.commands import info, version
from tokensguru.cli.main import main


def test_version_command_prints_version_and_runtime(capsys):
    assert version.run() == 0
    out = capsys.readouterr().out
    assert out.startswith("tokensguru ")
    assert "Python" in out


def test_info_fallbacks_when_package_metadata_is_missing(monkeypatch):
    def missing(name):
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(info.metadata, "metadata", missing)
    assert info._package_field("Summary") == "unknown"


def test_info_shortens_paths_under_home(monkeypatch, tmp_path):
    monkeypatch.setattr(info.Path, "home", classmethod(lambda cls: tmp_path))
    assert info._short_path(tmp_path / "project" / "pkg") == "~/project/pkg"
    assert info._short_path(tmp_path.parent / "elsewhere") == str(
        tmp_path.parent / "elsewhere"
    )


def test_info_run_prints_table(capsys):
    assert info.run() == 0
    out = capsys.readouterr().out
    assert "Requires Python" in out
    assert "tokensguru" in out


def test_banner_plain_output_has_no_escape_codes(capsys):
    banner.show_logo(False)
    assert "\x1b[" not in capsys.readouterr().out


def test_banner_animates_with_colour(monkeypatch, capsys):
    monkeypatch.setattr(banner.time, "sleep", lambda s: None)
    banner.show_logo(True)
    out = capsys.readouterr().out
    assert banner.BRAND in out
    assert "\x1b[10A" in out  # cursor moves back up between frames


def test_module_entry_point_runs_version(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tokensguru", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tokensguru", run_name="__main__")
    assert exc.value.code == 0
    assert "tokensguru" in capsys.readouterr().out


def test_main_runs_info_through_registry(capsys):
    assert main(["info"]) == 0
    assert "Requires Python" in capsys.readouterr().out
