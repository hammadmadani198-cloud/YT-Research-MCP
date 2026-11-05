"""Bounded one-at-a-time comparisons; immutable derivatives in existing analysis tables."""

import json
from decimal import Decimal

from youtube_niche_mcp import __version__
from youtube_niche_mcp.analysis.concentration import shares
from youtube_niche_mcp.analysis.models import AnalysisBundle, AnalysisRun
from youtube_niche_mcp.analysis.numerics import json_numbers, ratio
from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.analysis.service import AnalysisService
from youtube_niche_mcp.decision.models import VERSION, SensitivityOptions
from youtube_niche_mcp.decision.synthesis import assemble, compare, grade
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.qualitative.repository import ReviewRepository, references
from youtube_niche_mcp.qualitative.service import QualitativeService
from youtube_niche_mcp.services.safety import identity

WINNER_ROUTES = {
    "small_channel_viral",
    "faceless_outliers",
    "outliers",
    "viral",
    "small-channel-viral",
    "faceless-outliers",
}
SEMANTIC_ROUTES = {"semantic", "semantic_niche_search", "semantic_search", "niche_search"}
WEAK_ROUTES = {"suggested", "weak", "weak_case", "suggested_channels", "suggested_route"}


def route_map(frame):
    result = {}
    for v in frame.videos:
        occurrences = list(v.membership.discovery_occurrences)
        occurrences.extend(
            r
            for m in frame.members
            if m.subject.entity_id == v.channel_id
            for r in m.discovery_occurrences
        )
        result[v.video_id] = occurrences
    return result


def subset(frame, selected, *, remove_provider=False):
    videos = tuple(v for v in frame.videos if v.video_id in selected)
    channels = {v.channel_id for v in videos}
    members = tuple(m for m in frame.members if m.subject.entity_id in selected | channels)
    body = {
        "parent": frame.input_hash,
        "selected": sorted(selected),
        "remove_provider": remove_provider,
    }
    return frame.model_copy(
        update={"videos": videos, "members": members, "input_hash": identity(body)}
    )


def winner_ownership_diagnostic(metric, documented_units):
    """Project retained winner IDs only; do not fabricate per-winner entrant annotations."""
    if metric is None or not {"older_winners", "newer_winners"} <= metric.details.keys():
        return {
            "state": "insufficient_panel_history",
            "replacement_share": None,
            "incumbent_persistence": None,
            "verified_entrant_share": None,
        }
    old = set(metric.details["older_winners"]) & documented_units
    new = set(metric.details["newer_winners"]) & documented_units
    return {
        "state": "documented_winner_projection",
        "older_winners": sorted(old),
        "newer_winners": sorted(new),
        "replacement_share": ratio(len(new - old), len(new)),
        "incumbent_persistence": ratio(len(old & new), len(old)),
        "verified_entrant_share": None,
        "canonical_F21": metric.details,
        "warning": (
            "Known-group winner-set diagnostic only; retained aggregates lack "
            "per-winner entrant annotation, so entrant share stays unknown"
        ),
    }


def calculate(history, repository, frame, options):
    service = AnalysisService(history)

    # This immutable projection belongs to the derivative; the base is untouched.
    class ProjectedRepository:
        def load(self, *_):
            return frame

    service.repository = ProjectedRepository()
    return service.analyze(
        frame.cohort_id, options, video_cohort_id=frame.video_cohort_id, persist=False
    )


