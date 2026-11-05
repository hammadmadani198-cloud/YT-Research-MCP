"""Immutable reviews and transitive known-at-time/retention validation."""

import json
from datetime import datetime

from youtube_niche_mcp.analysis.repository import AnalysisRepository, AnalysisUnavailable
from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.qualitative.models import Annotation
from youtube_niche_mcp.services.safety import identity, safe_json


def references(annotation):
    p = annotation.payload
    ids = set(annotation.input_ids)
    for field in ("source_annotation_ids", "provider_evidence_ids", "provider_similarity_ids"):
        ids.update(getattr(p, field, ()))
    for task in getattr(p, "tasks", ()):
        ids.update(task.evidence_ids)
    ids.update(m.permission_id for m in annotation.materials if m.permission_id)
    return tuple(sorted(ids))


class ReviewRepository:
    def __init__(self, history):
        self.history = history
        self.connection = history.connection
        self.analysis = AnalysisRepository(history)

    def validate(self, ids, cutoff=None):
        """Bulk ancestry walk; bounded depth, no per-video queries, no surviving orphans."""
        annotations = {
            r["annotation_id"]: dict(r)
            for r in self.connection.execute("SELECT * FROM qualitative_annotations")
        }
        runs = {
            r["run_id"]: dict(r) for r in self.connection.execute("SELECT * FROM analysis_runs")
        }
        ordinary, expiries, seen, stack = set(), [], set(), [(i, ()) for i in ids]
        now = self.history.clock()
        while stack:
            item, path = stack.pop()
            if item in path or len(path) > 32:
                raise ValueError("Cyclic or excessively deep evidence ancestry")
            if item in seen:
                continue
            seen.add(item)
            if len(seen) > 10000:
                raise ValueError("Evidence ancestry exceeds bounded review limit")
            row = annotations.get(item) or runs.get(item)
            if not row:
                ordinary.add(item)
                continue
            if row["expires_at"]:
                expiry = datetime.fromisoformat(row["expires_at"])
                if expiry <= now:
                    raise AnalysisUnavailable(
                        "policy_permission_required", "Evidence ancestry expired"
                    )
                expiries.append(expiry)
            if item in annotations:
                body = Annotation.model_validate_json(row["annotation_json"])
                known = body.decided_at
                dependencies = references(body)
            else:
                body = json.loads(row["manifest_json"])
                known = datetime.fromisoformat(body["options"]["cutoff"])
                dependencies = body["input_ids"]
                # Frozen phase-4 discovery fingerprint checks are preserved on contextual reads.
            if cutoff and known > cutoff:
                raise ValueError("Future review/analysis cannot enter past assessment")
            stack.extend((dependency, (*path, item)) for dependency in dependencies)
        self.analysis.validate_dependencies(ordinary)
        # Earliest input expiry bounds derived annotation retention, including permissions.
        for table, key in (
            ("source_records", "source_id"),
            ("classification_claims", "evidence_id"),
            ("eligibility_decisions", "decision_id"),
            ("niche_memberships", "membership_id"),
            ("creator_group_memberships", "membership_id"),
            ("retention_permissions", "permission_id"),
            ("cohort_definitions", "cohort_id"),
            ("discovery_runs", "run_id"),
            ("provider_runs", "run_id"),
            ("provider_evidence", "evidence_id"),
        ):
            for row in self.connection.execute(f"SELECT * FROM {table}"):
                row = dict(row)
                if row[key] not in ordinary:
                    continue
                known = (
                    row.get("available_at")
                    or row.get("verified_at")
                    or row.get("known_at")
                    or row.get("finished_at")
                    or row.get("started_at")
                )
                if cutoff and known and known > timestamp(cutoff):
                    raise ValueError("Future source cannot enter past review")
                if row["expires_at"]:
                    expiries.append(datetime.fromisoformat(row["expires_at"]))
        # Observations may have a valid extended-statistics permission; choose longest valid copy.
        observation_expiries = {}
        for row in self.connection.execute(
            "SELECT o.observation_id,o.available_at,s.expires_at FROM video_observations o "
            "JOIN source_records s USING(source_id) UNION ALL "
            "SELECT o.observation_id,o.available_at,s.expires_at FROM channel_observations o "
            "JOIN source_records s USING(source_id) UNION ALL "
            "SELECT h.observation_id,h.available_at,MIN(h.expires_at,p.expires_at) "
            "FROM statistical_history h JOIN retention_permissions p USING(permission_id)"
        ):
            if row[0] in ordinary:
                if cutoff and row[1] > timestamp(cutoff):
                    raise ValueError("Future capture cannot enter past review")
                observation_expiries[row[0]] = max(observation_expiries.get(row[0], row[2]), row[2])
        expiries.extend(datetime.fromisoformat(t) for t in observation_expiries.values())
        return min(expiries) if expiries else None

    def put(self, annotation: Annotation):
        annotation = Annotation.model_validate(annotation.model_dump(mode="json"))
        if annotation.decided_at > self.history.clock():
            raise ValueError("Cannot store future review")
        if annotation.expires_at <= self.history.clock():
            raise AnalysisUnavailable("policy_permission_required", "Review already expired")
        dependencies = references(annotation)
        expiry = self.validate(dependencies, annotation.available_at)
        if expiry and annotation.expires_at > expiry:
            raise ValueError("Annotation cannot outlive retained dependencies")
        p = annotation.payload
        review_material_ids = {m.material_id for m in annotation.materials}
        for field in ("demand_evidence_ids", "reviewed_alternative_ids"):
            if not set(getattr(p, field, ())) <= set(dependencies) | review_material_ids:
                raise ValueError(
                    "Gap evidence IDs need retained dependencies or reviewed materials"
                )
        node_requirements = {n: "topic_family" for n in getattr(p, "family_node_ids", ())}
        if getattr(p, "premise_node_id", None):
            node_requirements[p.premise_node_id] = "video_premise"
        nodes = {
            r["node_id"]: r
            for r in self.connection.execute(
                "SELECT * FROM taxonomy_nodes WHERE taxonomy_version=? AND available_at<=?",
                (annotation.boundary.taxonomy_version, timestamp(annotation.available_at)),
            )
        }
        scoped = set(annotation.boundary.node_ids)
        for _ in range(6):
            scoped.update(n for n, row in nodes.items() if row["parent_id"] in scoped)
        if any(
            n not in scoped or nodes[n]["level"] != level for n, level in node_requirements.items()
        ):
            raise ValueError(
                "Premise must use known in-boundary taxonomy nodes at the correct level"
            )
        if dependencies:
            reviews = self.read_many(dependencies, annotation.available_at, missing_ok=True)
            if any(a.boundary != annotation.boundary for a in reviews):
                raise ValueError("Cross-boundary review dependencies are forbidden")
        provider_ids = set(getattr(p, "provider_evidence_ids", ())) | set(
            getattr(p, "provider_similarity_ids", ())
        )
        matched_provider = set()
        for row in self.connection.execute("SELECT * FROM provider_evidence"):
            if row["evidence_id"] in dependencies:
                body = json.loads(row["record_json"])
                claims = body.get("claims", [])
                allowed = {
                    "channel_id",
                    "video_id",
                    "title",
                    "transcript_metadata",
                    "comment_metadata",
                    "faceless",
                    "spoken_language",
                    "category",
                    "format",
                    "taxonomy_labels",
                    "semantic_similarity",
                    "format_similarity",
                    "thumbnail_similarity",
                }
                if not claims or any(c.get("field") not in allowed for c in claims):
                    raise ValueError("Provider financial/opaque evidence is forbidden in Phase 5")
                if row["evidence_id"] in provider_ids and not any(
                    c.get("trust_class") == "T4"
                    and c.get("field")
                    in {"semantic_similarity", "format_similarity", "thumbnail_similarity"}
                    for c in claims
                ):
                    raise ValueError("Similarity evidence must remain T4")
                matched_provider.add(row["evidence_id"])
                for claim in claims:
                    value = claim.get("value")
                    if (
                        isinstance(value, dict)
                        and value.get("retention_state") == "contract_review_required"
                    ):
                        raise ValueError(
                            "Restricted provider text needs contract review before derivation"
                        )
                for m in annotation.materials:
                    if m.kind in {"comment", "transcript"}:
                        text_deadline = datetime.fromisoformat(
                            body["fetch_at"].replace("Z", "+00:00")
                        )
                        from datetime import timedelta

                        if annotation.expires_at > text_deadline + timedelta(seconds=3600):
                            raise ValueError(
                                "Provider text derivation exceeds one-hour material TTL"
                            )
        if not provider_ids <= matched_provider:
            raise ValueError("Similarity IDs must reference retained T4 provider evidence")
        if annotation.source_type == "provider" and not matched_provider:
            raise ValueError("Provider annotations require retained provider evidence")
        for m in annotation.materials:
            if m.permission_id:
                permission = self.connection.execute(
                    "SELECT source,verified_at FROM retention_permissions WHERE permission_id=?",
                    (m.permission_id,),
                ).fetchone()
                if not permission or permission[1] > timestamp(annotation.available_at):
                    raise ValueError("Text/media permission must precede review availability")
                if matched_provider and not permission[0].startswith("nexlev"):
                    raise ValueError(
                        "Unrelated statistical acceptance cannot authorize provider text"
                    )
        body = annotation.model_dump(mode="json")
        digest = identity(body, self.history.secrets)
        with atomic(self.connection):
            old = self.connection.execute(
                "SELECT input_hash FROM qualitative_annotations WHERE annotation_id=?",
                (annotation.annotation_id,),
            ).fetchone()
            if old:
                if old[0] != digest:
                    raise ValueError("Immutable annotation ID cannot be rewritten")
                return annotation
            self.connection.execute(
                "INSERT INTO qualitative_annotations VALUES(?,?,?,?,?,?,?)",
                (
                    annotation.annotation_id,
                    annotation.version,
                    timestamp(annotation.available_at),
                    timestamp(annotation.decided_at),
                    timestamp(annotation.expires_at),
                    digest,
                    safe_json(body, self.history.secrets),
                ),
            )
        return annotation

    def read_many(self, ids, cutoff, *, missing_ok=False):
        wanted = set(ids)
        found = tuple(
            Annotation.model_validate_json(r["annotation_json"])
            for r in self.connection.execute(
                "SELECT * FROM qualitative_annotations ORDER BY annotation_id"
            )
            if r["annotation_id"] in wanted
        )
        if not missing_ok and len(found) != len(wanted):
            raise AnalysisUnavailable("policy_permission_required", "Review removed or unavailable")
        self.validate(tuple(a.annotation_id for a in found), cutoff)
        return found
