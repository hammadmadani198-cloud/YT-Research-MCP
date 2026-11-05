"""Evidence-led descriptive axes, never a weighted score or recommendation."""

from collections import Counter, defaultdict, deque
from decimal import Decimal

from youtube_niche_mcp.analysis.numerics import quantile, ratio


def typed(annotations, kind):
    return [a for a in annotations if a.payload.kind == kind]


def checked_sources(annotations):
    return {
        a.annotation_id: a
        for a in typed(annotations, "source")
        if a.source_type == "human"
        and a.payload.checked
        and a.payload.accessible is True
        and a.payload.credible is True
    }


def source_to_story(annotations):
    reviews = typed(annotations, "source")
    sources = checked_sources(annotations)
    families = Counter(a.payload.source_family for a in sources.values())
    return {
        "state": "reviewed_sample"
        if any(a.source_type == "human" and a.payload.checked for a in reviews)
        else "unknown",
        "checked_credible_accessible_ids": sorted(sources),
        "unverified_or_weak_ids": sorted(
            a.annotation_id for a in reviews if a.annotation_id not in sources
        ),
        "categories": sorted({a.payload.category for a in sources.values()}),
        "primary_source_ids": sorted(i for i, a in sources.items() if a.payload.primary is True),
        "secondary_source_ids": sorted(i for i, a in sources.items() if a.payload.primary is False),
        "source_families": dict(families),
        "single_source_family_dependency": len(families) == 1 if sources else None,
        "single_fragile_source_dependency": any(
            a.payload.fragility == "fragile" for a in sources.values()
        )
        if len(families) == 1 and all(a.payload.fragility != "unknown" for a in sources.values())
        else False
        if len(families) > 1
        else None,
        "source_fragility_reviews": {i: a.payload.fragility for i, a in sources.items()},
        "freshness": {
            i: a.payload.fresh_through.isoformat() if a.payload.fresh_through else None
            for i, a in sources.items()
        },
        "limitations": ["Checked pages are not a quality score; unreviewed sources are unknown"],
    }


