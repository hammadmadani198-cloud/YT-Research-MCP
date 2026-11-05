"""Public projections of validated shared-service results."""

import json
from collections import defaultdict

from youtube_niche_mcp.analysis.numerics import json_numbers
from youtube_niche_mcp.decision.sorting import sort_runs, sorting_index
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.models import CohortDefinition, Subject
from youtube_niche_mcp.eligibility.rules import classify
from youtube_niche_mcp.tools.errors import PublicError
from youtube_niche_mcp.tools.metadata import declared_country
from youtube_niche_mcp.tools.research import BUDGETS
from youtube_niche_mcp.tools.schemas import PublicResult
from youtube_niche_mcp.tools.serialization import card, page, project

DIMENSIONS = {
    "geo_language": (),
    "outliers": ("F1", "F2", "F5", "floor", "F6", "F7", "F20"),
    "content_gaps": ("content_gaps", "saturation", "F15", "source_to_story", "faceless_production"),
    "packaging": ("packaging_patterns", "content_gaps", "saturation"),
    "audience_demand": ("F3", "F4", "F8", "F9", "F11", "F14", "F19", "content_gaps"),
    "sustainability": (
        "F7",
        "F8",
        "F11",
        "F13",
        "F15",
        "F16",
        "series_continuation_structure",
        "source_to_story",
        "faceless_production",
    ),
    "risk": (
        "rights_legal",
        "platform_policy",
        "factual_editorial",
        "F16",
        "faceless_production",
        "F23",
    ),
    "history": ("F10", "F11", "F12", "F13", "F20", "F21"),
}


def provider_context(engine, subjects, fields, at):
    """Allowlisted non-financial claims only; provider estimates never canonical metrics."""
    now = timestamp(engine.history.clock())
    rows = engine.c.execute(
        "SELECT e.record_json,e.evidence_id,e.run_id FROM provider_evidence e "
        "JOIN provider_runs r USING(run_id) JOIN source_records s USING(source_id) "
        "WHERE e.available_at<=? AND e.observed_at<=? AND e.expires_at>? "
        "AND r.expires_at>? AND s.expires_at>? ORDER BY e.evidence_id LIMIT 1001",
        (timestamp(at), timestamp(at), now, now, now),
    ).fetchall()
    if len(rows) > 1000:
        raise PublicError("budget_exceeded")
    items = []
    for row in rows:
        body = json.loads(row[0])
        subject = body["subject"]
        if (subject["entity_kind"], subject["entity_id"]) not in subjects:
            continue
        for claim in body["claims"]:
            if claim["field"] not in fields:
                continue
            items.append(
                {
                    "subject": subject,
                    "field": claim["field"],
                    "value": claim["value"],
                    "provider": "nexlev",
                    "route": body["route"],
                    "observed_at": body["observed_at"],
                    "state": claim["state"],
                    "run_id": row[2],
                    "evidence_id": row[1],
                    "interpretation": "provider_estimate_context_only"
                    if claim["trust_class"] == "T5"
                    else "provider_derived_context_only"
                    if claim["trust_class"] == "T4"
                    else "provider_claim_requires_verification",
                    "retention_state": "contract_review_required",
                    "canonical_metric": False,
                }
            )
    return items


