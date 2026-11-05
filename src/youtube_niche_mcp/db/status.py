import sqlite3

from youtube_niche_mcp.db.migrations import validate_migrations
from youtube_niche_mcp.db.schema import SCHEMA_VERSION


def status(connection: sqlite3.Connection) -> dict:
    applied = validate_migrations(connection)
    version = applied[-1]["version"] if applied else 0
    return {
        "schema_version": version,
        "expected_schema_version": SCHEMA_VERSION,
        "migration_state": "current" if version == SCHEMA_VERSION else "pending",
        "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
        "foreign_keys": bool(connection.execute("PRAGMA foreign_keys").fetchone()[0]),
        "tables": [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ],
    }


def integrity(connection: sqlite3.Connection) -> dict:
    checks = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    violations = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
    return {
        "ok": checks == ["ok"] and not violations,
        "integrity_check": checks,
        "foreign_key_violations": violations,
    }
