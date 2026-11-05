from contextlib import contextmanager
from uuid import uuid4


@contextmanager
def atomic(connection):
    """Nested savepoints keep collector outcomes and their observations atomic."""
    name = "capture_" + uuid4().hex
    connection.execute(f"SAVEPOINT {name}")
    try:
        yield
    except BaseException:
        connection.execute(f"ROLLBACK TO {name}")
        connection.execute(f"RELEASE {name}")
        raise
    else:
        connection.execute(f"RELEASE {name}")