def overview(engine, research_id, *, reused=True, focus=None, request=None, sorting=None):
    decision, base, metrics, frame = engine.context(research_id)
    d = metrics["decision"].details
    f18 = metrics["F18"].model_dump(mode="json")
    selected = (
        DIMENSIONS[focus]
        if focus in DIMENSIONS
        else sorted(set(metrics) - {"decision", "F17", "F18"})
    )
    cards = [
        card(metrics[f], engine.history.secrets, include_details=focus is not None)
        for f in selected
        if f in metrics
    ]
    history = d.get("history_maturity", {})
    history_summary = {k: v for k, v in history.items() if k != "measurements"}
    robustness = {k: v for k, v in f18["details"].items() if k not in {"matrix", "grade_rule"}}
    mode = decision.run.options.sensitivity.mode
    counts = defaultdict(int)
    for m in frame.members:
        counts[m.state.value] += 1
    data = {
        "mode": mode,
        "budget": BUDGETS[mode],
        "budget_meaning": "exploratory ceilings, not statistical guarantees",
        "coverage": {
            "candidate_channels": len(frame.members),
            "eligible_channels": sum(
                m.state.value in {"included", "included_with_uncertainty"} for m in frame.members
            ),
            "candidate_videos": len(frame.videos),
            "eligible_videos": sum(
                v.membership.state.value in {"included", "included_with_uncertainty"}
                for v in frame.videos
            ),
            "entrant_channels": sum(bool(m.entry_status) for m in frame.members),
            "channel_states": dict(counts),
        },
        "recommendation_state": d["state"],
        "creator_fit": project(d.get("creator_fit", {})),
        "discovery_coverage": project(d.get("evidence", {}).get("routes", {})),
        "history_maturity": project(history_summary),
        "sensitivity_warnings": project(d.get("sensitivity_warnings", [])),
        "missing_dimensions": [f for f in selected if f not in metrics],
        "public_analytics_only": True,
    }
    if sorting:
        data["sorting_only_F17"] = json_numbers(
            sorting_index(
                metrics, sorting, essential_evidence_complete=not d.get("insufficiency_gates")
            )
        )
        data["sorting_configuration"] = sorting.model_dump(mode="json")
    items = []
    state = d["state"]
    if focus == "history":
        states = {metrics[f].state for f in DIMENSIONS["history"] if f in metrics}
        state = (
            "available"
            if "available" in states
            else "provider_history_only"
            if "provider_history_only" in states
            else "history_unavailable"
        )
    if focus in {"content_gaps", "packaging"}:
        gaps = metrics.get("content_gaps")
        items = list(gaps.details.get("gaps", [])) if gaps else []
        from youtube_niche_mcp.qualitative.repository import ReviewRepository

        annotations = ReviewRepository(engine.history).read_many(
            tuple(r["annotation_id"] for r in items), base.run.options.cutoff
        )
        by_id = {a.annotation_id: a for a in annotations}
        items = [
            {
                **r,
                "review": project(by_id[r["annotation_id"]].payload.model_dump(mode="json")),
                "evidence_strength": by_id[r["annotation_id"]].source_type,
                "differentiation_path": {"state": "not_retained_by_scoped_review", "value": None},
                "topic_nodes": list(by_id[r["annotation_id"]].boundary.node_ids),
            }
            for r in items
            if r["annotation_id"] in by_id
        ]
        if focus == "packaging":
            items = [r for r in items if r.get("scope") == "packaging"]
    if focus == "outliers":
        floor = metrics.get("F5")
        for o in sorted(base.outcomes, key=lambda o: (-(o.value or 0), o.video_id)):
            if o.state != "available" or (
                o.value < base.run.options.goal and o.video_id != base.run.options.candidate_id
            ):
                continue
            f1 = metrics.get("F1")
            canonical_f1 = f1 if f1 and f1.details.get("candidate_id") == o.video_id else None
            f7 = metrics.get("F7")
            items.append(
                {
                    "video_id": o.video_id,
                    "channel_id": o.channel_id,
                    "state": "candidate_hit"
                    if o.value >= base.run.options.goal
                    else "relative_outlier_candidate",
                    "absolute_goal_attained": o.value >= base.run.options.goal,
                    "absolute_reach": o.value,
                    "age_days": base.run.options.age_days,
                    "relative_lift_F1": str(canonical_f1.value)
                    if canonical_f1 and canonical_f1.value is not None
                    else None,
                    "F1_state": canonical_f1.state
                    if canonical_f1
                    else "no_candidate_specific_baseline",
                    "baseline": str(canonical_f1.denominator - 1)
                    if canonical_f1 and canonical_f1.denominator is not None
                    else None,
                    "baseline_landmark": base.run.options.baseline_cutoff.isoformat()
                    if canonical_f1 and base.run.options.baseline_cutoff
                    else None,
                    "ordinary_channel_floor": json_numbers(
                        floor.details.get("channel_floors", {}).get(o.channel_id)
                    )
                    if floor
                    else None,
                    "followup_F7": project(f7.details)
                    if f7 and f7.details.get("anchor_id") == o.video_id
                    else {"state": "anchor_specific_history_unavailable"},
                    "post_hit_F20": project(metrics["F20"].details)
                    if "F20" in metrics
                    and getattr(
                        engine.repository.read(
                            decision.run.options.historical_run_ids[0]
                        ).run.options,
                        "anchor_id",
                        None,
                    )
                    == o.video_id
                    else {"state": "anchor_specific_history_unavailable"},
                    "publication_at": o.publication_at.isoformat() if o.publication_at else None,
                    "outcome_observed_at": o.observed_at.isoformat() if o.observed_at else None,
                    "observation_id": o.observation_id,
                }
            )
        subjects = {("video", i["video_id"]) for i in items} | {
            ("channel", i["channel_id"]) for i in items if i["channel_id"]
        }
        data["provider_outlier_context"] = project(
            provider_context(engine, subjects, {"outlier_score"}, base.run.options.cutoff)
        )
        data["interpretation"] = "Candidate hits alone do not establish niche quality."
    if focus == "geo_language":
        subjects = [("video", v.video_id) for v in frame.videos] + [
            ("channel", m.subject.entity_id) for m in frame.members
        ]
        for kind, sid in subjects:
            subject = Subject(entity_kind=kind, entity_id=sid)
            at = frame.video_freeze_at if kind == "video" else frame.freeze_at
            known = engine.eligibility.latest(subject, "spoken_language_v1", at)
            claims = engine.eligibility.claims(subject, at, "spoken_language")
            classification = (
                known[1]
                if known
                else classify(subject, "spoken_language_v1", claims, decided_at=at)
            )
            capture = engine.history.latest(kind, sid, at)
            metadata = json.loads(capture["metadata_json"]) if capture else {}
            items.append(
                {
                    "subject": {"entity_kind": kind, "entity_id": sid},
                    "spoken_language": {
                        "state": classification.state.value,
                        "label": classification.label,
                    },
                    "language_evidence": [
                        {
                            "basis": c.basis,
                            "value": c.value,
                            "source": c.source,
                            "observed_at": c.observed_at.isoformat(),
                        }
                        for c in claims
                    ],
                    "metadata_language": {
                        "default_audio_language": metadata.get("default_audio_language"),
                        "default_language": metadata.get("default_language"),
                    },
                    "declared_country": declared_country(engine.history, sid)
                    if kind == "channel"
                    else {"state": "not_channel_subject", "value": None},
                    "audience_country": {"state": "not_publicly_available", "value": None},
                }
            )
        data["provider_geography_language_context"] = project(
            provider_context(
                engine,
                set(subjects),
                {"geography", "spoken_language", "audio_language", "transcript_metadata"},
                base.run.options.cutoff,
            )
        )
        data["limitations"] = [
            (
                "Title/subtitle language and declared country do not "
                "establish spoken language or audience location."
            ),
            (
                "Declared country, when retained, is short-lived current metadata "
                "context, separate from the frozen language and outcome frame."
            ),
        ]
    if focus == "risk":
        data["risk_dimensions"] = {
            "rights_reuse": "rights_legal",
            "platform_policy": "platform_policy",
            "factual_editorial": "factual_editorial",
            "production_dependency": "faceless_production",
            "capacity": "creator_fit",
            "policy_freshness": project(d.get("evidence", {}).get("policy", {})),
        }
    if request is not None:
        items, cursor = page(items, request, [research_id, focus])
    else:
        items, cursor = items[:10], None
    warnings = [
        "Descriptive researched-frame evidence; no creator-success probability.",
        "Focused details are bounded; raw transcripts/comments are withheld.",
    ]
    if (
        len(frame.members) < BUDGETS[mode]["channels"][0]
        or len(frame.videos) < BUDGETS[mode]["videos"][0]
    ):
        warnings.append("Available frame is below the approximate mode research target.")
    return PublicResult(
        state=state,
        summary="Retained multi-axis research with explicit confidence and missingness.",
        research_id=research_id,
        reused_run=reused,
        boundary=project(decision.run.boundary.model_dump(mode="json")),
        metrics=cards,
        evidence=items,
        confidence={
            "level": metrics["F18"].state,
            "F18": project(robustness),
            "history_maturity": project(history_summary),
            "critical_missing_evidence": project(d.get("insufficiency_gates", [])),
            "sensitivity_flags": project(d.get("sensitivity_warnings", [])),
        },
        supports=project(d.get("supports", [])),
        concerns=project(d.get("concerns", [])),
        unknowns=project(d.get("unknowns", [])),
        warnings=warnings,
        provenance={
            "decision_run_id": research_id,
            "analysis_run_ids": list(decision.run.options.analysis_run_ids),
            "cohort_id": base.run.cohort_id,
            "video_cohort_id": base.run.video_cohort_id,
            "taxonomy_node_ids": list(frame.boundary.node_ids),
            "cutoff": base.run.options.cutoff.isoformat(),
            "input_hash": decision.run.input_hash,
            "versions": {
                "decision": decision.run.formula_version,
                "core": base.run.formula_version,
            },
        },
        data=data,
        next_cursor=cursor,
        next_available_actions=[
            "youtube_niche_compare",
            "youtube_niche_content_gaps",
            "youtube_niche_history",
            "youtube_niche_risk",
        ],
    )


