"""Bulk frozen-input reads, source firewall and retention-bounded analysis storage."""

import json
from collections import defaultdict

from youtube_niche_mcp.analysis.models import (
    AnalysisBundle,
    AnalysisFrame,
    AnalysisRun,
    MetricResult,
    Outcome,
    Snapshot,
    VideoInput,
)
from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.models import CohortDefinition, CohortMember
from youtube_niche_mcp.services.safety import identity, safe_json


class AnalysisUnavailable(ValueError):
    def __init__(self, state, message):
        super().__init__(message)
        self.state = state


class AnalysisRepository:
    def __init__(self, history):
        self.history = history
        self.connection = history.connection

    def load(self, cohort_id, video_cohort_id, options):
        now, cutoff = self.history.clock(), options.cutoff
        if cutoff > now:
            raise ValueError("Cannot analyze a future cutoff")
        c = self.connection
        expiries, input_ids = [], set()

        def cohort(cid):
            row = c.execute("SELECT * FROM cohort_definitions WHERE cohort_id=?", (cid,)).fetchone()
            if not row:
                raise AnalysisUnavailable("insufficient_sample", "Frozen cohort unavailable")
            if row["expires_at"] and row["expires_at"] <= timestamp(now):
                raise AnalysisUnavailable(
                    "policy_permission_required", "Frozen input retention expired"
                )
            if row["expires_at"]:
                expiries.append(row["expires_at"])
            d = CohortDefinition.model_validate_json(row["definition_json"])
            if d.known_at > cutoff or d.created_at > cutoff:
                raise ValueError("Future cohort cannot enter past analysis")
            members = tuple(
                CohortMember.model_validate_json(r[0])
                for r in c.execute(
                    "SELECT member_json FROM cohort_memberships WHERE cohort_id=? "
                    "ORDER BY entity_id",
                    (cid,),
                )
            )
            input_ids.add(cid)
            return d, members

        definition, members = cohort(cohort_id)
        video_definition, video_members = cohort(video_cohort_id or cohort_id)
        if video_definition.kind != "eligible_long_form":
            raise ValueError("Analysis requires a frozen eligible-video frame")
        if definition.boundary != video_definition.boundary:
            raise ValueError("Frozen frames have different niche boundary/taxonomy versions")
        channels = (
            {m.subject.entity_id for m in members}
            if definition.kind != "eligible_long_form"
            else None
        )
        video_members = tuple(m for m in video_members if m.subject.entity_kind == "video")
        ids = {m.subject.entity_id for m in video_members}
        # Constant number of bulk queries; no per-video DB calls.
        live = defaultdict(list)
        rows = c.execute(
            """SELECT o.*,s.source,s.source_kind,s.precision,s.expires_at
            FROM video_observations o JOIN source_records s USING(source_id)
            WHERE o.observed_at<=? AND o.available_at<=?""",
            (timestamp(cutoff), timestamp(cutoff)),
        )
        for row in rows:
            if row["video_id"] in ids:
                live[row["video_id"]].append(dict(row))
        archive = defaultdict(list)
        for row in c.execute(
            """SELECT h.*,p.expires_at AS permission_expires
            FROM statistical_history h JOIN retention_permissions p USING(permission_id)
            WHERE h.entity_kind='video' AND h.observed_at<=? AND h.available_at<=?""",
            (timestamp(cutoff), timestamp(cutoff)),
        ):
            if row["entity_id"] in ids:
                archive[row["entity_id"]].append(dict(row))
        topics = defaultdict(list)
        taxonomy = list(
            c.execute(
                "SELECT node_id,parent_id FROM taxonomy_nodes WHERE taxonomy_version=? "
                "AND available_at<=?",
                (definition.boundary.taxonomy_version, timestamp(video_definition.known_at)),
            )
        )
        scoped_nodes = set(definition.boundary.node_ids)
        for _ in range(6):
            scoped_nodes.update(r[0] for r in taxonomy if r[1] in scoped_nodes)
        for row in c.execute(
            """SELECT m.*,n.level FROM niche_memberships m JOIN taxonomy_nodes n
            USING(node_id,taxonomy_version) WHERE m.taxonomy_version=? AND m.available_at<=?
            AND m.decided_at<=? AND n.available_at<=? AND n.level='topic_family'""",
            (
                definition.boundary.taxonomy_version,
                timestamp(video_definition.known_at),
                timestamp(video_definition.known_at),
                timestamp(video_definition.known_at),
            ),
        ):
            if row["entity_id"] in ids and row["node_id"] in scoped_nodes:
                topics[row["entity_id"]].append(dict(row))
        conflicts = defaultdict(list)
        for row in c.execute(
            "SELECT * FROM source_conflicts WHERE available_at<=?", (timestamp(cutoff),)
        ):
            if row["entity_id"] in ids:
                conflicts[row["entity_id"]].append(dict(row))
        videos = []
        for m in video_members:
            vid = m.subject.entity_id
            canonical = [
                r
                for r in live[vid]
                if r["source_kind"] == "public_api"
                and r["source"] == "youtube:videos.list"
                and r["expires_at"] > timestamp(now)
                and r["available_at"] <= timestamp(video_definition.known_at)
                and r["outcome"] == "available"
            ]
            canonical.sort(
                key=lambda r: (r["observed_at"], r["available_at"], r["observation_id"]),
                reverse=True,
            )
            meta = json.loads(canonical[0]["metadata_json"]) if canonical else {}
            channel = meta.get("channel_id")
            if channels is not None and channel and channel not in channels:
                continue
            pub = meta.get("publication_at")
            canonical_identities = {
                (
                    json.loads(r["metadata_json"]).get("channel_id"),
                    json.loads(r["metadata_json"]).get("publication_at"),
                )
                for r in canonical
            }
            selected_topics = {}
            for r in sorted(
                topics[vid], key=lambda r: (r["decided_at"], r["membership_id"]), reverse=True
            ):
                if r["rule_version"] != definition.boundary.classifier_version:
                    continue
                if r["expires_at"] and r["expires_at"] <= timestamp(now):
                    continue
                key = (r["node_id"], r["source"], r["rule_version"])
                selected_topics.setdefault(key, r)
            states = defaultdict(set)
            for r in selected_topics.values():
                body = json.loads(r["membership_json"])
                states[r["node_id"]].add(body["state"])
                input_ids.add(r["membership_id"])
                if r["expires_at"]:
                    expiries.append(r["expires_at"])
            families = tuple(sorted(k for k, s in states.items() if s == {"included"}))
            topic_conflict = any(
                "included" in s and ("excluded" in s or "uncertain" in s) for s in states.values()
            )
            snapshots, blocked = {}, False
            for r in live[vid]:
                if r["expires_at"] <= timestamp(now):
                    blocked = True
                    continue
                evidence = json.loads(r["evidence_json"]).get("view_count", {})
                provenance = evidence.get("provenance", {})
                value = evidence.get("value")
                if value is not None and type(value) is not int:
                    value = None
                s = Snapshot(
                    observation_id=r["observation_id"],
                    source=r["source"],
                    source_kind=r["source_kind"],
                    observed_at=r["observed_at"],
                    available_at=r["available_at"],
                    expires_at=r["expires_at"],
                    value=value,
                    precision=provenance.get("precision", "unknown"),
                    evidence_state=evidence.get("state", "insufficient_history"),
                    metric_definition=r["metric_definition"],
                    outcome=r["outcome"],
                )
                snapshots[s.observation_id] = s
            for r in archive[vid]:
                if r["expires_at"] <= timestamp(now) or r["permission_expires"] <= timestamp(now):
                    blocked = True
                    continue
                evidence = json.loads(r["statistics_json"]).get("metrics", {}).get("view_count", {})
                p = evidence.get("provenance", {})
                if not evidence or type(evidence.get("value")) is not int:
                    continue
                expiry = min(r["expires_at"], r["permission_expires"])
                s = Snapshot(
                    observation_id=r["observation_id"],
                    source=r["source"],
                    source_kind=p.get("source_kind", "unknown"),
                    observed_at=r["observed_at"],
                    available_at=r["available_at"],
                    expires_at=expiry,
                    value=evidence["value"],
                    precision=p.get("precision", "unknown"),
                    evidence_state=evidence.get("state", "insufficient_history"),
                    metric_definition=json.loads(r["statistics_json"])["metric_definition"],
                )
                # Prefer permitted extended statistics when they have a longer validity.
                if (
                    s.observation_id not in snapshots
                    or s.expires_at > snapshots[s.observation_id].expires_at
                ):
                    snapshots[s.observation_id] = s
                input_ids.add(r["permission_id"])
            if canonical:
                input_ids.add(canonical[0]["observation_id"])
                expiries.append(canonical[0]["expires_at"])
            for s in snapshots.values():
                input_ids.add(s.observation_id)
                expiries.append(timestamp(s.expires_at))
            input_ids.update(m.evidence_ids)
            input_ids.update(m.decision_ids)
            identity_conflict = len(canonical_identities) > 1 or any(
                r["field"] in {"publication_at", "channel_id"}
                and r["available_at"] <= timestamp(video_definition.known_at)
                and not r["preferred_source"].startswith("youtube:")
                for r in conflicts[vid]
            )
            videos.append(
                VideoInput(
                    video_id=vid,
                    channel_id=channel,
                    publication_at=pub,
                    membership=m,
                    snapshots=tuple(sorted(snapshots.values(), key=lambda s: s.observation_id)),
                    topic_families=families,
                    topic_conflict=topic_conflict,
                    identity_conflict=identity_conflict,
                    policy_blocked=blocked,
                )
            )
        # Frozen group units require retained grouping evidence; later group membership is ignored.
        all_members = (*members, *video_members)
        groups = list(
            c.execute(
                "SELECT * FROM creator_group_memberships WHERE available_at<=?",
                (timestamp(video_definition.known_at),),
            )
        )
        for m in all_members:
            if m.independence_state != "documented_group":
                continue
            group_id = m.independence_unit.removeprefix("group:")
            relevant = [r for r in groups if r["group_id"] == group_id]
            if not relevant or any(
                r["expires_at"] and r["expires_at"] <= timestamp(now) for r in relevant
            ):
                raise AnalysisUnavailable(
                    "policy_permission_required", "Frozen creator evidence no longer retained"
                )
            for r in relevant:
                input_ids.add(r["membership_id"])
                if r["expires_at"]:
                    expiries.append(r["expires_at"])
        body = {
            "definition": definition.model_dump(mode="json"),
            "video_definition": video_definition.model_dump(mode="json"),
            "members": [m.model_dump(mode="json") for m in members],
            "videos": [v.model_dump(mode="json") for v in videos],
            "input_ids": sorted(input_ids),
        }
        digest = identity(body, self.history.secrets)
        return AnalysisFrame(
            cohort_id=cohort_id,
            video_cohort_id=video_definition.cohort_id,
            kind=definition.kind,
            boundary=definition.boundary,
            freeze_at=definition.known_at,
            video_freeze_at=video_definition.known_at,
            members=members,
            videos=tuple(videos),
            input_ids=tuple(sorted(input_ids)),
            input_hash=digest,
            expires_at=min(expiries) if expiries else None,
        )

    def store(self, bundle: AnalysisBundle):
        body = bundle.run.model_dump(mode="json")
        r = bundle.run
        with atomic(self.connection):
            old = self.connection.execute(
                "SELECT 1 FROM analysis_runs WHERE run_id=?", (r.run_id,)
            ).fetchone()
            if old:
                previous = self.read(r.run_id)
                if previous.metrics != bundle.metrics or previous.outcomes != bundle.outcomes:
                    raise ValueError("Analysis replay differs from immutable results")
                return previous
            self.connection.execute(
                "INSERT INTO analysis_runs VALUES(?,?,?,?,?,?,?,?)",
                (
                    r.run_id,
                    r.cohort_id,
                    r.video_cohort_id,
                    r.formula_version,
                    timestamp(r.created_at),
                    timestamp(r.expires_at) if r.expires_at else None,
                    r.input_hash,
                    safe_json(body, self.history.secrets),
                ),
            )
            for result in bundle.metrics:
                self.connection.execute(
                    "INSERT INTO analysis_metric_results VALUES(?,?,?,?)",
                    (
                        r.run_id,
                        result.formula_id,
                        result.formula_version,
                        safe_json(result.model_dump(mode="json"), self.history.secrets),
                    ),
                )
            for o in bundle.outcomes:
                self.connection.execute(
                    "INSERT INTO analysis_outcomes VALUES(?,?,?)",
                    (
                        r.run_id,
                        o.video_id,
                        safe_json(o.model_dump(mode="json"), self.history.secrets),
                    ),
                )
        return bundle

    def read(self, run_id):
        row = self.connection.execute(
            "SELECT * FROM analysis_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if not row:
            raise AnalysisUnavailable("insufficient_sample", "Analysis run unavailable")
        if row["expires_at"] and row["expires_at"] <= timestamp(self.history.clock()):
            raise AnalysisUnavailable(
                "policy_permission_required", "Analysis input retention expired"
            )
        run = AnalysisRun.model_validate_json(row["manifest_json"])
        if run.formula_version == "phase6-v1":
            from youtube_niche_mcp.decision.service import validate_run

            validate_run(self.history, run)
        elif run.formula_version == "phase5-v1":
            from youtube_niche_mcp.qualitative.repository import ReviewRepository

            ReviewRepository(self.history).validate(run.input_ids, run.options.cutoff)
            for contextual_id in run.options.analysis_run_ids:
                self.read(contextual_id)
        else:
            self.validate_dependencies(run.input_ids)
        if run.formula_version == "phase4-v1":
            from collections import defaultdict

            from youtube_niche_mcp.analysis.historical_protocol import evidence_digest

            saved = run.options.annotation.get("frozen_discovery", [])
            wanted = {item["run_id"] for item in saved}
            runs = {
                r["run_id"]: r
                for r in self.connection.execute("SELECT * FROM discovery_runs")
                if r["run_id"] in wanted
            }
            pages, occurrences = defaultdict(list), defaultdict(list)
            for table, target in (("discovery_pages", pages), ("discovery_results", occurrences)):
                order = "page_number" if table == "discovery_pages" else "rank"
                for r in self.connection.execute(f"SELECT * FROM {table} ORDER BY run_id,{order}"):
                    if r["run_id"] in wanted:
                        target[r["run_id"]].append(r)
            if any(
                item["hash"]
                != evidence_digest(
                    runs[item["run_id"]],
                    pages[item["run_id"]],
                    occurrences[item["run_id"]],
                    item["cutoff"],
                )
                for item in saved
            ):
                raise AnalysisUnavailable("source_conflict", "Frozen discovery evidence changed")
        return AnalysisBundle(
            run=run,
            outcomes=tuple(
                Outcome.model_validate_json(r[0])
                for r in self.connection.execute(
                    "SELECT outcome_json FROM analysis_outcomes WHERE run_id=? ORDER BY video_id",
                    (run_id,),
                )
            ),
            metrics=tuple(
                MetricResult.model_validate_json(r[0])
                for r in self.connection.execute(
                    "SELECT result_json FROM analysis_metric_results WHERE run_id=? "
                    "ORDER BY formula_id",
                    (run_id,),
                )
            ),
        )

    def validate_dependencies(self, ids):
        """Revocation/purge cannot leave a readable cached derivative of removed inputs."""
        now = timestamp(self.history.clock())
        valid = set()
        for table, column in (
            ("cohort_definitions", "cohort_id"),
            ("classification_claims", "evidence_id"),
            ("eligibility_decisions", "decision_id"),
            ("niche_memberships", "membership_id"),
            ("creator_group_memberships", "membership_id"),
            ("retention_permissions", "permission_id"),
            ("source_records", "source_id"),
            ("discovery_runs", "run_id"),
            ("provider_runs", "run_id"),
        ):
            valid.update(
                r[0]
                for r in self.connection.execute(
                    f"SELECT {column} FROM {table} WHERE expires_at IS NULL OR expires_at>?", (now,)
                )
            )
        for table in ("video_observations", "channel_observations"):
            valid.update(
                r[0]
                for r in self.connection.execute(
                    f"SELECT observation_id FROM {table} JOIN source_records USING(source_id) "
                    "WHERE expires_at>?",
                    (now,),
                )
            )
        valid.update(
            r[0]
            for r in self.connection.execute(
                "SELECT h.observation_id FROM statistical_history h JOIN retention_permissions p "
                "USING(permission_id) WHERE h.expires_at>? AND p.expires_at>?",
                (now, now),
            )
        )
        valid.update(
            r[0]
            for r in self.connection.execute(
                "SELECT e.evidence_id FROM provider_evidence e JOIN provider_runs r USING(run_id) "
                "JOIN source_records s USING(source_id) "
                "WHERE e.expires_at>? AND r.expires_at>? AND s.expires_at>?",
                (now, now, now),
            )
        )
        valid.update(
            r[0]
            for r in self.connection.execute(
                "SELECT conflict_id FROM source_conflicts c JOIN source_records l "
                "ON c.left_source_id=l.source_id JOIN source_records r "
                "ON c.right_source_id=r.source_id "
                "WHERE l.expires_at>? AND r.expires_at>?",
                (now, now),
            )
        )
        if not set(ids) <= valid:
            raise AnalysisUnavailable(
                "policy_permission_required", "Analysis dependency removed or expired"
            )
