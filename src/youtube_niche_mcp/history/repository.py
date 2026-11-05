"""Append-only collection, explicit retention deletion, and availability-gated reads."""

import json
import sqlite3
from datetime import UTC, datetime, timedelta

from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.evidence import NumericEvidence
from youtube_niche_mcp.domain.foundation import Decision, Observation, timestamp, valid_id
from youtube_niche_mcp.domain.provenance import Provenance
from youtube_niche_mcp.domain.states import EvidenceState, Precision, SourceKind
from youtube_niche_mcp.services.safety import identity, safe_json


class HistoryRepository:
    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        clock=lambda: datetime.now(UTC),
        secrets: tuple[str, ...] = (),
    ):
        self.connection, self.clock, self.secrets = connection, clock, secrets

    @staticmethod
    def names(kind: str) -> tuple[str, str]:
        if kind not in {"channel", "video"}:
            raise ValueError("Unsupported entity kind")
        return ("channels" if kind == "channel" else "videos", f"{kind}_observations")

    def ensure_entity(self, kind: str, entity_id: str, first_seen: datetime) -> None:
        entities, _ = self.names(kind)
        if not valid_id(kind, entity_id):
            raise ValueError("Malformed entity identifier")
        at = timestamp(first_seen)
        self.connection.execute(
            f"""INSERT INTO {entities} VALUES (?, ?) ON CONFLICT({kind}_id)
            DO UPDATE SET first_seen_at=MIN(first_seen_at, excluded.first_seen_at)""",
            (entity_id, at),
        )

    def append(self, observation: Observation) -> str:
        observation = Observation.model_validate(observation.model_dump(mode="json"))
        _, table = self.names(observation.entity_kind)
        body = observation.model_dump(mode="json")
        content_hash = identity(body, self.secrets)
        source_body = {
            "provenance": body["provenance"],
            "request_at": timestamp(observation.request_at),
        }
        source_id = identity(source_body, self.secrets)
        observation_id = identity(
            [
                observation.capture_id,
                observation.entity_kind,
                observation.entity_id,
                observation.provenance.source,
            ]
        )
        existing = self.connection.execute(
            f"SELECT content_hash FROM {table} WHERE observation_id=?", (observation_id,)
        ).fetchone()
        if existing:
            if existing[0] != content_hash:
                raise ValueError("Capture replay differs from stored immutable observation")
            return observation_id
        p = observation.provenance
        expires = timestamp(p.observed_at + timedelta(days=30))
        with atomic(self.connection):
            self.ensure_entity(observation.entity_kind, observation.entity_id, p.available_at)
            self.connection.execute(
                "INSERT OR IGNORE INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    source_id,
                    p.source,
                    p.source_kind.value,
                    p.source_version,
                    p.precision.value,
                    timestamp(observation.request_at),
                    timestamp(p.observed_at),
                    timestamp(p.available_at),
                    safe_json(body["provenance"], self.secrets),
                    expires,
                ),
            )
            values = {name: evidence.value for name, evidence in observation.metrics.items()}
            columns = (
                "subscriber_count, subscriber_hidden, video_count"
                if observation.entity_kind == "channel"
                else "like_count, comment_count"
            )
            extra = (
                (
                    values.get("subscriber_count"),
                    observation.metadata.subscriber_hidden,
                    values.get("video_count"),
                )
                if observation.entity_kind == "channel"
                else (values.get("like_count"), values.get("comment_count"))
            )
            row = (
                observation_id,
                observation.entity_id,
                observation.capture_id,
                source_id,
                timestamp(p.observed_at),
                timestamp(p.available_at),
                observation.outcome.value,
                observation.outcome_detail,
                observation.http_status,
                values.get("view_count"),
                *extra,
                safe_json(body["metrics"], self.secrets),
                safe_json(body["metadata"], self.secrets),
                observation.metric_definition,
                content_hash,
            )
            self.connection.execute(
                f"""INSERT INTO {table}(observation_id, {observation.entity_kind}_id,
                capture_id, source_id, observed_at, available_at, outcome, outcome_detail,
                http_status, view_count, {columns}, evidence_json, metadata_json,
                metric_definition, content_hash) VALUES ({",".join("?" for _ in row)})""",
                row,
            )
            from youtube_niche_mcp.history.retention import RetentionRepository

            RetentionRepository(self).archive(observation, observation_id)
        return observation_id

    def observations(
        self, kind: str, entity_id: str, at: datetime, *, source: str | None = None
    ) -> list[dict]:
        entities, table = self.names(kind)
        args = [entity_id, timestamp(at), timestamp(at), timestamp(at), timestamp(self.clock())]
        query = f"""SELECT o.*, s.source, s.provenance_json, s.request_at, s.expires_at
            FROM {table} o JOIN source_records s ON s.source_id=o.source_id
            JOIN {entities} e ON e.{kind}_id=o.{kind}_id
            WHERE o.{kind}_id=? AND o.observed_at<=? AND o.available_at<=?
              AND e.first_seen_at<=? AND s.expires_at>?
        """
        if source:
            query += " AND s.source=?"
            args.append(source)
        query += " ORDER BY o.observed_at DESC, o.available_at DESC, o.observation_id"
        return [dict(row) for row in self.connection.execute(query, args)]

    def latest(
        self, kind: str, entity_id: str, at: datetime, *, source: str | None = None
    ) -> dict | None:
        rows = self.observations(kind, entity_id, at, source=source)
        return rows[0] if rows else None

    def existed(self, kind: str, entity_id: str, at: datetime) -> bool:
        entities, _ = self.names(kind)
        return (
            self.connection.execute(
                f"SELECT 1 FROM {entities} WHERE {kind}_id=? AND first_seen_at<=?",
                (entity_id, timestamp(at)),
            ).fetchone()
            is not None
        )

    def publication_size(
        self, channel_id: str, publication_at: datetime, *, tolerance: timedelta = timedelta(days=1)
    ) -> NumericEvidence:
        if not timedelta(0) <= tolerance <= timedelta(days=7):
            raise ValueError("Explicit bounded contemporaneous window required")
        for row in self.statistical_snapshots("channel", channel_id, publication_at):
            observed = datetime.fromisoformat(row["observed_at"])
            evidence = json.loads(row["evidence_json"]).get("subscriber_count")
            if (
                publication_at - observed <= tolerance
                and evidence
                and evidence.get("value") is not None
            ):
                return NumericEvidence.model_validate(evidence)
        return NumericEvidence(
            state=EvidenceState.INSUFFICIENT_HISTORY,
            value=None,
            reason="No contemporaneous subscriber evidence available at publication",
            provenance=Provenance(
                source="history:publication-size-query",
                source_kind=SourceKind.DERIVED,
                source_version="publication-size-v1",
                precision=Precision.UNKNOWN,
                observed_at=publication_at,
                available_at=publication_at,
            ),
        )

    def statistical_snapshots(self, kind: str, entity_id: str, at: datetime) -> list[dict]:
        """Statistics only; valid extended history never rehydrates expired text."""
        from youtube_niche_mcp.history.retention import RetentionRepository

        rows = {r["observation_id"]: r for r in self.observations(kind, entity_id, at)}
        for row in RetentionRepository(self).snapshots(kind, entity_id, at):
            if row["observation_id"] not in rows:
                row["evidence_json"] = json.dumps(json.loads(row["statistics_json"])["metrics"])
                rows[row["observation_id"]] = row
        return sorted(
            rows.values(), key=lambda r: (r["observed_at"], r["available_at"]), reverse=True
        )

    def record_decision(self, decision: Decision) -> str:
        body = decision.model_dump(mode="json")
        decision_id = identity(body, self.secrets)
        with atomic(self.connection):
            self.ensure_entity(decision.entity_kind, decision.entity_id, decision.available_at)
            self.connection.execute(
                "INSERT OR IGNORE INTO eligibility_decisions "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    decision_id,
                    decision.entity_kind,
                    decision.entity_id,
                    decision.decision_type,
                    decision.state.value,
                    decision.confidence,
                    decision.source,
                    decision.reason,
                    decision.rule_version,
                    timestamp(decision.observed_at),
                    timestamp(decision.available_at),
                    timestamp(decision.decided_at),
                    timestamp(decision.observed_at + timedelta(days=30)),
                ),
            )
        return decision_id

    def latest_decision(
        self, kind: str, entity_id: str, decision_type: str, at: datetime
    ) -> dict | None:
        entities, _ = self.names(kind)
        row = self.connection.execute(
            f"""SELECT d.* FROM eligibility_decisions d JOIN {entities} e
            ON e.{kind}_id=d.entity_id WHERE entity_kind=? AND entity_id=? AND decision_type=?
            AND observed_at<=? AND available_at<=? AND decided_at<=? AND e.first_seen_at<=?
            AND expires_at>? ORDER BY decided_at DESC, decision_id LIMIT 1""",
            (kind, entity_id, decision_type, *([timestamp(at)] * 4), timestamp(self.clock())),
        ).fetchone()
        return dict(row) if row else None

    def conflict(
        self,
        kind: str,
        entity_id: str,
        field: str,
        left_id: str,
        right_id: str,
        *,
        detected_at: datetime,
        preferred_source: str = "youtube:videos.list",
    ) -> str:
        _, table = self.names(kind)
        if field not in {
            "publication_at",
            "upload_at",
            "provider_index_at",
            "title",
            "channel_id",
            "view_count",
            "subscriber_count",
        }:
            raise ValueError("Unsupported conflict field")
        rows = [
            self.connection.execute(
                f"SELECT * FROM {table} WHERE observation_id=? AND {kind}_id=?", (value, entity_id)
            ).fetchone()
            for value in (left_id, right_id)
        ]
        if any(row is None for row in rows) or left_id == right_id:
            raise ValueError("Two subject observations required")
        for row in rows:
            if row["available_at"] > timestamp(detected_at):
                raise ValueError("Cannot detect an unavailable source")

        def field_value(row):
            return (
                row[field]
                if field in {"view_count", "subscriber_count"} and field in dict(row)
                else json.loads(row["metadata_json"]).get(field)
            )

        if field_value(rows[0]) == field_value(rows[1]):
            raise ValueError("Values do not conflict")
        source_ids = [row["source_id"] for row in rows]
        if not self.connection.execute(
            "SELECT 1 FROM source_records WHERE source_id IN (?, ?) AND source=?",
            (*source_ids, preferred_source),
        ).fetchone():
            raise ValueError("Preferred source must be a preserved alternative")
        cid = identity([kind, entity_id, field, *sorted([left_id, right_id])])
        with atomic(self.connection):
            self.connection.execute(
                "INSERT OR IGNORE INTO source_conflicts "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    cid,
                    kind,
                    entity_id,
                    field,
                    left_id,
                    right_id,
                    *source_ids,
                    preferred_source,
                    "official-detail-preference-v1",
                    timestamp(detected_at),
                    timestamp(detected_at),
                ),
            )
        return cid

    def conflicts(self, kind: str, entity_id: str, at: datetime) -> list[dict]:
        return [
            dict(row)
            for row in self.connection.execute(
                """SELECT c.* FROM source_conflicts c
            JOIN source_records l ON c.left_source_id=l.source_id
            JOIN source_records r ON c.right_source_id=r.source_id
            WHERE entity_kind=? AND entity_id=? AND c.available_at<=?
            AND l.expires_at>? AND r.expires_at>? ORDER BY c.available_at""",
                (kind, entity_id, timestamp(at), timestamp(self.clock()), timestamp(self.clock())),
            )
        ]

    def record_quota(self, entry) -> None:
        with atomic(self.connection):
            self.connection.execute(
                """INSERT INTO quota_requests(endpoint,request_count,assumed_cost,bucket,
                requested_at,contract_version) VALUES (?, ?, ?, ?, ?, ?)""",
                tuple(vars(entry).values()),
            )

    def purge_expired(self) -> dict[str, int]:
        """Explicit policy deletion; never invoked by startup/verify/read queries."""
        now = timestamp(self.clock())
        result = {}
        with atomic(self.connection):
            for table in (
                "analysis_runs",
                "source_records",
                "discovery_runs",
                "eligibility_decisions",
                "live_cache",
                "derived_cache",
                "cohort_definitions",
                "niche_memberships",
                "creator_group_memberships",
                "classification_claims",
                "statistical_history",
                "retention_permissions",
                "provider_runs",
                "provider_evidence",
                "qualitative_annotations",
            ):
                result[table] = self.connection.execute(
                    f"DELETE FROM {table} WHERE expires_at<=?", (now,)
                ).rowcount
            self.connection.execute(
                """DELETE FROM snapshot_targets WHERE observation_id IS NOT NULL AND
                observation_id NOT IN (SELECT observation_id FROM channel_observations
                UNION SELECT observation_id FROM video_observations)"""
            )
            result["snapshot_jobs"] = self.connection.execute(
                "DELETE FROM snapshot_jobs WHERE requested_at<=?",
                (timestamp(self.clock() - timedelta(days=30)),),
            ).rowcount
            for kind in ("channel", "video"):
                entities, table = self.names(kind)
                self.connection.execute(
                    f"""DELETE FROM {entities} WHERE first_seen_at<=? AND {kind}_id
                    NOT IN (SELECT {kind}_id FROM {table})
                    AND {kind}_id NOT IN
                        (SELECT entity_id FROM classification_claims WHERE entity_kind=?)
                    AND {kind}_id NOT IN
                        (SELECT entity_id FROM statistical_history WHERE entity_kind=?)
                    AND {kind}_id NOT IN
                        (SELECT entity_id FROM cohort_memberships WHERE entity_kind=?)""",
                    (timestamp(self.clock() - timedelta(days=30)), kind, kind, kind),
                )
        return result
