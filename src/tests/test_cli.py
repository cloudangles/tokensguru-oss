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


def test_help_lists_the_docs_command(capsys):
    assert main([]) == 0
    assert "docs" in capsys.readouterr().out


def test_docs_command_starts_the_server(monkeypatch):
    seen = {}

    def fake_serve(port=None, open_browser=True):
        seen.update(port=port, open_browser=open_browser)
        return 0

    monkeypatch.setattr("tokensguru.cli.commands.docs.serve", fake_serve)
    assert main(["docs"]) == 0
    assert seen == {"port": None, "open_browser": True}
    assert main(["docs", "--port", "9100", "--no-open"]) == 0
    assert seen == {"port": 9100, "open_browser": False}


def test_docs_command_reports_a_port_that_cannot_be_used(monkeypatch, capsys):
    def fake_serve(port=None, open_browser=True):
        raise OSError("Address already in use")

    monkeypatch.setattr("tokensguru.cli.commands.docs.serve", fake_serve)
    assert main(["docs", "--port", "9100"]) == 1
    assert "Address already in use" in capsys.readouterr().err


@pytest.mark.parametrize("port", ["abc", "-1", "70000", "1.5", ""])
def test_docs_command_rejects_a_bad_port(port, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["docs", "--port", port])
    assert exc.value.code == 2
    assert "port" in capsys.readouterr().err