def idea_feasibility(annotations, generated):
    sources = checked_sources(annotations)
    reviews = typed(annotations, "premise")
    candidates = defaultdict(list)
    for a in reviews:
        if a.payload.candidate_id not in generated:
            raise ValueError("Reviewed premise absent from generated candidate inventory")
        candidates[a.payload.candidate_id].append(a)
    validated, unsupported, conflicts = {}, [], []
    for cid, rows in candidates.items():
        human = [a for a in rows if a.source_type == "human"]
        bodies = {a.payload.model_dump_json() for a in human}
        if len(bodies) > 1:
            conflicts.append(cid)
            continue
        if not human:
            continue
        p = human[0].payload
        supported = bool(p.source_annotation_ids) and set(p.source_annotation_ids) <= sources.keys()
        if not supported:
            unsupported.append(cid)
        if supported and all(
            (
                p.subject.strip(),
                p.viewer_promise.strip(),
                p.mechanism.strip(),
                p.long_form_treatment.strip(),
                p.production_path.strip(),
                p.family_node_ids,
            )
        ):
            validated[cid] = human[0]
    parent = {cid: cid for cid in validated}

    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i

    relations = defaultdict(set)
    auxiliary = []
    for a in typed(annotations, "relation"):
        p = a.payload
        if not {p.left_candidate_id, p.right_candidate_id} <= set(generated):
            raise ValueError("Premise relation outside generated inventory")
        if a.source_type == "human":
            relations[tuple(sorted((p.left_candidate_id, p.right_candidate_id)))].add(p.relation)
        else:
            auxiliary.append(a.annotation_id)
    uncertain = []
    for pair, states in relations.items():
        if len(states) != 1 or "uncertain" in states:
            uncertain.append(list(pair))
        elif states == {"near_duplicate"} and set(pair) <= parent.keys():
            parent[root(pair[1])] = root(pair[0])
    # Exact reviewed premise identity does not count title rewrites as distinct ideas.
    keys = {}
    for cid, a in validated.items():
        p = a.payload
        key = tuple(
            " ".join(s.casefold().split())
            for s in (p.subject, p.viewer_promise, p.mechanism, p.long_form_treatment)
        )
        if key in keys:
            parent[root(cid)] = root(keys[key])
        keys[key] = cid
    clusters = defaultdict(list)
    for cid in sorted(validated):
        clusters[root(cid)].append(cid)
    for pair, states in relations.items():
        if (
            set(pair) <= parent.keys()
            and root(pair[0]) == root(pair[1])
            and states != {"near_duplicate"}
        ):
            uncertain.append(list(pair))
    families = sorted({f for a in validated.values() for f in a.payload.family_node_ids})
    humans = {a.payload.candidate_id for a in reviews if a.source_type == "human"}
    finalist_unreviewed = sorted(
        {a.payload.candidate_id for a in reviews if a.payload.finalist} - humans
    )
    missing = sorted(set(generated) - validated.keys())
    n, d = len(clusters), len(generated)
    indeterminate = bool(uncertain or conflicts)
    return {
        "state": "unknown"
        if not candidates
        else "source_conflict"
        if indeterminate
        else "partial_coverage"
        if missing
        else "available"
        if d
        else "unknown",
        "value": None if indeterminate or not candidates else ratio(n, d),
        "numerator": None if indeterminate or not candidates else n,
        "denominator": d,
        "validated_distinct_count": None if indeterminate else n,
        "validated_candidate_ids": sorted(validated),
        "viable_families": families,
        "distinct_clusters": sorted(clusters.values()),
        "duplicate_density": None if indeterminate else ratio(len(validated) - n, len(validated)),
        "source_supported_ids": sorted(validated),
        "unsupported_ids": sorted(unsupported),
        "unvalidated_ids": missing,
        "classification_coverage": ratio(len(candidates), d),
        "human_review_count": len(humans),
        "human_minimum_10_met": len(humans) >= 10,
        "review_warnings": ([] if len(humans) >= 10 else ["Fewer than ten human premise reviews"])
        + (["Every finalist needs human review"] if finalist_unreviewed else []),
        "unreviewed_finalists": finalist_unreviewed,
        "finite_inventory_ids": sorted(
            cid for cid, a in validated.items() if a.payload.finite_inventory
        ),
        "recurring_entities": sorted(
            {e for a in validated.values() for e in a.payload.recurring_entities}
        ),
        "uncertain_relations": uncertain,
        "conflicting_premise_ids": conflicts,
        "provider_model_relation_ids_auxiliary": auxiliary,
        "source_to_story_yield": ratio(len(validated), len(candidates)),
        "limitations": [
            "30 candidates is a research planning example, not a universal threshold",
            "Validation is a reviewed feasibility judgment, not a success forecast",
        ],
    }


def content_gaps(annotations):
    sources = checked_sources(annotations)
    rows = []
    for a in typed(annotations, "gap"):
        p = a.payload
        if p.demand == "absent" or (p.demand == "positive" and not p.demand_evidence_ids):
            state = "insufficient_demand_evidence"
        elif p.supply == "unknown" or not p.reviewed_alternative_ids:
            state = "insufficient_supply_evidence"
        elif p.supply == "served":
            state = "saturated"
        elif p.differentiated is False or p.feasible_production is False:
            state = "insufficient_differentiation"
        elif p.demand == "unknown":
            state = "insufficient_demand_evidence"
        elif p.demand == "comment_only" or a.source_type != "human":
            state = "possible_gap"
        elif (
            p.differentiated is True
            and p.feasible_production is True
            and p.source_annotation_ids
            and set(p.source_annotation_ids) <= sources.keys()
        ):
            state = "supported_gap"
        else:
            state = "possible_gap"
        rows.append(
            {
                "annotation_id": a.annotation_id,
                "scope": p.scope,
                "state": state,
                "demand_ids": list(p.demand_evidence_ids),
                "supply_ids": list(p.reviewed_alternative_ids),
            }
        )
    return {
        "state": "reviewed_sample" if rows else "unknown",
        "gaps": rows,
        "limitations": [
            "Few videos alone cannot establish a gap",
            "Content, packaging and production gaps remain separate",
        ],
    }