def comparable(engine, ids):
    contexts = [engine.context(rid) for rid in ids]
    signatures = []
    for decision, base, _, _ in contexts:
        definitions = [
            CohortDefinition.model_validate_json(
                engine.c.execute(
                    "SELECT definition_json FROM cohort_definitions WHERE cohort_id=?", (cid,)
                ).fetchone()[0]
            )
            for cid in (base.run.cohort_id, base.run.video_cohort_id)
        ]
        signatures.append(
            (
                decision.run.options.sensitivity.mode,
                base.run.options.age_days,
                base.run.options.goal,
                base.run.options.tolerance_seconds,
                decision.run.options.rubric.model_dump(mode="json"),
                tuple(
                    getattr(base.run.options, k)
                    for k in (
                        "low_threshold",
                        "own_minimum",
                        "peer_video_minimum",
                        "peer_channel_minimum",
                        "pooling_k",
                        "breadth_k",
                        "classification_minimum",
                        "exposure_days",
                        "first_k",
                        "independence_policy",
                        "missing_policy",
                        "quantile_version",
                        "observation_policy",
                    )
                ),
                *[
                    (
                        d.kind,
                        d.long_form_rule,
                        d.small_rule,
                        d.allow_archived_live,
                        d.include_uncertain,
                        d.format_rule,
                        d.live_rule,
                        d.language_rule,
                        d.faceless_rule,
                        d.publication_end - d.publication_start,
                        d.entry_end - d.entry_start if d.entry_end and d.entry_start else None,
                    )
                    for d in definitions
                ],
            )
        )
    if any(s != signatures[0] for s in signatures[1:]):
        raise PublicError("incompatible_runs")
    return contexts


