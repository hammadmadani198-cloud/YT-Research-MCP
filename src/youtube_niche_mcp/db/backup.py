"""Explicit administrative SQLite data backup, separate from source bundles."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path


def backup_database(source_path: Path, destination_path: Path) -> dict:
    source_path, destination_path = source_path.resolve(), destination_path.resolve()
    if not source_path.is_file() or source_path == destination_path:
        raise ValueError("Existing source and a distinct new destination are required")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidentally overwriting a research database or backup.
    descriptor = os.open(destination_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    with (
        closing(sqlite3.connect(f"{source_path.as_uri()}?mode=ro", uri=True)) as source,
        closing(sqlite3.connect(destination_path)) as destination,
    ):
        source.backup(destination)
        checks = [r[0] for r in destination.execute("PRAGMA integrity_check")]
        foreign_keys = destination.execute("PRAGMA foreign_key_check").fetchall()
        if checks != ["ok"] or foreign_keys:
            raise ValueError("Backup integrity verification failed; keep the original source")
        tables = destination.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
    return {"ok": True, "integrity": "ok", "foreign_key_violations": 0, "tables": tables}
