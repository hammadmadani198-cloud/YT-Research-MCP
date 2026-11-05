"""Schema v3 only. The v1/v2 SQL strings and checksums remain frozen."""

ELIGIBILITY_SQL = (
    """CREATE TABLE eligibility_rules (
        rule_id TEXT PRIMARY KEY, decision_type TEXT NOT NULL, rule_json TEXT NOT NULL)""",
    """CREATE TABLE classification_claims (
        evidence_id TEXT PRIMARY KEY, entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL,
        field TEXT NOT NULL, source TEXT NOT NULL, observed_at TEXT NOT NULL,
        available_at TEXT NOT NULL, expires_at TEXT, claim_json TEXT NOT NULL,
        CHECK(observed_at <= available_at))""",
    """CREATE TABLE classification_details (
        decision_id TEXT PRIMARY KEY
            REFERENCES eligibility_decisions(decision_id) ON DELETE CASCADE,
        rule_id TEXT NOT NULL REFERENCES eligibility_rules(rule_id), label TEXT NOT NULL,
        classification_json TEXT NOT NULL)""",
    """CREATE TABLE taxonomy_nodes (
        node_id TEXT NOT NULL, taxonomy_version TEXT NOT NULL, label TEXT NOT NULL,
        level TEXT NOT NULL, parent_id TEXT, available_at TEXT NOT NULL, node_json TEXT NOT NULL,
        PRIMARY KEY(node_id, taxonomy_version),
        FOREIGN KEY(parent_id, taxonomy_version)
            REFERENCES taxonomy_nodes(node_id, taxonomy_version))""",
    """CREATE TABLE niche_memberships (
        membership_id TEXT PRIMARY KEY, entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL,
        node_id TEXT NOT NULL, taxonomy_version TEXT NOT NULL, source TEXT NOT NULL,
        rule_version TEXT NOT NULL, decided_at TEXT NOT NULL, available_at TEXT NOT NULL,
        expires_at TEXT, membership_json TEXT NOT NULL,
        FOREIGN KEY(node_id, taxonomy_version) REFERENCES taxonomy_nodes(node_id, taxonomy_version),
        CHECK(available_at <= decided_at))""",
    """CREATE TABLE creator_groups (
        group_id TEXT PRIMARY KEY, display_label TEXT NOT NULL,
        group_kind TEXT NOT NULL CHECK(group_kind IN ('creator','studio','network')))""",
    """CREATE TABLE creator_group_memberships (
        membership_id TEXT PRIMARY KEY, group_id TEXT NOT NULL REFERENCES creator_groups(group_id),
        channel_id TEXT NOT NULL, evidence_id TEXT NOT NULL
            REFERENCES classification_claims(evidence_id) ON DELETE CASCADE,
        available_at TEXT NOT NULL, expires_at TEXT)""",
    """CREATE TABLE cohort_definitions (
        cohort_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, known_at TEXT NOT NULL,
        research_run TEXT NOT NULL, definition_json TEXT NOT NULL,
        candidates_hash TEXT NOT NULL, expires_at TEXT,
        CHECK(known_at <= created_at))""",
    """CREATE TABLE cohort_memberships (
        cohort_id TEXT NOT NULL REFERENCES cohort_definitions(cohort_id) ON DELETE CASCADE,
        entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL, state TEXT NOT NULL,
        member_json TEXT NOT NULL, PRIMARY KEY(cohort_id, entity_kind, entity_id))""",
    """CREATE TABLE retention_permissions (
        permission_id TEXT PRIMARY KEY, source TEXT NOT NULL, approval_reference TEXT NOT NULL,
        verified_by TEXT NOT NULL, verified_at TEXT NOT NULL, expires_at TEXT NOT NULL,
        statistical_months INTEGER NOT NULL CHECK(statistical_months BETWEEN 1 AND 36))""",
    """CREATE TABLE statistical_history (
        observation_id TEXT PRIMARY KEY, entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL,
        source TEXT NOT NULL, observed_at TEXT NOT NULL, available_at TEXT NOT NULL,
        expires_at TEXT NOT NULL, permission_id TEXT NOT NULL
            REFERENCES retention_permissions(permission_id) ON DELETE CASCADE,
        statistics_json TEXT NOT NULL, CHECK(observed_at <= available_at))""",
    "CREATE INDEX claim_subject ON classification_claims"
    "(entity_kind, entity_id, field, available_at)",
    "CREATE INDEX niche_subject ON niche_memberships"
    "(entity_kind, entity_id, taxonomy_version, decided_at)",
    "CREATE INDEX statistical_subject ON statistical_history(entity_kind, entity_id, available_at)",
    *(
        f"""CREATE TRIGGER immutable_{table} BEFORE UPDATE ON {table}
            BEGIN SELECT RAISE(ABORT, 'Append-only classification cannot be updated'); END"""
        for table in (
            "eligibility_rules",
            "classification_claims",
            "classification_details",
            "taxonomy_nodes",
            "niche_memberships",
            "creator_groups",
            "creator_group_memberships",
            "cohort_definitions",
            "cohort_memberships",
            "retention_permissions",
            "statistical_history",
        )
    ),
    "UPDATE app_metadata SET value='phase_2_eligibility_cohorts' WHERE key='schema_scope'",
)