def packaging_patterns(annotations):
    rows = typed(annotations, "packaging")
    mechanisms = Counter(m for a in rows for m in a.payload.title_mechanisms)
    thumbnails = [a for a in rows if a.payload.thumbnail_reviewed]
    layouts = Counter(a.payload.composition for a in thumbnails if a.payload.composition)
    return {
        "state": "reviewed_sample" if rows else "unknown",
        "title_mechanisms": dict(mechanisms),
        "title_length_median": quantile(
            [a.payload.title_length for a in rows if a.payload.title_length is not None]
        ),
        "promise_structures": dict(
            Counter(a.payload.promise_structure for a in rows if a.payload.promise_structure)
        ),
        "thumbnail_review_count": len(thumbnails),
        "unreviewed_thumbnails": len(rows) - len(thumbnails),
        "face_patterns": dict(Counter(a.payload.face for a in thumbnails)),
        "dominant_assets": dict(Counter(a.payload.dominant_asset for a in thumbnails)),
        "text_density": dict(Counter(a.payload.text_density for a in thumbnails)),
        "compositions": dict(layouts),
        "emotional_devices": dict(
            Counter(a.payload.emotional_device for a in thumbnails if a.payload.emotional_device)
        ),
        "provider_similarity_ids_T4": sorted(
            {i for a in rows for i in a.payload.provider_similarity_ids}
        ),
        "limitations": [
            "Public patterns and T4 similarity do not reveal CTR or private performance"
        ],
    }


def series_structure(annotations, generated):
    links = typed(annotations, "continuation")
    edges, rows = defaultdict(set), []
    for a in links:
        p = a.payload
        if not {p.from_candidate, p.to_candidate} <= set(generated):
            raise ValueError("Continuation outside declared candidate inventory")
        reviewed = a.source_type == "human" and p.compatible is True and not p.playlist_only
        if reviewed:
            edges[p.from_candidate].add(p.to_candidate)
        rows.append(
            {
                "annotation_id": a.annotation_id,
                "from": p.from_candidate,
                "to": p.to_candidate,
                "structure": p.structure,
                "reviewed_compatible": reviewed,
                "exhaustible": p.exhaustible,
                "playlist_only": p.playlist_only,
            }
        )
    nodes = set(edges) | {n for targets in edges.values() for n in targets}
    indegrees = {n: 0 for n in nodes}
    for targets in edges.values():
        for n in targets:
            indegrees[n] += 1
    pending = deque(sorted(n for n in nodes if indegrees[n] == 0))
    depths = dict.fromkeys(nodes, 1)
    visited = 0
    while pending:
        node = pending.popleft()
        visited += 1
        for target in sorted(edges[node]):
            depths[target] = max(depths[target], depths[node] + 1)
            indegrees[target] -= 1
            if indegrees[target] == 0:
                pending.append(target)
    cycle = visited != len(nodes)
    depth_value = max(depths.values(), default=0)
    return {
        "state": "reviewed_sample" if rows else "unknown",
        "links": rows,
        "continuation_depth": None if cycle else depth_value,
        "cycle_present": cycle,
        "compatible_link_count": sum(len(v) for v in edges.values()),
        "structures": dict(Counter(r["structure"] for r in rows)),
        "finite_exhaustible_concern": any(r["exhaustible"] is True for r in rows),
        "limitations": [
            "Continuation structure is not evidence of binge retention or audience overlap"
        ],
    }


