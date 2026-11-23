import pytest

from tokensguru import __version__
from tokensguru.cli.main import main


def test_version_flag_prints_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"tokensguru {__version__}"


def test_version_command_prints_version(capsys):
    assert main(["version"]) == 0
    assert f"tokensguru {__version__}" in capsys.readouterr().out


def test_info_command_prints_package_details(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "tokensguru" in out
    assert __version__ in out


def test_no_arguments_prints_help(capsys):
    assert main([]) == 0
    assert "usage: tokensguru" in capsys.readouterr().out


def test_help_lists_commands(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "version" in out
    assert "info" in out
