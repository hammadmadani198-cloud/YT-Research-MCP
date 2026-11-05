"""Additive schema v5; all v1-v4 statements/checksums remain frozen."""

ANALYSIS_SQL = (
    """CREATE TABLE analysis_runs (
        run_id TEXT PRIMARY KEY, cohort_id TEXT NOT NULL
            REFERENCES cohort_definitions(cohort_id) ON DELETE CASCADE,
        video_cohort_id TEXT NOT NULL REFERENCES cohort_definitions(cohort_id) ON DELETE CASCADE,
        formula_version TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT,
        input_hash TEXT NOT NULL, manifest_json TEXT NOT NULL)""",
    """CREATE TABLE analysis_metric_results (
        run_id TEXT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
        formula_id TEXT NOT NULL, formula_version TEXT NOT NULL, result_json TEXT NOT NULL,
        PRIMARY KEY(run_id, formula_id))""",
    """CREATE TABLE analysis_outcomes (
        run_id TEXT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
        video_id TEXT NOT NULL, outcome_json TEXT NOT NULL, PRIMARY KEY(run_id, video_id))""",
    "CREATE INDEX analysis_expiry ON analysis_runs(expires_at)",
    *(
        f"""CREATE TRIGGER immutable_{table} BEFORE UPDATE ON {table}
        BEGIN SELECT RAISE(ABORT, 'Append-only analysis cannot be updated'); END"""
        for table in ("analysis_runs", "analysis_metric_results", "analysis_outcomes")
    ),
    "UPDATE app_metadata SET value='phase_3_core_analytics' WHERE key='schema_scope'",
)