def run_plan(
    history, repository, base, frame, source_bundles, metrics, generic, evidence, options, persist
):
    reports, derived_ids = [], []
    budget = options.sensitivity.max_runs
    contextual = {f: m for f, m in metrics.items() if m.formula_version != "phase3-v1"}
    policy = evidence["policy"]["state"]

    def project(projected, measurement):
        return calculate(history, repository, projected, measurement) if budget else None

    def emit(
        family,
        label,
        changed,
        bundle=None,
        diagnostic=None,
        *,
        comparable=True,
        context=None,
        reason=None,
        dependency_bundles=(),
    ):
        nonlocal budget
        if budget <= 0:
            reports.append(
                {
                    "family": family,
                    "label": label,
                    "state": "budget_omitted",
                    "comparable": False,
                    "same_decision": False,
                    "material": False,
                    "changed_axes": [],
                    "run_id": None,
                    "reason": "Declared one-at-a-time run budget exhausted",
                }
            )
            return
        budget -= 1
        variant_metrics = dict(contextual if context is None else context)
        variant_metrics.update(
            {m.formula_id: m for m in bundle.metrics}
            if bundle
            else {m.formula_id: m for m in base.metrics}
        )
        result = assemble(
            variant_metrics,
            options.rubric,
            policy_state=policy,
            classifications=evidence["classifications"],
        )
        shifts = compare(metrics, variant_metrics, options.rubric) if bundle else []
        changed_axes = [
            a for a, d in result["axes"].items() if d["state"] != generic["axes"][a]["state"]
        ]
        material = any(s["material"] for s in shifts) or bool(changed_axes)
        if diagnostic:
            material |= diagnostic.get("material", False)
        same = result["state"] == generic["state"]
        if diagnostic and "bounds" in diagnostic:
            # The documented F22 reversal condition is a decision-relevant specification flip.
            same = same and not diagnostic.get("material", False)
        if not comparable:
            state = (
                "insufficient_without_provider"
                if family == "provider"
                else "insufficient_comparable_evidence"
            )
        else:
            state = "materially_changed" if material or not same else "stable"
        ids = tuple(
            sorted(
                {
                    base.run.run_id,
                    *(b.run.run_id for b in (*source_bundles, *dependency_bundles)),
                    *(bundle.run.input_ids if bundle else ()),
                }
            )
        )
        expiry = min(
            (
                b.run.expires_at
                for b in (
                    base,
                    *source_bundles,
                    *dependency_bundles,
                    *((bundle,) if bundle else ()),
                )
                if b.run.expires_at
            ),
            default=None,
        )
        if not bundle:
            expiry = base.run.expires_at if expiry is None else expiry
        digest = identity(
            {
                "parent": base.run.run_id,
                "family": family,
                "label": label,
                "changed": changed,
                "inputs": ids,
                "rubric": options.rubric.model_dump(mode="json"),
                "policy": json_numbers(evidence["policy"]),
                "classifications": json_numbers(evidence["classifications"]),
                "base_decision": generic["state"],
                "variant_decision": result["state"],
                "context": [m.model_dump(mode="json") for _, m in sorted(variant_metrics.items())],
                "diagnostic": json_numbers(diagnostic),
                "metrics": [m.model_dump(mode="json") for m in bundle.metrics] if bundle else [],
                "code": __version__,
            },
            history.secrets,
        )
        rid = identity([VERSION, "sensitivity", digest], history.secrets)
        manifest = SensitivityOptions(
            cutoff=options.cutoff,
            age_days=options.age_days,
            tolerance_seconds=options.tolerance_seconds,
            goal=bundle.run.options.goal if bundle else options.goal,
            parent_run_id=base.run.run_id,
            family=family,
            label=label,
            changed_option=json_numbers(changed),
            source_run_ids=tuple(
                b.run.run_id for b in (base, *source_bundles, *dependency_bundles)
            ),
            input_identity=digest,
            frozen_discovery=options.frozen_discovery,
        )
        report = {
            "family": family,
            "label": label,
            "state": state,
            "comparable": comparable,
            "same_decision": same,
            "material": material,
            "changed_axes": changed_axes,
            "run_id": rid,
            "parent_run_id": base.run.run_id,
            "changed_option": changed,
            "metric_shifts": shifts,
            "raw_metric_comparison": [
                {
                    "formula_id": f,
                    "base": metrics[f].value if f in metrics else None,
                    "variant": m.value,
                    "base_state": metrics[f].state if f in metrics else "missing",
                    "variant_state": m.state,
                    "base_included": metrics[f].included if f in metrics else 0,
                    "variant_included": m.included,
                    "variant_details": m.details,
                }
                for f, m in variant_metrics.items()
                if f in ("F3", "F5", "floor", "F6", "F8", "F9", "F19", "F15", "content_gaps")
            ],
            "diagnostic": diagnostic,
            "reason": reason,
            "decision": result["state"],
            "comparison_scope": (
                "Changed family only; retained contextual axes held fixed unless "
                "explicitly replaced"
            ),
        }
        run = AnalysisRun(
            run_id=rid,
            formula_version=VERSION,
            formula_set=("sensitivity",),
            cohort_id=frame.cohort_id,
            video_cohort_id=frame.video_cohort_id,
            boundary=frame.boundary,
            options=manifest,
            input_ids=ids,
            input_hash=digest,
            software_version=__version__,
            created_at=history.clock(),
            expires_at=expiry,
        )
        template = base.metrics[0]
        result_metric = template.model_copy(
            update={
                "formula_id": "sensitivity",
                "formula_version": VERSION,
                "analysis_run_id": rid,
                "state": state,
                "value": None,
                "numerator": None,
                "denominator": None,
                "unit": "structured_sensitivity",
                "input_manifest_hash": digest,
                "details": json_numbers(report),
            }
        )
        derived = AnalysisBundle(
            run=run, outcomes=bundle.outcomes if bundle else (), metrics=(result_metric,)
        )
        if persist:
            repository.store(derived)
        reports.append(json_numbers(report))
        derived_ids.append(rid)

    routes = route_map(frame)
    selected_all = {v.video_id for v in frame.videos}
    route_names = sorted({r.get("route", "unknown") for rows in routes.values() for r in rows})
    if "route" in options.sensitivity.required_families:
        checks = [
            ("all_routes", lambda r: True),
            (
                "official_only",
                lambda r: (
                    str(r.get("provider", "")).startswith("youtube")
                    or r.get("provider") == "official"
                ),
            ),
            ("NexLev_excluded", lambda r: "nexlev" not in str(r.get("provider", "")).lower()),
            ("winner_oriented_excluded", lambda r: r.get("route") not in WINNER_ROUTES),
            ("weak_suggested_excluded", lambda r: r.get("route") not in WEAK_ROUTES),
            ("semantic_excluded", lambda r: r.get("route") not in SEMANTIC_ROUTES),
        ]
        if options.sensitivity.mode == "deep":
            checks.extend(
                ("route:" + name, lambda r, n=name: r.get("route") == n) for name in route_names
            )
        for label, predicate in checks:
            if not budget:
                emit("route", label, {}, comparable=False)
                continue
            selected = {vid for vid, rows in routes.items() if any(predicate(r) for r in rows)}
            projected = subset(frame, selected)
            b = calculate(history, repository, projected, base.run.options)
            weak = [
                o.video_id for o in b.outcomes if o.value is not None and o.value < options.goal
            ]
            emit(
                "route",
                label,
                {"selected_video_ids": sorted(selected), "routes_available": route_names},
                b,
                {
                    "weak_case_ids": weak,
                    "winner_only_bias_indicator": bool(selected) and not weak,
                    "omitted_video_ids": sorted(selected_all - selected),
                    "canonical_entities_deduplicated": True,
                },
                comparable=bool(selected),
                reason=None if selected else "No retained candidates for this route subset",
            )
    if "provider" in options.sensitivity.required_families:
        provider_ids = set()
        similarity_ids = set()
        for row in history.connection.execute(
            "SELECT evidence_id,record_json FROM provider_evidence"
        ):
            provider_ids.add(row["evidence_id"])
            body = json.loads(row["record_json"])
            if any(
                c["field"] in {"semantic_similarity", "format_similarity", "thumbnail_similarity"}
                for c in body["claims"]
            ):
                similarity_ids.add(row["evidence_id"])
        for label in (
            "NexLev_T1_T2_T3_removed",
            "provider_classifications_removed",
            "provider_similarity_removed",
        ):
            if not budget:
                emit("provider", label, {}, comparable=False)
                continue
            selected = set(selected_all)
            if label != "provider_similarity_removed":
                # Exclude unresolved provider dependencies without inventing replacements.
                uncertain = {
                    sid
                    for item in evidence["classifications"].values()
                    for sid in item["provider_only_ids"]
                }
                selected = {
                    v.video_id
                    for v in frame.videos
                    if v.video_id not in uncertain and v.channel_id not in uncertain
                }
            projected = subset(frame, selected, remove_provider=True)
            projected = projected.model_copy(
                update={
                    "videos": tuple(
                        v.model_copy(
                            update={
                                "snapshots": tuple(
                                    s for s in v.snapshots if s.source_kind == "public_api"
                                )
                            }
                        )
                        for v in projected.videos
                    )
                }
            )
            b = calculate(history, repository, projected, base.run.options)
            provider_context = dict(contextual)
            removed_reviews = []
            provider_inputs_available = True
            for q in (s for s in source_bundles if s.run.formula_version == "phase5-v1"):
                try:
                    reviews = ReviewRepository(history).read_many(
                        q.run.options.annotation_ids, options.cutoff
                    )
                except AnalysisUnavailable:
                    provider_inputs_available = False
                    continue
                blocked = similarity_ids if label == "provider_similarity_removed" else provider_ids
                removed = {
                    a.annotation_id
                    for a in reviews
                    if set(references(a)) & blocked
                    or (label != "provider_similarity_removed" and a.source_type == "provider")
                }
                while True:
                    expanded = removed | {
                        a.annotation_id for a in reviews if set(references(a)) & removed
                    }
                    if expanded == removed:
                        break
                    removed = expanded
                removed_reviews.extend(sorted(removed))
                qo = q.run.options.model_copy(
                    update={
                        "annotation_ids": tuple(
                            i for i in q.run.options.annotation_ids if i not in removed
                        )
                    }
                )
                qb = QualitativeService(history).analyze(
                    q.run.cohort_id, qo, video_cohort_id=q.run.video_cohort_id, persist=False
                )
                provider_context.update({m.formula_id: m for m in qb.metrics})
            emit(
                "provider",
                label,
                {"remove": label, "selected_video_ids": sorted(selected)},
                b,
                {
                    "T4_T5_core_scoring": "excluded_by_prior_phase_firewall",
                    "dependent_subjects_removed": len(selected_all - selected),
                    "removed_annotation_ids": removed_reviews,
                },
                context=provider_context,
                comparable=provider_inputs_available
                and bool(selected)
                and all(
                    m.state != "insufficient_classification_coverage"
                    for m in b.metrics
                    if m.formula_id == "F8"
                ),
            )
    if "threshold" in options.sensitivity.required_families:
        for goal in options.sensitivity.goals:
            if not budget:
                emit("threshold", "goal:" + str(goal), {}, comparable=False)
                continue
            b = calculate(
                history, repository, frame, base.run.options.model_copy(update={"goal": goal})
            )
            emit("threshold", "goal:" + str(goal), {"goal": goal}, b)
    for family, labels in (
        ("threshold", ("6m", "8m", "10m", "50k", "100k")),
        ("boundary", ("broad", "practical", "narrow")),
    ):
        if family not in options.sensitivity.required_families:
            continue
        for label in labels:
            if not budget:
                emit(family, label, {}, comparable=False)
                continue
            spec = next(
                (v for v in options.sensitivity.cohorts if v.family == family and v.label == label),
                None,
            )
            if not spec:
                emit(
                    family,
                    label,
                    {"label": label},
                    comparable=False,
                    reason="A separately predeclared frozen alternative cohort is unavailable",
                )
                continue
            row = history.connection.execute(
                "SELECT definition_json FROM cohort_definitions WHERE cohort_id=?",
                (spec.video_cohort_id,),
            ).fetchone()
            definition = json.loads(row[0]) if row else None
            if not definition or definition["created_at"] > timestamp(spec.declared_at):
                raise ValueError("Sensitivity cohort must be frozen by its declared time")
            expected = {
                "6m": ("long_form_rule", "long_form_v1_6m"),
                "8m": ("long_form_rule", "long_form_v1_8m"),
                "10m": ("long_form_rule", "long_form_v1_10m"),
                "50k": ("small_rule", "current_small_v1_50k"),
                "100k": ("small_rule", "current_small_v1_100k"),
            }
            if label in expected and definition[expected[label][0]] != expected[label][1]:
                raise ValueError("Alternative cohort label does not match frozen threshold rule")
            original_row = history.connection.execute(
                "SELECT definition_json FROM cohort_definitions WHERE cohort_id=?",
                (base.run.video_cohort_id,),
            ).fetchone()
            original = json.loads(original_row[0])
            permitted_change = expected[label][0] if label in expected else "boundary"
            invariant_fields = (
                "publication_start",
                "publication_end",
                "long_form_rule",
                "small_rule",
                "allow_archived_live",
                "include_uncertain",
                "format_rule",
                "live_rule",
                "language_rule",
                "faceless_rule",
                "entry_rule",
                "boundary",
            )
            if any(original[k] != definition[k] for k in invariant_fields if k != permitted_change):
                raise ValueError("One-at-a-time sensitivity cannot silently change other rules")
            if family == "boundary" and not all(
                definition["boundary"].get(k)
                for k in (
                    "boundary_id",
                    "node_ids",
                    "inclusion_rules",
                    "exclusion_rules",
                    "classifier_version",
                )
            ):
                raise ValueError("Explicit boundary identity/rules required")
            # Both frames define recruitment; the channel frame cannot silently change entry rules.
            channel_row = history.connection.execute(
                "SELECT definition_json FROM cohort_definitions WHERE cohort_id=?",
                (spec.cohort_id,),
            ).fetchone()
            original_channel_row = history.connection.execute(
                "SELECT definition_json FROM cohort_definitions WHERE cohort_id=?",
                (base.run.cohort_id,),
            ).fetchone()
            channel_definition = json.loads(channel_row[0]) if channel_row else None
            original_channel = json.loads(original_channel_row[0])
            if not channel_definition or channel_definition["created_at"] > timestamp(
                spec.declared_at
            ):
                raise ValueError("Alternative channel cohort must be frozen by declared time")
            if any(
                original_channel[k] != channel_definition[k]
                for k in invariant_fields
                if k != permitted_change
            ):
                raise ValueError("One-at-a-time channel recruitment rules must remain compatible")
            alternate = repository.load(spec.cohort_id, spec.video_cohort_id, base.run.options)
            b = calculate(history, repository, alternate, base.run.options)
            extra = [repository.read(r) for r in spec.contextual_run_ids]
            if any(
                e.run.formula_version not in {"phase4-v1", "phase5-v1"}
                or e.run.boundary != alternate.boundary
                or e.run.cohort_id != alternate.cohort_id
                or e.run.video_cohort_id != alternate.video_cohort_id
                or e.run.options.cutoff > options.cutoff
                or any(
                    getattr(e.run.options, key) != getattr(options, key)
                    for key in ("age_days", "goal", "tolerance_seconds")
                )
                for e in extra
            ):
                raise ValueError("Alternative contextual run is incompatible")
            context_ids = [m.formula_id for e in extra for m in e.metrics]
            if len(set(context_ids)) != len(context_ids):
                raise ValueError("Ambiguous alternative contextual metrics")
            context = (
                {m.formula_id: m for e in extra for m in e.metrics}
                if extra
                else contextual
                if alternate.boundary == frame.boundary
                else {}
            )
            emit(
                family,
                label,
                spec.model_dump(mode="json"),
                b,
                {
                    "boundary": alternate.boundary.model_dump(mode="json"),
                    "channel_count": len({v.channel_id for v in alternate.videos}),
                    "omissions": list(spec.omissions),
                },
                context=context,
                dependency_bundles=extra,
                comparable=bool(b.outcomes)
                and (alternate.boundary == frame.boundary or bool(extra) or not contextual),
                reason=(
                    "Cross-boundary qualitative/history claims require compatible "
                    "alternative contextual runs"
                )
                if alternate.boundary != frame.boundary and contextual and not extra
                else None,
            )
    if "missingness" in options.sensitivity.required_families:
        f22 = metrics["F22"].details
        diagnoses = []
        for fid, detail in (
            ("F3", f22),
            (
                "F19",
                metrics.get("F19").details.get("channel_bounds", {}) if metrics.get("F19") else {},
            ),
        ):
            rule = next(
                (r for r in options.rubric.rules if r.formula_id == fid and not r.path), None
            )
            lower, upper = detail.get("lower"), detail.get("upper")
            flip = bool(
                rule
                and lower is not None
                and upper is not None
                and grade(Decimal(str(lower)), rule) != grade(Decimal(str(upper)), rule)
            )
            diagnoses.append(
                {
                    "formula_id": fid,
                    "F22_bounds": detail,
                    "known_only": metrics[fid].value
                    if fid == "F3"
                    else metrics[fid].details.get("known_only_fraction")
                    if fid in metrics
                    else None,
                    "rule_flip": flip,
                }
            )
        emit(
            "missingness",
            "finite_frame_bounds",
            {"treatment": "F22_lower_upper_known_only"},
            diagnostic={"bounds": diagnoses, "material": any(d["rule_flip"] for d in diagnoses)},
            comparable=f22.get("lower") is not None,
        )
    if "ownership" in options.sensitivity.required_families:
        documented = {
            v.video_id
            for v in frame.videos
            if v.membership.independence_state == "documented_group"
        }
        b = project(subset(frame, documented), base.run.options)
        mass = metrics["F9"].details.get("channels", {}).get("mass", {})
        emit(
            "ownership",
            "documented_groups_only",
            {"policy": "documented_group_only"},
            b,
            {
                **evidence["ownership"],
                "provisional_canonical_concentration": shares(mass),
                "grouped_concentration": metrics["F9"].details.get("creator_units"),
                "F21_documented_winners": winner_ownership_diagnostic(
                    metrics.get("F21"), set(evidence["ownership"]["documented_groups"])
                ),
                "warning": (
                    "Provisional channels are not proven independent; no shared ownership invented"
                ),
            },
            comparable=bool(documented),
        )
    if "qualitative" in options.sensitivity.required_families:
        q = next((b for b in source_bundles if b.run.formula_version == "phase5-v1"), None)
        if q:
            specs = [
                ("alternate_seed", {"seed": q.run.options.seed + ":phase6-alternate"}),
                ("reduced_sample", {"review_budget": max(1, q.run.options.review_budget // 2)}),
            ]
            if options.sensitivity.mode == "deep":
                specs.append(
                    (
                        "expanded_sample",
                        {
                            "review_budget": min(
                                500,
                                max(
                                    q.run.options.review_budget + 1, q.run.options.review_budget * 2
                                ),
                            )
                        },
                    )
                )
            for label, change in specs:
                if not budget:
                    emit("qualitative", label, change, comparable=False)
                    continue
                qs = q.run.options.model_copy(update=change)
                try:
                    qb = QualitativeService(history).analyze(
                        q.run.cohort_id, qs, video_cohort_id=q.run.video_cohort_id, persist=False
                    )
                except AnalysisUnavailable as exc:
                    emit(
                        "qualitative",
                        label,
                        change,
                        comparable=False,
                        reason=f"Alternative review sample unavailable: {exc.state}",
                    )
                    continue
                unchanged = {
                    f: m for f, m in contextual.items() if m.formula_version != "phase5-v1"
                }
                emit(
                    "qualitative",
                    label,
                    change,
                    qb,
                    {
                        "sample_manifests": [
                            m.details.get("sample_manifest")
                            for m in qb.metrics
                            if m.formula_id == "F15"
                        ],
                        "comment_sample": [
                            m.details for m in qb.metrics if m.formula_id == "content_gaps"
                        ],
                    },
                    context={**unchanged, **{m.formula_id: m for m in base.metrics}},
                )
        else:
            emit(
                "qualitative",
                "alternate_sample",
                {},
                comparable=False,
                reason="No retained qualitative run available",
            )
    return reports, derived_ids