def saturation(annotations, contextual):
    relations = typed(annotations, "relation")
    premises = typed(annotations, "premise")
    outcomes = defaultdict(list)
    for bundle in contextual:
        for o in bundle.outcomes:
            if o.state == "available":
                outcomes[o.video_id].append(
                    {
                        "analysis_run_id": bundle.run.run_id,
                        "age_days": bundle.run.options.age_days,
                        "cutoff": bundle.run.options.cutoff.isoformat(),
                        "observed_at": o.observed_at.isoformat(),
                        "observed_views": o.value,
                        "observation_id": o.observation_id,
                        "declared_goal": bundle.run.options.goal,
                        "goal_state": "hit" if o.value >= bundle.run.options.goal else "miss",
                    }
                )
    rows = []
    for a in premises:
        p = a.payload
        rows.append(
            {
                "candidate_id": p.candidate_id,
                "publication_at": p.publication_at.isoformat() if p.publication_at else None,
                "observed_outcomes": outcomes.get(p.outcome_video_id, []),
            }
        )
    return {
        "state": "reviewed_sample" if relations else "unknown",
        "premise_chronology_outcomes": rows,
        "canonical_near_duplicate_pairs": [
            a.payload.model_dump(mode="json")
            for a in relations
            if a.source_type == "human" and a.payload.relation == "near_duplicate"
        ],
        "auxiliary_similarity_reviews": [
            a.annotation_id for a in relations if a.source_type != "human"
        ],
        "limitations": [
            "Premise similarity does not establish copying intent",
            "Observed outcomes retain their original age/window; "
            "no causal imitation claim or competition-count score",
        ],
    }


def production_assessment(annotations, creator, selected_case):
    reviews = typed(annotations, "production")
    cases = []
    for a in reviews:
        p = a.payload
        hours = sum((t.hours for t in p.tasks), Decimal(0))
        cash = sum((t.cash for t in p.tasks), Decimal(0))
        skills = {s for t in p.tasks for s in t.required_skills}
        compatibility = {"state": "unknown", "reason": "No creator profile supplied"}
        if creator:
            failed, unknown = [], []
            capacity = (
                ratio(creator.hours_per_week, hours) if creator.hours_per_week is not None else None
            )
            if creator.currency != p.currency:
                unknown.append("Currency mismatch; no exchange-rate assumption")
            if creator.releases_per_week is None:
                unknown.append("Desired cadence not declared")
            else:
                if capacity is None:
                    unknown.append("Hours/week or nonzero release task hours unavailable")
                elif creator.releases_per_week > capacity:
                    failed.append("Declared weekly hours below task burden at desired cadence")
                if creator.monthly_cash is None or creator.currency != p.currency:
                    unknown.append("Comparable monthly cash budget unavailable")
                elif (
                    cash * creator.releases_per_week * Decimal(52) / Decimal(12)
                    > creator.monthly_cash
                ):
                    failed.append("Declared monthly budget below annualized cadence cash burden")
            if creator.skills is None:
                unknown.append("Creator skills not declared")
            elif not skills <= set(creator.skills):
                failed.append("Required skills absent from declared profile")
            requirements = set(p.required_capabilities)
            if any(t.category == "narration" for t in p.tasks):
                requirements.add("narration")
            for capability in sorted(requirements):
                declared = getattr(creator, capability)
                if declared is None:
                    unknown.append(f"Creator {capability} not declared")
                elif declared is False:
                    failed.append(f"Required {capability} absent from creator profile")
            if p.required_team_size:
                if creator.team_size is None:
                    unknown.append("Required team size not declared")
                elif creator.team_size < p.required_team_size:
                    failed.append("Declared team size below reviewed requirement")
            if not p.complete_task_inventory:
                unknown.append("Task inventory is incomplete")
            compatibility = {
                "state": "incompatible_declared_constraints"
                if failed
                else "unknown"
                if unknown
                else "compatible_declared_constraints",
                "releases_per_week_capacity_before_additional_overhead": capacity,
                "failed_constraints": failed,
                "unresolved_constraints": unknown,
                "profile_id": creator.profile_id,
            }
        cases.append(
            {
                "annotation_id": a.annotation_id,
                "case_id": p.case_id,
                "hours_per_release": hours,
                "cash_per_release": cash,
                "currency": p.currency,
                "method": p.method,
                "complete_task_inventory": p.complete_task_inventory,
                "tasks": [t.model_dump(mode="json") for t in p.tasks],
                "required_capabilities": list(p.required_capabilities),
                "required_team_size": p.required_team_size,
                "compatibility": compatibility,
            }
        )
    selected = (
        [c for c in cases if c["case_id"] == selected_case]
        if selected_case
        else cases
        if len(cases) == 1
        else []
    )
    if selected_case and len(selected) != 1:
        raise ValueError("Selected production case must have one unambiguous review")
    return {
        "state": "reviewed_sample" if cases else "unknown",
        "cases": cases,
        "value": selected[0]["hours_per_release"] if selected else None,
        "timed_pilot_present": any(c["method"] == "timed_pilot" for c in cases),
        "contrasting_estimate_count": len(
            {c["case_id"] for c in cases if c["method"] == "estimate"}
        ),
        "limitations": [
            "Estimated burden is not measured creator performance",
            "24 hours/week divided by 12 task hours/release gives 2 before additional overhead",
            "Compatibility never changes the underlying task burden",
        ],
    }


