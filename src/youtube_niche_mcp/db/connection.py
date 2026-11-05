import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(
    path: Path, *, read_only: bool = False, timeout: float = 10
) -> Iterator[sqlite3.Connection]:
    """Writes are opt-in. Read-only access never creates a database or its parent."""
    path = path.resolve()
    if read_only:
        connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=timeout)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=timeout)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")
        if read_only:
            connection.execute("PRAGMA query_only = ON")
        else:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
        yield connection
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
