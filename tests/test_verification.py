from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import applied_migrations, migrate
from youtube_niche_mcp.services.verification import verify


def test_verify_absent_db_without_persistent_changes(tmp_path):
    path = tmp_path / "missing" / "research.sqlite3"
    before = sorted(tmp_path.iterdir())
    result = verify(Settings(db_path=path))
    assert result["ok"], result
    assert sorted(tmp_path.iterdir()) == before
    assert not path.exists()
    database = next(item for item in result["checks"] if item["name"] == "database")
    assert database["detail"]["state"] == "not_initialized"


def test_verify_existing_database_does_not_change_rows_or_main_file(tmp_path):
    path = tmp_path / "research.sqlite3"
    with connect(path) as connection:
        migrate(connection)
        before_rows = [tuple(row) for row in applied_migrations(connection)]
    before_bytes = path.read_bytes()
    assert verify(Settings(db_path=path))["ok"]
    assert path.read_bytes() == before_bytes
    with connect(path, read_only=True) as connection:
        assert [tuple(row) for row in applied_migrations(connection)] == before_rows


def test_verify_pending_db_fails_without_migrating(tmp_path):
    path = tmp_path / "research.sqlite3"
    with connect(path):
        pass
    result = verify(Settings(db_path=path))
    assert not result["ok"]
    with connect(path, read_only=True) as connection:
        assert applied_migrations(connection) == []


def test_verify_tampered_db_fails(tmp_path):
    path = tmp_path / "research.sqlite3"
    with connect(path) as connection:
        migrate(connection)
        connection.execute("UPDATE schema_migrations SET checksum='bad'")
        connection.commit()
    assert not verify(Settings(db_path=path))["ok"]


def test_verify_directory_as_db_fails_safely(tmp_path):
    result = verify(Settings(db_path=tmp_path))
    assert not result["ok"]
    database = next(item for item in result["checks"] if item["name"] == "database")
    assert database["error_type"] == "OperationalError"
