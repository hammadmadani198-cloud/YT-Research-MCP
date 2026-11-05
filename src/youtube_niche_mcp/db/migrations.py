import sqlite3
from datetime import UTC, datetime

from youtube_niche_mcp.db.schema import MIGRATIONS, Migration


class MigrationError(ValueError):
    """Unknown, changed, missing, or unordered migrations require review."""


def applied_migrations(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if not exists:
        return []
    return connection.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()


def validate_migrations(
    connection: sqlite3.Connection, migrations: tuple[Migration, ...] = MIGRATIONS
) -> list[sqlite3.Row]:
    if [m.version for m in migrations] != list(range(1, len(migrations) + 1)):
        raise MigrationError("Migration definitions must be contiguous from version 1")
    applied = applied_migrations(connection)
    if [row["version"] for row in applied] != list(range(1, len(applied) + 1)):
        raise MigrationError("Applied migration history has gaps")
    if len(applied) > len(migrations):
        raise MigrationError("Database schema is newer than this application")
    for row, migration in zip(applied, migrations, strict=False):
        if row["checksum"] != migration.checksum or row["name"] != migration.name:
            raise MigrationError("Applied migration checksum/name differs from this application")
    return applied


def migrate(
    connection: sqlite3.Connection, migrations: tuple[Migration, ...] = MIGRATIONS
) -> list[int]:
    """Atomic across the pending batch; transaction lock serializes concurrent starts."""
    if connection.in_transaction:
        raise MigrationError("Migration requires a connection without an active transaction")
    connection.execute("BEGIN IMMEDIATE")
    try:
        applied = validate_migrations(connection, migrations)
        if not applied:
            unrelated = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if unrelated:
                raise MigrationError("Refusing to initialize an unversioned nonempty database")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY CHECK (version > 0),
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )"""
        )
        installed = []
        for migration in migrations[len(applied) :]:
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (?, ?, ?, ?)",
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    datetime.now(UTC).isoformat(),
                ),
            )
            installed.append(migration.version)
        connection.commit()
        return installed
    except BaseException:
        connection.rollback()
        raise
