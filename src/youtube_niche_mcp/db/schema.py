"""Frozen v1 bootstrap followed by the normalized Phase 1 research foundation."""

from dataclasses import dataclass
from hashlib import sha256

from youtube_niche_mcp.db.phase2 import ELIGIBILITY_SQL
from youtube_niche_mcp.db.phase2_5 import PROVIDER_SQL
from youtube_niche_mcp.db.phase3 import ANALYSIS_SQL
from youtube_niche_mcp.db.phase5 import QUALITATIVE_SQL
from youtube_niche_mcp.db.phase7 import WATCH_SQL


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        return sha256("\n".join(self.statements).encode("utf-8")).hexdigest()


BOOTSTRAP = (
    Migration(
        1,
        "bootstrap",
        (
            """CREATE TABLE app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""",
            """INSERT INTO app_metadata(key, value)
                VALUES ('schema_scope', 'phase_0_bootstrap')""",
        ),
    ),
)

FOUNDATION_SQL = (
    """CREATE TABLE channels (channel_id TEXT PRIMARY KEY, first_seen_at TEXT NOT NULL)""",
    """CREATE TABLE videos (video_id TEXT PRIMARY KEY, first_seen_at TEXT NOT NULL)""",
    """CREATE TABLE source_records (
        source_id TEXT PRIMARY KEY, source TEXT NOT NULL, source_kind TEXT NOT NULL,
        source_version TEXT NOT NULL, precision TEXT NOT NULL, request_at TEXT NOT NULL,
        observed_at TEXT NOT NULL, available_at TEXT NOT NULL, provenance_json TEXT NOT NULL,
        expires_at TEXT NOT NULL, CHECK(request_at <= observed_at),
        CHECK(observed_at <= available_at))""",
    *(
        f"""CREATE TABLE {kind}_observations (
            observation_id TEXT PRIMARY KEY, {kind}_id TEXT NOT NULL REFERENCES {plural}({kind}_id),
            capture_id TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES source_records(source_id)
                ON DELETE CASCADE,
            observed_at TEXT NOT NULL, available_at TEXT NOT NULL, outcome TEXT NOT NULL,
            outcome_detail TEXT NOT NULL, http_status INTEGER,
            view_count INTEGER CHECK(view_count >= 0),
            {extra}, evidence_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
            metric_definition TEXT NOT NULL, content_hash TEXT NOT NULL,
            UNIQUE(capture_id, {kind}_id, source_id), CHECK(observed_at <= available_at))"""
        for kind, plural, extra in (
            (
                "channel",
                "channels",
                "subscriber_count INTEGER CHECK(subscriber_count >= 0), "
                "subscriber_hidden INTEGER, video_count INTEGER CHECK(video_count >= 0)",
            ),
            (
                "video",
                "videos",
                "like_count INTEGER CHECK(like_count >= 0), "
                "comment_count INTEGER CHECK(comment_count >= 0)",
            ),
        )
    ),
    """CREATE TABLE source_conflicts (
        conflict_id TEXT PRIMARY KEY, entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL,
        field TEXT NOT NULL, left_observation_id TEXT NOT NULL, right_observation_id TEXT NOT NULL,
        left_source_id TEXT NOT NULL REFERENCES source_records(source_id) ON DELETE CASCADE,
        right_source_id TEXT NOT NULL REFERENCES source_records(source_id) ON DELETE CASCADE,
        preferred_source TEXT NOT NULL, policy_version TEXT NOT NULL,
        detected_at TEXT NOT NULL, available_at TEXT NOT NULL)""",
    """CREATE TABLE discovery_runs (
        run_id TEXT PRIMARY KEY, query TEXT NOT NULL, route TEXT NOT NULL, provider TEXT NOT NULL,
        sort_order TEXT, filters_json TEXT NOT NULL, region TEXT, language TEXT,
        mode TEXT NOT NULL, page_size INTEGER NOT NULL, started_at TEXT NOT NULL,
        finished_at TEXT, outcome TEXT NOT NULL, collection_version TEXT NOT NULL,
        expires_at TEXT NOT NULL)""",
    """CREATE TABLE discovery_pages (
        run_id TEXT NOT NULL REFERENCES discovery_runs(run_id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL, request_token TEXT, next_token TEXT,
        request_at TEXT NOT NULL, observed_at TEXT NOT NULL, available_at TEXT NOT NULL,
        outcome TEXT NOT NULL, http_status INTEGER, reason TEXT NOT NULL,
        PRIMARY KEY(run_id, page_number))""",
    """CREATE TABLE discovery_results (
        run_id TEXT NOT NULL REFERENCES discovery_runs(run_id) ON DELETE CASCADE,
        rank INTEGER NOT NULL, page_number INTEGER NOT NULL, page_rank INTEGER NOT NULL,
        result_id TEXT, result_type TEXT, raw_status TEXT NOT NULL,
        outcome TEXT NOT NULL, observed_at TEXT NOT NULL, available_at TEXT NOT NULL,
        PRIMARY KEY(run_id, rank),
        FOREIGN KEY(run_id, page_number) REFERENCES discovery_pages(run_id, page_number))""",
    """CREATE TABLE eligibility_decisions (
        decision_id TEXT PRIMARY KEY, entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL,
        decision_type TEXT NOT NULL, state TEXT NOT NULL, confidence TEXT NOT NULL,
        source TEXT NOT NULL, reason TEXT NOT NULL, rule_version TEXT NOT NULL,
        observed_at TEXT NOT NULL, available_at TEXT NOT NULL, decided_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        CHECK(observed_at <= available_at AND available_at <= decided_at))""",
    """CREATE TABLE snapshot_jobs (
        job_id TEXT PRIMARY KEY, requested_at TEXT NOT NULL, finished_at TEXT,
        status TEXT NOT NULL, targets_hash TEXT NOT NULL, collection_version TEXT NOT NULL)""",
    """CREATE TABLE snapshot_targets (
        job_id TEXT NOT NULL REFERENCES snapshot_jobs(job_id) ON DELETE CASCADE,
        entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL, outcome TEXT NOT NULL,
        observation_id TEXT, request_at TEXT, captured_at TEXT, available_at TEXT,
        reason TEXT NOT NULL, http_status INTEGER,
        PRIMARY KEY(job_id, entity_kind, entity_id))""",
    """CREATE TABLE live_cache (
        cache_key TEXT PRIMARY KEY, source TEXT NOT NULL, payload_json TEXT NOT NULL,
        fetched_at TEXT NOT NULL, expires_at TEXT NOT NULL, stale_until TEXT NOT NULL)""",
    """CREATE TABLE derived_cache (
        cache_key TEXT PRIMARY KEY, input_identity TEXT NOT NULL, analysis_version TEXT NOT NULL,
        permission_state TEXT NOT NULL, payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL, expires_at TEXT NOT NULL)""",
    """CREATE TABLE quota_requests (
        request_id INTEGER PRIMARY KEY, endpoint TEXT NOT NULL, request_count INTEGER NOT NULL,
        assumed_cost INTEGER NOT NULL, bucket TEXT NOT NULL,
        requested_at TEXT NOT NULL, contract_version TEXT NOT NULL)""",
    "CREATE INDEX channel_time ON channel_observations(channel_id, observed_at DESC, available_at)",
    "CREATE INDEX video_time ON video_observations(video_id, observed_at DESC, available_at)",
    "CREATE INDEX channels_first_seen ON channels(first_seen_at)",
    "CREATE INDEX videos_first_seen ON videos(first_seen_at)",
    "CREATE INDEX discovery_rank ON discovery_results(run_id, page_number, rank)",
    "CREATE INDEX conflict_subject ON source_conflicts(entity_kind, entity_id, available_at)",
    "CREATE INDEX decision_subject ON eligibility_decisions"
    "(entity_kind, entity_id, decided_at DESC, available_at)",
    "CREATE INDEX source_expiry ON source_records(expires_at)",
    "CREATE INDEX quota_time ON quota_requests(bucket, requested_at)",
    *(
        f"""CREATE TRIGGER immutable_{table} BEFORE UPDATE ON {table}
            BEGIN SELECT RAISE(ABORT, 'Append-only evidence cannot be updated'); END"""
        for table in (
            "source_records",
            "channel_observations",
            "video_observations",
            "source_conflicts",
            "eligibility_decisions",
            "discovery_results",
            "discovery_pages",
        )
    ),
    "UPDATE app_metadata SET value='phase_1_foundation' WHERE key='schema_scope'",
)
MIGRATIONS = (
    *BOOTSTRAP,
    Migration(2, "research_foundation", FOUNDATION_SQL),
    Migration(3, "eligibility_cohorts", ELIGIBILITY_SQL),
    Migration(4, "optional_provider_evidence", PROVIDER_SQL),
    Migration(5, "core_analytics", ANALYSIS_SQL),
    Migration(6, "qualitative_reviews", QUALITATIVE_SQL),
    Migration(7, "local_watch_intent", WATCH_SQL),
)
SCHEMA_VERSION = MIGRATIONS[-1].version