def faceless_feasibility(annotations):
    rows = []
    for a in typed(annotations, "faceless"):
        p = a.payload
        state = (
            "host_dependency"
            if p.central_host_required is True
            else "reviewed_path"
            if p.checked_paths and p.central_host_required is False and a.source_type == "human"
            else "unknown"
        )
        rows.append({"annotation_id": a.annotation_id, "state": state, **p.model_dump(mode="json")})
    return {
        "state": "reviewed_sample" if rows else "unknown",
        "paths": rows,
        "limitations": [
            "Faceless feasibility is separate from task burden and Phase-2 eligibility"
        ],
    }


def risk_assessment(annotations, now):
    rights, policy, factual = [], [], []
    for a in typed(annotations, "rights"):
        p = a.payload
        state = (
            "uncertain"
            if p.clearance == "uncertain" or p.dependency == "unknown"
            else "high_clearance_dependency"
            if p.dependency == "high"
            else "moderate_clearance_burden"
            if p.dependency == "moderate" or p.clearance == "required"
            else "low_apparent_dependency"
        )
        rights.append(
            {"annotation_id": a.annotation_id, "state": state, **p.model_dump(mode="json")}
        )
    for a in typed(annotations, "policy"):
        p = a.payload
        policy.append(
            {
                "annotation_id": a.annotation_id,
                "state": "review_required" if p.refresh_by > now else "stale_policy_unknown",
                **p.model_dump(mode="json"),
            }
        )
    for a in typed(annotations, "factual"):
        factual.append(
            {
                "annotation_id": a.annotation_id,
                "state": "reviewed_burden",
                **a.payload.model_dump(mode="json"),
            }
        )
    return {
        "rights_legal": {
            "state": "reviewed_sample" if rights else "unknown",
            "assets": rights,
            "limitations": [
                "Asset dependency is not a legal conclusion; no fixed safe reuse duration"
            ],
        },
        "platform_policy": {
            "state": "reviewed_sample" if policy else "unknown",
            "snapshots": policy,
            "limitations": ["Review flags are not monetization approval or violation predictions"],
        },
        "factual_editorial": {
            "state": "reviewed_sample" if factual else "unknown",
            "reviews": factual,
            "limitations": [
                "Verification/correction burden only; no allegations or universally safe niche"
            ],
        },
    }
