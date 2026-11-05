"""Mutable local watch intent, deliberately separate from append-only evidence."""

WATCH_SQL = (
    """CREATE TABLE research_watches (
        watch_id TEXT PRIMARY KEY,
        watch_type TEXT NOT NULL CHECK(watch_type IN ('niche','competitor')),
        subject_json TEXT NOT NULL,
        profile_json TEXT NOT NULL,
        enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
        revision INTEGER NOT NULL CHECK(revision >= 1),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_checked_at TEXT CHECK(last_checked_at IS NULL),
        owner_context TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        CHECK(created_at <= updated_at AND updated_at < expires_at))""",
    "CREATE INDEX watch_owner_type ON research_watches(owner_context,watch_type,watch_id)",
)
