"""Enumerate and freeze candidates before outcomes. No view/output-success filter."""

import json
from datetime import datetime

from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.models import (
    Candidate,
    CohortDefinition,
    CohortMember,
    MembershipState,
    Subject,
)
from youtube_niche_mcp.eligibility.rules import age_band
from youtube_niche_mcp.services.safety import identity, safe_json

M = MembershipState


class CohortBuilder:
    def __init__(self, eligibility):
        self.eligibility = eligibility
        self.history = eligibility.history
        self.connection = eligibility.connection

    def nodes(self, definition):
        boundary = definition.boundary
        rows = self.connection.execute(
            """SELECT node_id,parent_id FROM taxonomy_nodes
            WHERE taxonomy_version=? AND available_at<=?""",
            (boundary.taxonomy_version, timestamp(definition.known_at)),
        ).fetchall()
        available = {row[0] for row in rows}
        if not set(boundary.node_ids) <= available:
            raise ValueError("Boundary requires known taxonomy nodes")
        nodes = set(boundary.node_ids)
        if boundary.include_descendants:
            changed = True
            while changed:
                before = len(nodes)
                nodes.update(row[0] for row in rows if row[1] in nodes)
                changed = len(nodes) != before
        return nodes

    def routes(self, subject, at):
        # Preserve each known, still-retained occurrence, even duplicate query ranks.
        return tuple(
            dict(row)
            for row in self.connection.execute(
                """SELECT r.run_id,r.rank,r.page_number,r.page_rank,
            d.query,d.route,d.provider,d.sort_order,d.filters_json FROM discovery_results r
            JOIN discovery_runs d USING(run_id) WHERE result_id=? AND result_type=?
            AND r.available_at<=?
            AND d.expires_at>? ORDER BY r.run_id,r.rank""",
                (
                    subject.entity_id,
                    subject.entity_kind,
                    timestamp(at),
                    timestamp(self.history.clock()),
                ),
            )
        )

    def video_state(self, subject, definition, at, nodes):
        decisions, evidence, uncertainties, problems = [], [], [], []
        capture = self.history.latest("video", subject.entity_id, at)
        if capture is None:
            return (
                M.INSUFFICIENT,
                "No known publication evidence",
                None,
                decisions,
                evidence,
                uncertainties,
                None,
            )
        evidence.append(capture["observation_id"])
        date_conflicts = [
            c
            for c in self.history.conflicts("video", subject.entity_id, at)
            if c["field"] in {"publication_at", "channel_id"}
        ]
        if date_conflicts:
            problems.append((M.CONFLICT, "Publication/identity source conflict"))
            evidence.extend(c["conflict_id"] for c in date_conflicts)
        metadata = json.loads(capture["metadata_json"])
        pub = metadata.get("publication_at")
        channel = metadata.get("channel_id")
        if pub is None or pub > timestamp(at):
            problems.append((M.INSUFFICIENT, "Public publication clock unavailable"))
        elif (
            not timestamp(definition.publication_start)
            <= pub
            < timestamp(definition.publication_end)
        ):
            problems.append((M.EXCLUDED, "Outside declared publication window"))
        memberships = [
            (mid, m)
            for mid, m in self.eligibility.memberships(
                subject, definition.boundary.taxonomy_version, at
            )
            if m.node_id in nodes and m.rule_version == definition.boundary.classifier_version
        ]
        evidence.extend(mid for mid, _ in memberships)
        if not memberships:
            problems.append((M.PENDING, "Niche membership unknown"))
        else:
            by_node = {}
            for _, m in memberships:
                by_node.setdefault(m.node_id, set()).add(m.state)
            if any("included" in states and "excluded" in states for states in by_node.values()):
                problems.append((M.CONFLICT, "Niche classifiers disagree"))
            elif not any(m.state == "included" for _, m in memberships):
                if any(m.state == "uncertain" for _, m in memberships):
                    uncertainties.append("Uncertain niche membership")
                else:
                    problems.append((M.EXCLUDED, "Explicitly outside niche boundary"))
        requirements = (
            (definition.long_form_rule, {"duration_eligible"}, {"below_threshold"}),
            (
                definition.format_rule,
                {"standard_vod_confirmed", "probable_vod"},
                {"short_form_confirmed"},
            ),
            (
                definition.live_rule,
                {"ordinary_vod"} | ({"archived_live"} if definition.allow_archived_live else set()),
                {"currently_live", "scheduled_live"}
                | (set() if definition.allow_archived_live else {"archived_live"}),
            ),
            (
                definition.language_rule,
                {"verified_english", "likely_english"},
                {"non_english", "mixed_language"},
            ),
            (
                definition.faceless_rule,
                {"verified_faceless", "likely_faceless"},
                {"host_central", "hybrid"},
            ),
        )
        for rule, allowed, excluded in requirements:
            result = self.eligibility.latest(subject, rule, at)
            if result is None:
                problems.append((M.PENDING, rule + ": no known decision"))
                continue
            did, d = result
            decisions.append(did)
            evidence.extend(d.evidence_ids)
            if d.state.value == "conflicting":
                problems.append((M.CONFLICT, rule + ": preserved source conflict"))
            elif d.label in excluded:
                problems.append((M.EXCLUDED, rule + ": " + d.label))
            elif d.label not in allowed:
                problems.append((M.PENDING, rule + ": unresolved " + d.label))
            elif d.state.value != "verified":
                uncertainties.append(rule + ": " + d.state.value)
        if problems:
            priority = {M.CONFLICT: 0, M.EXCLUDED: 1, M.INSUFFICIENT: 2, M.PENDING: 3}
            state = min(problems, key=lambda p: priority[p[0]])[0]
            return (
                state,
                "; ".join(reason for _, reason in problems),
                pub,
                decisions,
                evidence,
                uncertainties,
                channel,
            )
        if uncertainties:
            state = M.UNCERTAIN if definition.include_uncertain else M.PENDING
            return (
                state,
                "Eligibility has declared uncertainty",
                pub,
                decisions,
                evidence,
                uncertainties,
                channel,
            )
        return (
            M.INCLUDED,
            "Declared video eligibility satisfied",
            pub,
            decisions,
            evidence,
            uncertainties,
            channel,
        )

    def member(self, candidate, definition, nodes):
        subject = candidate.subject
        at = definition.known_at
        entry_status = {}
        problems = []
        decisions = []
        evidence = []
        uncertainties = []
        expected = "video" if definition.kind == "eligible_long_form" else "channel"
        if subject.entity_kind != expected:
            raise ValueError("Candidate kind does not match cohort constructor")
        if definition.kind == "entrant":
            if candidate.entry_known_at is None or candidate.entry_known_at > at:
                problems.append(
                    (M.PENDING, "Entrant requires eligibility landmark known by freeze time")
                )
            else:
                at = candidate.entry_known_at
        if subject.entity_kind == "video":
            state, reason, pub, decisions, evidence, uncertainties, channel = self.video_state(
                subject, definition, at, nodes
            )
        else:
            channel = subject.entity_id
            choices = []
            for row in self.connection.execute(
                "SELECT video_id FROM videos WHERE first_seen_at<=?", (timestamp(at),)
            ):
                vid = Subject(entity_kind="video", entity_id=row[0])
                capture = self.history.latest("video", vid.entity_id, at)
                if capture and json.loads(capture["metadata_json"]).get("channel_id") == channel:
                    result = self.video_state(vid, definition, at, nodes)
                    choices.append((vid, result))
            acceptable = [(vid, res) for vid, res in choices if res[0] in {M.INCLUDED, M.UNCERTAIN}]
            if acceptable:
                vid, res = min(acceptable, key=lambda choice: (choice[1][2], choice[0].entity_id))
                state, reason, pub, decisions, evidence, uncertainties, _ = res
                entry_status = {"qualifying_video_id": vid.entity_id}
            else:
                state = M.INSUFFICIENT
                reason = "No known qualifying video"
                if choices:
                    # Preserve unsuccessful candidates and their evidence.
                    states = {res[0] for _, res in choices}
                    state = (
                        M.CONFLICT
                        if M.CONFLICT in states
                        else M.PENDING
                        if M.PENDING in states
                        else M.INSUFFICIENT
                        if M.INSUFFICIENT in states
                        else M.EXCLUDED
                    )
                    for _, res in choices:
                        decisions.extend(res[3])
                        evidence.extend(res[4])
                        uncertainties.extend(res[5])
                    reason += "; " + "; ".join(res[1] for _, res in choices)
            if definition.kind == "small_channel":
                size = self.eligibility.latest(subject, definition.small_rule, at)
                if not size:
                    problems.append((M.PENDING, "Current-size classification unavailable"))
                else:
                    did, d = size
                    decisions.append(did)
                    evidence.extend(d.evidence_ids)
                    entry_status["current_size_label"] = d.label
                    if d.state.value == "conflicting":
                        problems.append((M.CONFLICT, "Current-size sources disagree"))
                    elif d.label == "known_not_small":
                        problems.append((M.EXCLUDED, "Outside current-small threshold"))
                    elif d.label in {"hidden", "unknown", "threshold_uncertain"}:
                        uncertainties.append("Current subscriber size " + d.label)
            if definition.kind == "entrant":
                # Do not use the first eligible video inside the requested window as entry.
                # Scan the known catalog without the publication-window restriction first.
                full = definition.model_copy(
                    update={
                        "publication_start": datetime(1970, 1, 1, tzinfo=at.tzinfo),
                        "publication_end": at,
                    }
                )
                earlier = []
                for vid, _ in choices:
                    result = self.video_state(vid, full, at, nodes)
                    if result[0] in {M.INCLUDED, M.UNCERTAIN}:
                        earlier.append((vid, result))
                if earlier:
                    first_vid, first = min(
                        earlier, key=lambda choice: (choice[1][2], choice[0].entity_id)
                    )
                    entry = first[2]
                    entry_date = datetime.fromisoformat(entry)
                    entry_status.update(
                        {
                            "first_observed_niche_entry": entry,
                            "entry_known_at": timestamp(at),
                            "qualifying_video_id": first_vid.entity_id,
                            "niche_entry_age_band": age_band(entry_date, definition.known_at),
                            "earlier_history": "unknown_hidden_deleted_private",
                            "rule_version": definition.entry_rule,
                        }
                    )
                    decisions.extend(first[3])
                    evidence.extend(first[4])
                    uncertainties.append(
                        "Earlier hidden/deleted/private niche participation unknown"
                    )
                    if not definition.entry_start <= entry_date < definition.entry_end:
                        problems.append(
                            (
                                M.EXCLUDED,
                                "First observed qualifying entry outside declared entry window",
                            )
                        )
                else:
                    problems.append(
                        (M.INSUFFICIENT, "First observed qualifying niche entry unavailable")
                    )
        if problems:
            # A missing entry landmark cannot be rescued by today's otherwise eligible catalog.
            state = problems[0][0]
            reason += "; " + "; ".join(r for _, r in problems)
        elif uncertainties and state == M.INCLUDED:
            state = M.UNCERTAIN if definition.include_uncertain else M.PENDING
        independence = (
            self.eligibility.independence(channel, at)
            if channel
            else {"unit": "unknown:" + subject.entity_id, "state": "unknown"}
        )
        if independence["state"] == "unknown":
            uncertainties.append(
                "Creator ownership relation unknown; canonical channel is provisional unit"
            )
        return CohortMember(
            subject=subject,
            state=state,
            reason=reason,
            exclusion_reason=reason if state == M.EXCLUDED else None,
            evidence_ids=tuple(sorted(set(evidence))),
            decision_ids=tuple(sorted(set(decisions))),
            entry_status=entry_status,
            discovery_occurrences=self.routes(subject, definition.known_at),
            independence_unit=independence["unit"],
            independence_state=independence["state"],
            uncertainties=tuple(sorted(set(uncertainties))),
        )

    def freeze(self, definition: CohortDefinition, candidates: tuple[Candidate, ...]):
        definition = CohortDefinition.model_validate(definition.model_dump(mode="json"))
        canonical = {}
        for candidate in candidates:
            candidate = Candidate.model_validate(candidate.model_dump(mode="json"))
            key = (candidate.subject.entity_kind, candidate.subject.entity_id)
            if key in canonical and canonical[key] != candidate:
                raise ValueError("Duplicate candidate has conflicting entry landmarks")
            canonical[key] = candidate
        frame = tuple(canonical[k] for k in sorted(canonical))
        body = safe_json(definition.model_dump(mode="json"), self.history.secrets)
        digest = identity([c.model_dump(mode="json") for c in frame], self.history.secrets)
        with atomic(self.connection):
            old = self.connection.execute(
                "SELECT definition_json,candidates_hash,expires_at "
                "FROM cohort_definitions WHERE cohort_id=?",
                (definition.cohort_id,),
            ).fetchone()
            if old:
                if old[0] != body or old[1] != digest:
                    raise ValueError("Frozen cohort ID cannot be redefined")
                return self.read(definition.cohort_id)
            nodes = self.nodes(definition)
            members = tuple(self.member(c, definition, nodes) for c in frame)
            # Frozen labels do not bypass input-specific retention. Internal independent
            # annotations/configuration can persist; externally derived frames are bounded.
            expiry = []
            for member in members:
                for did in member.decision_ids:
                    expiry.append(
                        self.connection.execute(
                            "SELECT expires_at FROM eligibility_decisions WHERE decision_id=?",
                            (did,),
                        ).fetchone()[0]
                    )
                for eid in member.evidence_ids:
                    conflict = self.connection.execute(
                        """SELECT l.expires_at,r.expires_at
                        FROM source_conflicts c
                        JOIN source_records l ON c.left_source_id=l.source_id
                        JOIN source_records r ON c.right_source_id=r.source_id
                        WHERE conflict_id=?""",
                        (eid,),
                    ).fetchone()
                    if conflict:
                        expiry.extend(conflict)
                    for table, key in (
                        ("source_records", "source_id"),
                        ("classification_claims", "evidence_id"),
                        ("niche_memberships", "membership_id"),
                    ):
                        row = self.connection.execute(
                            f"SELECT expires_at FROM {table} WHERE {key}=?", (eid,)
                        ).fetchone()
                        if row and row[0]:
                            expiry.append(row[0])
                    for table in ("channel_observations", "video_observations"):
                        row = self.connection.execute(
                            f"SELECT expires_at FROM {table} JOIN source_records USING(source_id) "
                            "WHERE observation_id=?",
                            (eid,),
                        ).fetchone()
                        if row:
                            expiry.append(row[0])
                for route in member.discovery_occurrences:
                    expiry.append(
                        self.connection.execute(
                            "SELECT expires_at FROM discovery_runs WHERE run_id=?",
                            (route["run_id"],),
                        ).fetchone()[0]
                    )
            expires = min(expiry, default=None)
            self.connection.execute(
                "INSERT INTO cohort_definitions VALUES(?,?,?,?,?,?,?)",
                (
                    definition.cohort_id,
                    timestamp(definition.created_at),
                    timestamp(definition.known_at),
                    definition.research_run,
                    body,
                    digest,
                    expires,
                ),
            )
            for member in members:
                self.connection.execute(
                    "INSERT INTO cohort_memberships VALUES(?,?,?,?,?)",
                    (
                        definition.cohort_id,
                        member.subject.entity_kind,
                        member.subject.entity_id,
                        member.state.value,
                        safe_json(member.model_dump(mode="json"), self.history.secrets),
                    ),
                )
        return members

    def read(self, cohort_id: str):
        row = self.connection.execute(
            "SELECT expires_at FROM cohort_definitions WHERE cohort_id=?", (cohort_id,)
        ).fetchone()
        if not row:
            raise ValueError("Frozen cohort unavailable")
        if row[0] is not None and row[0] <= timestamp(self.history.clock()):
            raise ValueError("Frozen cohort inputs exceeded permitted retention")
        return tuple(
            CohortMember.model_validate_json(row[0])
            for row in self.connection.execute(
                "SELECT member_json FROM cohort_memberships WHERE cohort_id=? "
                "ORDER BY entity_kind,entity_id",
                (cohort_id,),
            )
        )
