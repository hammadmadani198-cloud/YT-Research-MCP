import sqlite3

import pytest

from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import (
    MigrationError,
    applied_migrations,
    migrate,
    validate_migrations,
)
from youtube_niche_mcp.db.schema import MIGRATIONS, Migration
from youtube_niche_mcp.db.status import integrity, status


def test_initialize_and_migrate_idempotently(tmp_path):
    path = tmp_path / "nested" / "research.sqlite3"
    with connect(path) as connection:
        assert migrate(connection) == [1, 2, 3, 4, 5, 6, 7]
        before = [tuple(row) for row in applied_migrations(connection)]
        assert migrate(connection) == []
        assert [tuple(row) for row in applied_migrations(connection)] == before
        assert status(connection)["migration_state"] == "current"
        assert status(connection)["foreign_keys"]
        assert status(connection)["journal_mode"] == "wal"
        assert {"app_metadata", "schema_migrations", "source_records", "videos"} <= set(
            status(connection)["tables"]
        )
        assert integrity(connection)["ok"]


def test_readonly_never_creates_parent_or_db(tmp_path):
    path = tmp_path / "absent" / "research.sqlite3"
    with pytest.raises(sqlite3.OperationalError), connect(path, read_only=True):
        pass
    assert not path.parent.exists()


def test_readonly_prohibits_writes(tmp_path):
    path = tmp_path / "research.sqlite3"
    with connect(path) as connection:
        migrate(connection)
    with connect(path, read_only=True) as connection, pytest.raises(sqlite3.OperationalError):
        connection.execute("INSERT INTO app_metadata VALUES ('bad', 'bad')")


def test_failed_batch_rolls_back_all_schema_and_versions(tmp_path):
    bad = Migration(8, "broken", ("CREATE TABLE temporary_test (id INTEGER)", "INVALID SQL"))
    with connect(tmp_path / "research.sqlite3") as connection:
        with pytest.raises(sqlite3.OperationalError):
            migrate(connection, (*MIGRATIONS, bad))
        assert applied_migrations(connection) == []
        assert (
            connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
        )
        assert migrate(connection) == [1, 2, 3, 4, 5, 6, 7]


def test_checksum_tampering_refused(tmp_path):
    with connect(tmp_path / "research.sqlite3") as connection:
        migrate(connection)
        connection.execute("UPDATE schema_migrations SET checksum='changed'")
        connection.commit()
        with pytest.raises(MigrationError, match="checksum"):
            migrate(connection)


def test_future_schema_refused(tmp_path):
    second = Migration(8, "next", ("CREATE TABLE next_phase (id INTEGER)",))
    with connect(tmp_path / "research.sqlite3") as connection:
        migrate(connection, (*MIGRATIONS, second))
        with pytest.raises(MigrationError, match="newer"):
            migrate(connection)


def test_definition_gaps_refused(tmp_path):
    bad = Migration(9, "gap", ("CREATE TABLE gap (id INTEGER)",))
    with (
        connect(tmp_path / "research.sqlite3") as connection,
        pytest.raises(MigrationError, match="contiguous"),
    ):
        migrate(connection, (*MIGRATIONS, bad))


def test_applied_history_gap_refused(tmp_path):
    with connect(tmp_path / "research.sqlite3") as connection:
        migrate(connection)
        connection.execute("UPDATE schema_migrations SET version=9 WHERE version=1")
        connection.commit()
        with pytest.raises(MigrationError, match="gaps"):
            validate_migrations(connection)


def test_unrelated_unversioned_database_not_overwritten(tmp_path):
    with connect(tmp_path / "unrelated.sqlite3") as connection:
        connection.execute("CREATE TABLE unrelated (id INTEGER)")
        connection.commit()
        with pytest.raises(MigrationError, match="nonempty"):
            migrate(connection)
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()[
            0
        ] == ("unrelated")


def test_integrity_detects_foreign_key_violation(tmp_path):
    with connect(tmp_path / "research.sqlite3") as connection:
        migrate(connection)
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))")
        connection.commit()
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("INSERT INTO child VALUES (999)")
        connection.commit()
        connection.execute("PRAGMA foreign_keys=ON")
        result = integrity(connection)
        assert not result["ok"]
        assert len(result["foreign_key_violations"]) == 1
