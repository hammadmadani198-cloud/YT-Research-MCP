"""Append v4; source/discovery/conflict/cache/quota/eligibility tables are reused."""

PROVIDER_SQL = (
    """CREATE TABLE provider_runs (
        run_id TEXT PRIMARY KEY, provider TEXT NOT NULL, route TEXT NOT NULL,
        fetched_at TEXT NOT NULL, available_at TEXT NOT NULL, expires_at TEXT NOT NULL,
        run_kind TEXT NOT NULL, manifest_json TEXT NOT NULL, content_hash TEXT NOT NULL)""",
    """CREATE TABLE provider_evidence (
        evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES provider_runs(run_id)
            ON DELETE CASCADE,
        source_id TEXT NOT NULL REFERENCES source_records(source_id) ON DELETE CASCADE,
        entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL, route TEXT NOT NULL,
        observed_at TEXT NOT NULL, available_at TEXT NOT NULL, expires_at TEXT NOT NULL,
        record_json TEXT NOT NULL, anomalies_json TEXT NOT NULL)""",
    """CREATE TABLE provider_quota_details (
        request_id INTEGER PRIMARY KEY REFERENCES quota_requests(request_id) ON DELETE CASCADE,
        provider TEXT NOT NULL, access_mode TEXT NOT NULL, documented_cost INTEGER,
        charged_cost INTEGER, cached_free INTEGER, http_status INTEGER,
        plan_state TEXT NOT NULL)""",
    "CREATE INDEX provider_subject ON provider_evidence(entity_kind,entity_id,available_at)",
    *(
        f"""CREATE TRIGGER immutable_{table} BEFORE UPDATE ON {table}
       BEGIN SELECT RAISE(ABORT, 'Append-only provider evidence cannot be updated'); END"""
        for table in ("provider_runs", "provider_evidence", "provider_quota_details")
    ),
    "UPDATE app_metadata SET value='phase_2_5_provider_foundation' WHERE key='schema_scope'",
)
