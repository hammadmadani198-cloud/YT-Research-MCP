"""Versioned labels and claims, gated by availability AND present retention validity."""

import json
from datetime import datetime, timedelta

from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.models import (
    Claim,
    Classification,
    NicheMembership,
    Subject,
    TaxonomyNode,
)
from youtube_niche_mcp.eligibility.rules import REGISTRY, age_band, claim_id, classify
from youtube_niche_mcp.services.safety import identity, safe_json

FOREVER = "9999-12-31T23:59:59.999999+00:00"
LEVELS = ("category", "niche", "sub_niche", "micro_niche", "topic_family", "video_premise")


class EligibilityRepository:
    def __init__(self, history):
        self.history = history
        self.connection = history.connection

    def _insert(self, table, key_column, key, columns, values):
        # Table/column names are internal constants, never external parameters.
        with atomic(self.connection):
            existing = self.connection.execute(
                f"SELECT {','.join(columns)} FROM {table} WHERE {key_column}=?", (key,)
            ).fetchone()
            if existing:
                if tuple(existing) != tuple(values):
                    raise ValueError("Immutable record replay differs")
                return key
            self.connection.execute(
                f"INSERT INTO {table}({key_column},{','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in range(len(values) + 1))})",
                (key, *values),
            )
        return key

    def register_rules(self):
        with atomic(self.connection):
            for rule in REGISTRY.values():
                self._insert(
                    "eligibility_rules",
                    "rule_id",
                    rule.rule_id,
                    ("decision_type", "rule_json"),
                    (rule.decision_type, safe_json(rule.model_dump(mode="json"))),
                )

    def append_claim(self, claim: Claim) -> str:
        claim = Claim.model_validate(claim.model_dump(mode="json"))
        expires = claim.expires_at
        if claim.data_origin != "independent_annotation":
            cap = claim.observed_at + timedelta(days=30)
            if expires is not None and expires > cap:
                raise ValueError("External claim retention requires a verified integration")
            expires = cap if expires is None else expires
        if expires is not None and expires <= claim.available_at:
            raise ValueError("Claim expired before availability")
        for did in claim.supporting_decision_ids:
            row = self.connection.execute(
                "SELECT * FROM eligibility_decisions WHERE decision_id=?", (did,)
            ).fetchone()
            if (
                not row
                or row["available_at"] > timestamp(claim.available_at)
                or row["decided_at"] > timestamp(claim.available_at)
            ):
                raise ValueError("Supporting decision unavailable at annotation")
            if row["expires_at"] <= timestamp(self.history.clock()):
                raise ValueError("Supporting decision expired")
            if expires is None or row["expires_at"] < timestamp(expires):
                expires = datetime.fromisoformat(row["expires_at"])
        if claim.subject.entity_kind == "channel" and claim.field == "faceless":
            for vid in claim.reviewed_video_ids:
                capture = self.history.latest("video", vid, claim.available_at)
                if (
                    not capture
                    or json.loads(capture["metadata_json"]).get("channel_id")
                    != claim.subject.entity_id
                ):
                    raise ValueError("Reviewed eligible video must belong to the annotated channel")
        claim = Claim.model_validate({**claim.model_dump(mode="json"), "expires_at": expires})
        body = safe_json(claim.model_dump(mode="json"), self.history.secrets)
        eid = claim_id(claim)
        with atomic(self.connection):
            self.history.ensure_entity(
                claim.subject.entity_kind, claim.subject.entity_id, claim.available_at
            )
            self._insert(
                "classification_claims",
                "evidence_id",
                eid,
                (
                    "entity_kind",
                    "entity_id",
                    "field",
                    "source",
                    "observed_at",
                    "available_at",
                    "expires_at",
                    "claim_json",
                ),
                (
                    claim.subject.entity_kind,
                    claim.subject.entity_id,
                    claim.field,
                    claim.source,
                    timestamp(claim.observed_at),
                    timestamp(claim.available_at),
                    timestamp(expires) if expires else None,
                    body,
                ),
            )
        return eid

    def claims(self, subject: Subject, at: datetime, field: str | None = None):
        args = [
            subject.entity_kind,
            subject.entity_id,
            timestamp(at),
            timestamp(at),
            timestamp(self.history.clock()),
        ]
        query = """SELECT claim_json FROM classification_claims WHERE entity_kind=? AND entity_id=?
                   AND observed_at<=? AND available_at<=?
                   AND (expires_at IS NULL OR expires_at>?)"""
        if field is not None:
            query += " AND field=?"
            args.append(field)
        query += " ORDER BY available_at, evidence_id"
        return tuple(
            Claim.model_validate_json(row[0]) for row in self.connection.execute(query, args)
        )

    def evidence_expiry(self, ids, subject: Subject, at: datetime, *, field: str | None = None):
        expiries = []
        for eid in ids:
            row = self.connection.execute(
                "SELECT * FROM classification_claims WHERE evidence_id=?", (eid,)
            ).fetchone()
            if (
                row is None
                or row["entity_kind"] != subject.entity_kind
                or row["entity_id"] != subject.entity_id
            ):
                raise ValueError("Preserved subject evidence required")
            if row["available_at"] > timestamp(at) or row["observed_at"] > timestamp(at):
                raise ValueError("Future evidence cannot enter a classification")
            if field is not None and row["field"] != field:
                raise ValueError("Evidence field does not support this classification")
            if row["expires_at"] is not None:
                if row["expires_at"] <= max(timestamp(at), timestamp(self.history.clock())):
                    raise ValueError("Expired evidence cannot enter a classification")
                expiries.append(row["expires_at"])
        return min(expiries, default=None)

    def evaluate(self, subject: Subject, rule: str, *, at: datetime) -> tuple[str, Classification]:
        claims = self.claims(subject, at)
        # A later capture from the same source is a revision/history, not a
        # simultaneous source disagreement. Equal-clock contradictory claims remain.
        latest = {}
        for c in claims:
            key = (c.field, c.source, c.basis)
            latest[key] = max(
                latest.get(key, (c.observed_at, c.available_at)), (c.observed_at, c.available_at)
            )
        claims = tuple(
            c
            for c in claims
            if (c.observed_at, c.available_at) == latest[(c.field, c.source, c.basis)]
        )
        decision = classify(subject, rule, claims, decided_at=at)
        return self.record_decision(decision), decision

    def record_decision(self, decision: Classification):
        decision = Classification.model_validate(decision.model_dump(mode="json"))
        if REGISTRY[decision.rule_version].decision_type != decision.decision_type:
            raise ValueError("Decision type differs from immutable rule")
        field = {
            "long_form": "duration_seconds",
            "current_small": "subscriber_count",
            "creator_independence": "creator_relation",
        }.get(decision.decision_type, decision.decision_type)
        self.evidence_expiry(
            decision.evidence_ids, decision.subject, decision.decided_at, field=field
        )
        expires = self.evidence_expiry(decision.evidence_ids, decision.subject, decision.decided_at)
        if expires is not None and (
            decision.expires_at is None or timestamp(decision.expires_at) > expires
        ):
            raise ValueError("Decision cannot outlive restricted inputs")
        if decision.evidence_ids:
            claims = [
                Claim.model_validate_json(
                    self.connection.execute(
                        "SELECT claim_json FROM classification_claims WHERE evidence_id=?", (eid,)
                    ).fetchone()[0]
                )
                for eid in decision.evidence_ids
            ]
            if decision.available_at < max(
                c.available_at for c in claims
            ) or decision.observed_at < max(c.observed_at for c in claims):
                raise ValueError("Decision provenance precedes evidence")
            if decision.permission_state == "permitted" and not all(
                c.permission_state == "permitted" for c in claims
            ):
                raise ValueError("Decision cannot confer permission on restricted data")
            expected = classify(
                decision.subject,
                decision.rule_version,
                tuple(claims),
                decided_at=decision.decided_at,
            )
            if (decision.label, decision.state, decision.conflicts) != (
                expected.label,
                expected.state,
                expected.conflicts,
            ):
                raise ValueError("Decision does not follow its declared evidence/rule version")
        body = safe_json(decision.model_dump(mode="json"), self.history.secrets)
        did = identity(decision.model_dump(mode="json"), self.history.secrets)
        subject = decision.subject
        with atomic(self.connection):
            self.register_rules()
            self.history.ensure_entity(
                subject.entity_kind, subject.entity_id, decision.available_at
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO eligibility_decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    did,
                    subject.entity_kind,
                    subject.entity_id,
                    decision.decision_type,
                    decision.state.value,
                    decision.confidence,
                    decision.source,
                    decision.reason,
                    decision.rule_version,
                    timestamp(decision.observed_at),
                    timestamp(decision.available_at),
                    timestamp(decision.decided_at),
                    timestamp(decision.expires_at) if decision.expires_at else expires or FOREVER,
                ),
            )
            self._insert(
                "classification_details",
                "decision_id",
                did,
                ("rule_id", "label", "classification_json"),
                (decision.rule_version, decision.label, body),
            )
        return did

    def latest(self, subject: Subject, rule: str, at: datetime):
        row = self.connection.execute(
            """SELECT d.decision_id,c.classification_json FROM eligibility_decisions d
            JOIN classification_details c USING(decision_id)
            WHERE entity_kind=? AND entity_id=? AND rule_version=?
            AND observed_at<=? AND available_at<=? AND decided_at<=? AND expires_at>?
            ORDER BY decided_at DESC, decision_id DESC LIMIT 1""",
            (
                subject.entity_kind,
                subject.entity_id,
                rule,
                *([timestamp(at)] * 3),
                timestamp(self.history.clock()),
            ),
        ).fetchone()
        return (row[0], Classification.model_validate_json(row[1])) if row else None

    def add_node(self, node: TaxonomyNode):
        node = TaxonomyNode.model_validate(node.model_dump(mode="json"))
        if node.parent_id:
            parent = self.connection.execute(
                "SELECT level,available_at FROM taxonomy_nodes "
                "WHERE node_id=? AND taxonomy_version=?",
                (node.parent_id, node.taxonomy_version),
            ).fetchone()
            if (
                not parent
                or LEVELS.index(parent["level"]) >= LEVELS.index(node.level)
                or parent["available_at"] > timestamp(node.available_at)
            ):
                raise ValueError("Earlier higher-level parent in same taxonomy required")
        body = safe_json(node.model_dump(mode="json"), self.history.secrets)
        with atomic(self.connection):
            old = self.connection.execute(
                "SELECT node_json FROM taxonomy_nodes WHERE node_id=? AND taxonomy_version=?",
                (node.node_id, node.taxonomy_version),
            ).fetchone()
            if old and old[0] != body:
                raise ValueError("Taxonomy changes require a new version")
            self.connection.execute(
                "INSERT OR IGNORE INTO taxonomy_nodes VALUES(?,?,?,?,?,?,?)",
                (
                    node.node_id,
                    node.taxonomy_version,
                    node.label,
                    node.level,
                    node.parent_id,
                    timestamp(node.available_at),
                    body,
                ),
            )

    def assign_niche(self, membership: NicheMembership):
        membership = NicheMembership.model_validate(membership.model_dump(mode="json"))
        expires = self.evidence_expiry(
            membership.evidence_ids,
            membership.subject,
            membership.available_at,
            field="niche_membership",
        )
        node = self.connection.execute(
            "SELECT available_at FROM taxonomy_nodes WHERE node_id=? AND taxonomy_version=?",
            (membership.node_id, membership.taxonomy_version),
        ).fetchone()
        if not node or node[0] > timestamp(membership.available_at):
            raise ValueError("Taxonomy node was unavailable at assignment")
        for eid in membership.evidence_ids:
            claim = Claim.model_validate_json(
                self.connection.execute(
                    "SELECT claim_json FROM classification_claims WHERE evidence_id=?", (eid,)
                ).fetchone()[0]
            )
            if (
                not isinstance(claim.value, dict)
                or claim.value.get("node_id") != membership.node_id
                or claim.value.get("state") != membership.state
            ):
                raise ValueError("Membership must preserve the supporting node/state claim")
        body = membership.model_dump(mode="json")
        mid = identity(body, self.history.secrets)
        return self._insert(
            "niche_memberships",
            "membership_id",
            mid,
            (
                "entity_kind",
                "entity_id",
                "node_id",
                "taxonomy_version",
                "source",
                "rule_version",
                "decided_at",
                "available_at",
                "expires_at",
                "membership_json",
            ),
            (
                membership.subject.entity_kind,
                membership.subject.entity_id,
                membership.node_id,
                membership.taxonomy_version,
                membership.source,
                membership.rule_version,
                timestamp(membership.decided_at),
                timestamp(membership.available_at),
                expires,
                safe_json(body, self.history.secrets),
            ),
        )

    def memberships(self, subject: Subject, version: str, at: datetime):
        rows = self.connection.execute(
            """SELECT membership_id,membership_json FROM niche_memberships
            WHERE entity_kind=? AND entity_id=?
            AND taxonomy_version=? AND available_at<=? AND decided_at<=?
            AND (expires_at IS NULL OR expires_at>?)
            ORDER BY decided_at DESC, membership_id""",
            (
                subject.entity_kind,
                subject.entity_id,
                version,
                timestamp(at),
                timestamp(at),
                timestamp(self.history.clock()),
            ),
        )
        latest = {}
        for mid, body in rows:
            m = NicheMembership.model_validate_json(body)
            latest.setdefault((m.node_id, m.source, m.rule_version), (mid, m))
        return tuple(latest.values())

    def group_channel(self, group_id: str, display_label: str, group_kind: str, evidence_id: str):
        safe_json([group_id, display_label, group_kind], self.history.secrets)
        row = self.connection.execute(
            "SELECT claim_json,expires_at FROM classification_claims WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()
        if not row:
            raise ValueError("Documented grouping evidence required")
        c = Claim.model_validate_json(row[0])
        if (
            c.subject.entity_kind != "channel"
            or c.field != "creator_relation"
            or c.basis
            not in {"public_disclosure", "shared_company", "explicit_network", "documented_source"}
            or c.value != group_id
        ):
            raise ValueError(
                "Style similarity/provider inference cannot establish creator ownership"
            )
        if row[1] and row[1] <= timestamp(self.history.clock()):
            raise ValueError("Grouping evidence expired")
        mid = identity([group_id, c.subject.entity_id, evidence_id])
        with atomic(self.connection):
            self._insert(
                "creator_groups",
                "group_id",
                group_id,
                ("display_label", "group_kind"),
                (display_label, group_kind),
            )
            self._insert(
                "creator_group_memberships",
                "membership_id",
                mid,
                ("group_id", "channel_id", "evidence_id", "available_at", "expires_at"),
                (group_id, c.subject.entity_id, evidence_id, timestamp(c.available_at), row[1]),
            )
        return mid

    def independence(self, channel_id: str, at: datetime):
        rows = self.connection.execute(
            """SELECT DISTINCT group_id FROM creator_group_memberships WHERE channel_id=?
            AND available_at<=? AND (expires_at IS NULL OR expires_at>?) ORDER BY group_id""",
            (channel_id, timestamp(at), timestamp(self.history.clock())),
        ).fetchall()
        groups = {row[0] for row in rows}
        if not groups:
            return {"unit": "channel:" + channel_id, "state": "unknown", "groups": []}
        # Known overlapping groups are a connected component, not independent groups.
        changed = True
        while changed:
            changed = False
            for row in self.connection.execute(
                """SELECT channel_id,group_id FROM creator_group_memberships
                WHERE available_at<=? AND (expires_at IS NULL OR expires_at>?)""",
                (timestamp(at), timestamp(self.history.clock())),
            ):
                if row[1] in groups:
                    linked = self.connection.execute(
                        """SELECT group_id FROM creator_group_memberships WHERE channel_id=?
                        AND available_at<=? AND (expires_at IS NULL OR expires_at>?)""",
                        (row[0], timestamp(at), timestamp(self.history.clock())),
                    )
                    before = len(groups)
                    groups.update(r[0] for r in linked)
                    changed |= len(groups) != before
        return {
            "unit": "group:" + min(groups),
            "state": "documented_group",
            "groups": sorted(groups),
        }

    def clocks(self, channel_id: str, version: str, node_ids: set[str], at: datetime):
        channel = self.history.latest("channel", channel_id, at)
        account = (
            json.loads(channel["metadata_json"]).get("account_created_at") if channel else None
        )
        canonical = self.connection.execute(
            "SELECT first_seen_at FROM channels WHERE channel_id=? AND first_seen_at<=?",
            (channel_id, timestamp(at)),
        ).fetchone()
        visible, eligible, niche = [], [], []
        evidence = []
        for row in self.connection.execute(
            "SELECT video_id FROM videos WHERE first_seen_at<=?", (timestamp(at),)
        ):
            vid = row[0]
            capture = self.history.latest("video", vid, at)
            if not capture:
                continue
            metadata = json.loads(capture["metadata_json"])
            if metadata.get("channel_id") != channel_id or not metadata.get("publication_at"):
                continue
            pub = metadata["publication_at"]
            if pub > timestamp(at):
                continue
            visible.append(pub)
            evidence.append(capture["observation_id"])
            subject = Subject(entity_kind="video", entity_id=vid)
            lf = self.latest(subject, "long_form_v1_8m", at)
            surface = self.latest(subject, "surface_format_v1", at)
            live = self.latest(subject, "live_status_v1", at)
            if (
                lf
                and lf[1].label == "duration_eligible"
                and lf[1].state.value == "verified"
                and surface
                and surface[1].label in {"standard_vod_confirmed", "probable_vod"}
                and live
                and live[1].label == "ordinary_vod"
                and surface[1].state.value != "conflicting"
                and live[1].state.value != "conflicting"
            ):
                eligible.append(pub)
            ms = self.memberships(subject, version, at)
            if any(m.node_id in node_ids and m.state == "included" for _, m in ms):
                niche.append(pub)
        result = {
            "account_created_at": account,
            "first_visible_upload": min(visible, default=None),
            "first_observed_eligible_long_form": min(eligible, default=None),
            "first_observed_niche_entry": min(niche, default=None),
            "first_mcp_discovery": canonical[0] if canonical else None,
            "earlier_history": "unknown_hidden_deleted_private",
            "evidence_ids": evidence,
        }
        entry = datetime.fromisoformat(result["first_observed_niche_entry"]) if niche else None
        result["niche_entry_age_band"] = age_band(entry, at)
        result["clock_states"] = {
            key: "observed" if result[key] is not None else "insufficient_history"
            for key in (
                "account_created_at",
                "first_visible_upload",
                "first_observed_eligible_long_form",
                "first_observed_niche_entry",
                "first_mcp_discovery",
            )
        }
        return result

    def aggregate_faceless(self, channel_id: str, *, at: datetime):
        """Aggregate known video reviews in the observed eligible catalog, with coverage."""
        subject = Subject(entity_kind="channel", entity_id=channel_id)
        total = []
        reviewed = []
        decisions = []
        labels = set()
        for row in self.connection.execute(
            "SELECT video_id FROM videos WHERE first_seen_at<=?", (timestamp(at),)
        ):
            vid = Subject(entity_kind="video", entity_id=row[0])
            capture = self.history.latest("video", vid.entity_id, at)
            if not capture or json.loads(capture["metadata_json"]).get("channel_id") != channel_id:
                continue
            lf = self.latest(vid, "long_form_v1_8m", at)
            surface = self.latest(vid, "surface_format_v1", at)
            live = self.latest(vid, "live_status_v1", at)
            if not (
                lf
                and lf[1].label == "duration_eligible"
                and surface
                and surface[1].label in {"standard_vod_confirmed", "probable_vod"}
                and live
                and live[1].label == "ordinary_vod"
                and all(x[1].state.value != "conflicting" for x in (lf, surface, live))
            ):
                continue
            total.append(vid.entity_id)
            decision = self.latest(vid, "faceless_v1", at)
            if decision and decision[1].state.value == "verified":
                reviewed.append(vid.entity_id)
                decisions.append(decision[0])
                labels.add(decision[1].label)
        label = "unknown"
        if labels:
            label = (
                "faceless"
                if labels == {"verified_faceless"}
                else "host_central"
                if labels == {"host_central"}
                else "hybrid"
            )
        c = Claim(
            subject=subject,
            field="faceless",
            value=label,
            basis="human_review",
            source="derived:observed-channel-reviews",
            source_version="faceless_v1",
            observed_at=at,
            available_at=at,
            reason="Stored video reviews aggregated within the observed eligible catalog",
            complete_review=bool(total) and len(reviewed) == len(total),
            reviewed_video_ids=tuple(reviewed),
            eligible_video_count=len(total),
            supporting_decision_ids=tuple(decisions),
        )
        self.append_claim(c)
        return self.evaluate(subject, "faceless_v1", at=at)