def comparison_confidence(confidence):
    """Keep canonical F18 states/counts/scope without repeating evidence rosters."""
    f18 = confidence["F18"]
    components = {}
    for name, item in f18.get("components", {}).items():
        if name == "sensitivity":
            components[name] = {
                family: {k: v for k, v in values.items() if k in {"state", "planned", "comparable"}}
                for family, values in item.items()
                if isinstance(values, dict)
            }
        elif isinstance(item, dict):
            components[name] = {
                k: v for k, v in item.items() if v is None or isinstance(v, (str, int, float, bool))
            }
    return {
        **confidence,
        "F18": {
            k: v
            for k, v in f18.items()
            if k
            in {
                "confidence",
                "assessment_scope",
                "consistent_specifications",
                "comparable_specifications",
                "planned_specifications",
                "specification_agreement",
                "warning",
            }
        }
        | {"components": components},
    }


def compare(engine, request):
    comparable(engine, request.research_ids)
    rows = []
    for rid in request.research_ids:
        result = overview(engine, rid, sorting=request.sorting)
        rows.append(
            {
                "research_id": rid,
                "boundary": result.boundary,
                "state": result.state,
                "confidence": comparison_confidence(result.confidence),
                "axes": {
                    m.dimension: {
                        "state": m.state,
                        "value": m.value,
                        "mature": m.mature,
                        "pending": m.pending,
                        "unknown": m.unknown,
                    }
                    for m in result.metrics
                },
                "creator_fit": result.data["creator_fit"],
                "sorting_only_F17": result.data.get("sorting_only_F17"),
                "provenance": result.provenance,
            }
        )
    if request.sorting:
        order = sort_runs(
            [{"run_id": r["research_id"], "value": r["sorting_only_F17"]["value"]} for r in rows]
        )
        by_id = {r["research_id"]: r for r in rows}
        rows = [by_id[r["run_id"]] for r in order]
    return PublicResult(
        state="available",
        summary="Descriptive multi-axis comparison of compatible research runs.",
        evidence=rows,
        data={
            "winner": None,
            "confidence_detail": (
                "Component states/counts retained; "
                "research and focused tools provide evidence detail."
            ),
            "sorting_configuration": request.sorting.model_dump(mode="json")
            if request.sorting
            else None,
        },
        warnings=["Confidence and maturity differ by row. F17 never changes recommendation state."],
        provenance={"decision_run_ids": list(request.research_ids)},
    )


