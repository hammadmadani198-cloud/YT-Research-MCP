"""One append-only table for structured reviews; reuse existing analysis storage."""

QUALITATIVE_SQL = (
    """CREATE TABLE qualitative_annotations (
        annotation_id TEXT PRIMARY KEY, version TEXT NOT NULL,
        available_at TEXT NOT NULL, decided_at TEXT NOT NULL, expires_at TEXT NOT NULL,
        input_hash TEXT NOT NULL, annotation_json TEXT NOT NULL,
        CHECK(available_at<=decided_at AND decided_at<expires_at))""",
    "CREATE INDEX qualitative_expiry ON qualitative_annotations(expires_at)",
    """CREATE TRIGGER immutable_qualitative_annotations BEFORE UPDATE ON qualitative_annotations
       BEGIN SELECT RAISE(ABORT, 'Append-only qualitative evidence cannot be updated'); END""",
    "UPDATE app_metadata SET value='phase_5_qualitative' WHERE key='schema_scope'",
)
