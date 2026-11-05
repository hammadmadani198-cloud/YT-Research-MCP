import json

from youtube_niche_mcp.cli import main


def test_config_check_redacts_key(monkeypatch, capsys):
    monkeypatch.setenv("YOUTUBE_API_KEY", "fixture-secret")
    assert main(["config", "check"]) == 0
    output = capsys.readouterr()
    assert "fixture-secret" not in output.out + output.err
    assert json.loads(output.out)["youtube_api_key_present"]


def test_cli_migrate_status_integrity_verify(tmp_path, capsys):
    path = tmp_path / "research.sqlite3"
    for args in (["migrate"], ["db", "status"], ["db", "integrity"], ["verify"]):
        assert main(["--db", str(path), *args]) == 0
        assert json.loads(capsys.readouterr().out)["ok"]


def test_cli_missing_database_is_structured_error(tmp_path, capsys):
    path = tmp_path / "missing.sqlite3"
    assert main(["--db", str(path), "db", "status"]) == 2
    output = capsys.readouterr()
    assert not json.loads(output.err)["ok"]
    assert not path.exists()


def test_cli_invalid_config_has_nonzero_exit(monkeypatch, capsys):
    monkeypatch.setenv("YTNMCP_LOG_LEVEL", "sensitive-input")
    assert main(["config", "check"]) == 2
    output = capsys.readouterr()
    assert "sensitive-input" not in output.err
    assert json.loads(output.err)["error_type"] == "ConfigurationError"


def test_cli_lists_planned_separately_from_registered(capsys):
    assert main(["tool", "list"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert sorted(result["registered_tools"]) == sorted(result["planned_tools"])
    assert result["planned_tool_count"] == len(result["planned_tools"]) == 15


def test_cli_unexpected_failure_is_structured_and_safe(monkeypatch, capsys):
    def failed(_settings):
        raise RuntimeError("sensitive-exception")

    monkeypatch.setattr("youtube_niche_mcp.cli.verify", failed)
    assert main(["verify"]) == 2
    output = capsys.readouterr()
    assert "sensitive-exception" not in output.err
    assert json.loads(output.err)["error_type"] == "RuntimeError"


def test_phase1_operational_commands_are_offline_and_noncreating(tmp_path, capsys):
    path = tmp_path / "absent" / "history.sqlite3"
    for args in (["api", "capability"], ["history", "status"], ["snapshot", "status"]):
        assert main(["--db", str(path), *args]) == 0
        assert json.loads(capsys.readouterr().out)["ok"]
    assert not path.parent.exists()
    assert main(["--db", str(path), "history", "purge-expired"]) == 2
    assert json.loads(capsys.readouterr().err)["error_type"] == "MigrationError"
    assert not path.parent.exists()