def discover(engine, request):
    now = timestamp(engine.history.clock())
    nodes = engine.c.execute(
        (
            "SELECT node_id,taxonomy_version,label,level FROM "
            "taxonomy_nodes WHERE available_at<=? AND "
            "instr(lower(label),lower(?))>0 ORDER BY "
            "taxonomy_version,node_id LIMIT 1001"
        ),
        (now, request.query),
    ).fetchall()
    if request.taxonomy_version:
        nodes = [n for n in nodes if n[1] == request.taxonomy_version]
    if len(nodes) > 1000:
        raise PublicError("budget_exceeded")
    memberships = engine.c.execute(
        (
            "SELECT "
            "entity_kind,entity_id,node_id,taxonomy_version,membership_json"
            " FROM niche_memberships WHERE available_at<=? AND "
            "decided_at<=? AND (expires_at IS NULL OR expires_at>?) ORDER"
            " BY membership_id LIMIT 20001"
        ),
        (now, now, now),
    ).fetchall()
    if len(memberships) > 20000:
        raise PublicError("budget_exceeded")
    routes = engine.c.execute(
        (
            "SELECT "
            "d.result_id,d.result_type,r.run_id,r.route,r.provider,r.query,r.language,r.outcome,r.mode,r.filters_json"
            " FROM discovery_results d JOIN discovery_runs r "
            "USING(run_id) WHERE d.available_at<=? AND d.observed_at<=? "
            "AND r.started_at<=? AND r.expires_at>? ORDER BY "
            "r.run_id,d.rank LIMIT 20001"
        ),
        (now, now, now, now),
    ).fetchall()
    if len(routes) > 20000:
        raise PublicError("budget_exceeded")
    captured = engine.c.execute(
        "WITH ranked AS (SELECT o.video_id,o.metadata_json,ROW_NUMBER() OVER "
        "(PARTITION BY o.video_id ORDER BY o.observed_at DESC,o.available_at DESC,"
        "o.observation_id) n "
        "FROM video_observations o JOIN source_records s USING(source_id) WHERE "
        "o.observed_at<=? AND o.available_at<=? AND s.expires_at>?) "
        "SELECT video_id,metadata_json FROM ranked WHERE n=1 LIMIT 20001",
        (now, now, now),
    ).fetchall()
    if len(captured) > 20000:
        raise PublicError("budget_exceeded")
    channel_map = {r[0]: json.loads(r[1]).get("channel_id") for r in captured}
    taxonomy = engine.c.execute(
        "SELECT node_id,taxonomy_version,parent_id FROM taxonomy_nodes "
        "WHERE available_at<=? LIMIT 10001",
        (now,),
    ).fetchall()
    if len(taxonomy) > 10000:
        raise PublicError("budget_exceeded")
    children = defaultdict(set)
    for row in taxonomy:
        children[(row[2], row[1])].add(row[0])
    boundary_map = engine.boundaries()
    entrant_rows = engine.c.execute(
        "SELECT d.definition_json,m.member_json FROM cohort_definitions d "
        "JOIN cohort_memberships m USING(cohort_id) WHERE d.known_at<=? AND d.created_at<=? "
        "AND (d.expires_at IS NULL OR d.expires_at>?) ORDER BY d.cohort_id,m.entity_id LIMIT 20001",
        (now, now, now),
    ).fetchall()
    if len(entrant_rows) > 20000:
        raise PublicError("budget_exceeded")
    entrants = defaultdict(set)
    for row in entrant_rows:
        definition = CohortDefinition.model_validate_json(row[0])
        member = json.loads(row[1])
        if definition.kind == "entrant" and member["state"] in {
            "included",
            "included_with_uncertainty",
        }:
            entrants[definition.boundary.boundary_id].add(member["subject"]["entity_id"])
    candidates = []
    for node in nodes:
        descendants, pending = set(), [node[0]]
        while pending:
            nid = pending.pop()
            if nid not in descendants:
                descendants.add(nid)
                pending.extend(children[(nid, node[1])])
        subjects = {(m[0], m[1]) for m in memberships if m[2] in descendants and m[3] == node[1]}
        found_routes = {
            r[2]: {
                "run_id": r[2],
                "route": r[3],
                "provider": r[4],
                "query": r[5],
                "language": r[6],
                "coverage_state": r[7],
                "weak_case_declared": "weak" in (r[3] + r[5] + r[8]).lower()
                or bool(json.loads(r[9]).get("weak_case")),
            }
            for r in routes
            if (r[1], r[0]) in subjects
        }
        boundaries = [
            bid
            for bid, b in boundary_map.items()
            if node[0] in b.node_ids and b.taxonomy_version == node[1]
        ]
        candidates.append(
            {
                "taxonomy_node_id": node[0],
                "taxonomy_version": node[1],
                "label": node[2],
                "level": node[3],
                "boundary_ids": boundaries,
                "candidate_channel_count": len(
                    {sid for kind, sid in subjects if kind == "channel"}
                    | {
                        channel_map[sid]
                        for kind, sid in subjects
                        if kind == "video" and channel_map.get(sid)
                    }
                ),
                "candidate_video_count": len({sid for kind, sid in subjects if kind == "video"}),
                "evidence_routes": list(found_routes.values()),
                "weak_case_route_present": any(
                    r["weak_case_declared"] for r in found_routes.values()
                ),
                "recent_entrant_evidence": {
                    "state": "observed_frozen_frames"
                    if any(b in entrants for b in boundaries)
                    else "unknown",
                    "channel_count": len(set().union(*(entrants[b] for b in boundaries)))
                    if any(b in entrants for b in boundaries)
                    else None,
                    "scope": "declared frozen entrant windows; not current creator census",
                },
                "initial_evidence_state": "candidate_evidence" if subjects else "taxonomy_only",
                "coverage_limitations": [
                    (
                        "Selected routes are not a creator census; zero "
                        "search/provider results do not establish absence."
                    )
                ],
            }
        )
    candidates, cursor = page(
        candidates, request, ["discover", request.query, request.taxonomy_version, request.mode]
    )
    return PublicResult(
        state="available" if candidates else "insufficient_evidence",
        summary="Candidate taxonomy and route evidence; no opportunity ranking.",
        evidence=candidates,
        next_cursor=cursor,
        data={"mode": request.mode, "budget": BUDGETS[request.mode], "ranking": "none"},
        next_available_actions=["youtube_niche_research"],
        warnings=["A candidate is not a supported niche until full research is performed."],
    )
