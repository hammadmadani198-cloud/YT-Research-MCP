"""R3–R6 and bounded reproducible route/threshold/boundary/missingness diagnostics."""

from datetime import timedelta

import pytest
from phase3_helpers import metrics
from phase6_helpers import clone_cohort, result, setup

from youtube_niche_mcp.decision.models import CohortVariant, SensitivityPlan
from youtube_niche_mcp.decision.service import DecisionService


def variants(repository, base, ids, now, labels):
    output = []
    for label in labels:
        family = "boundary" if label in {"broad", "practical", "narrow"} else "threshold"
        boundary = (
            base.run.boundary.model_copy(update={"boundary_id": label})
            if family == "boundary"
            else None
        )
        changes = {}
        if label.endswith("m"):
            changes["long_form_rule"] = "long_form_v1_" + label
        if label.endswith("k"):
            changes["small_rule"] = "current_small_v1_" + label
        selected = set(ids) if label in {"6m", "8m", "100k", "broad", "practical"} else set(ids[:6])
        vd = clone_cohort(
            repository,
            base.run.video_cohort_id,
            "variant-videos-" + label,
            selected=selected,
            boundary=boundary,
            changes=changes,
        )
        cd = clone_cohort(
            repository,
            base.run.cohort_id,
            "variant-entrants-" + label,
            boundary=boundary,
            changes=changes,
        )
        output.append(
            CohortVariant(
                variant_id=label,
                family=family,
                label=label,
                cohort_id=cd,
                video_cohort_id=vd,
                declared_at=now,
                research_reference="Predeclared synthetic alternate recruitment frame",
            )
        )
    return tuple(output)


def sensitivity(bundle, label):
    return next(r for r in result(bundle, "decision").details["sensitivity"] if r["label"] == label)


def test_R3_weak_route_exclusion_changes_metrics(repository, observation_factory, now):
    _, _, opt, _, _ = setup(
        repository,
        observation_factory,
        now,
        values=[[15000] * 6, [100] * 6, [100] * 6],
        official_span=6,
    )
    b = DecisionService(repository).analyze(opt)
    official = sensitivity(b, "official_only")
    weak = sensitivity(b, "weak_suggested_excluded")
    assert official["state"] == "materially_changed"
    assert weak["state"] == "materially_changed"
    assert weak["diagnostic"]["winner_only_bias_indicator"] is True
    assert "performance" in weak["changed_axes"]
    assert result(b, "F18").details["components"]["sensitivity"]["route"]["state"] == "sensitive"


def test_semantic_only_and_missing_official_route(repository, observation_factory, now):
    base, _, opt, _, _ = setup(repository, observation_factory, now, with_routes=False)
    b = DecisionService(repository).analyze(opt)
    assert sensitivity(b, "official_only")["state"] == "insufficient_comparable_evidence"
    assert sensitivity(b, "NexLev_excluded")["comparable"] is False
    assert result(b, "decision").details["evidence"]["routes"]["omissions"]
    assert DecisionService(repository).repository.read(base.run.run_id) == base


@pytest.mark.parametrize(
    "label", ["all_routes", "official_only", "NexLev_excluded", "winner_oriented_excluded"]
)
def test_redundant_routes_do_not_multiply_entities(repository, observation_factory, now, label):
    _, _, opt, _, ids = setup(repository, observation_factory, now)
    row = sensitivity(DecisionService(repository).analyze(opt), label)
    assert len(row["changed_option"]["selected_video_ids"]) == len(set(ids))
    assert row["state"] == "stable"


def test_R4_duration_and_size_threshold_variants(repository, observation_factory, now):
    base, _, opt, _, ids = setup(
        repository, observation_factory, now, values=[[12000] * 6, [9000] * 6, [8000] * 6]
    )
    plan = opt.sensitivity.model_copy(
        update={
            "cohorts": variants(repository, base, ids, now, ("6m", "8m", "10m", "50k", "100k")),
            "goals": (5000, 25000),
        }
    )
    b = DecisionService(repository).analyze(opt.model_copy(update={"sensitivity": plan}))
    for label in ("6m", "8m", "10m", "50k", "100k", "goal:5000", "goal:25000"):
        assert sensitivity(b, label)["comparable"] is True
    assert sensitivity(b, "10m")["material"] is True
    assert sensitivity(b, "6m")["state"] == "stable"
    assert sensitivity(b, "goal:5000")["material"] is True
    assert metrics(base)["F3"].value < 1


def test_R5_boundary_diversity_and_missing_context(repository, observation_factory, now):
    base, _, opt, _, ids = setup(
        repository, observation_factory, now, values=[[100000] * 6, [12000] * 6, [15000] * 6]
    )
    plan = opt.sensitivity.model_copy(
        update={"cohorts": variants(repository, base, ids, now, ("broad", "practical", "narrow"))}
    )
    b = DecisionService(repository).analyze(opt.model_copy(update={"sensitivity": plan}))
    narrow = sensitivity(b, "narrow")
    assert narrow["diagnostic"]["channel_count"] == 1
    assert narrow["diagnostic"]["boundary"]["boundary_id"] == "narrow"
    assert narrow["state"] == "insufficient_comparable_evidence"
    assert any(
        m["formula_id"] == "F9" and m["variant"] == "1" for m in narrow["raw_metric_comparison"]
    )
    assert "compatible alternative" in narrow["reason"]


@pytest.mark.parametrize("unknown,expected", [(False, False), (True, True)])
def test_R6_finite_frame_missingness_bounds(
    repository, observation_factory, now, unknown, expected
):
    values = (
        [[12000, None, None, None, None, None], [None] * 6, [100] * 6]
        if unknown
        else [[12000] * 6, [100] * 6, [100] * 6]
    )
    _, _, opt, _, _ = setup(repository, observation_factory, now, values=values)
    b = DecisionService(repository).analyze(opt)
    row = sensitivity(b, "finite_frame_bounds")
    assert row["material"] == expected
    bounds = row["diagnostic"]["bounds"][0]["F22_bounds"]
    assert bounds["n"] == 18
    assert bounds["lower"] != bounds["upper"] if unknown else bounds["lower"] == bounds["upper"]


@pytest.mark.parametrize("mode,limit", [("quick", 8), ("standard", 24), ("deep", 48)])
def test_sensitivity_budgets_are_bounded(repository, observation_factory, now, mode, limit):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    plan = SensitivityPlan(mode=mode, max_runs=limit, declared_at=now, goals=(5000, 25000))
    b = DecisionService(repository).analyze(opt.model_copy(update={"sensitivity": plan}))
    rows = result(b, "decision").details["sensitivity"]
    assert len([r for r in rows if r["run_id"]]) <= limit
    assert all(r["comparable"] is False for r in rows if r["state"] == "budget_omitted")
    if mode == "quick":
        assert any(r["state"] == "budget_omitted" for r in rows)


def test_qualitative_reduced_alternate_and_expanded_manifests(repository, observation_factory, now):
    _, q, opt, _, _ = setup(repository, observation_factory, now, review_budget=20)
    b = DecisionService(repository).analyze(opt)
    reduced = sensitivity(b, "reduced_sample")["diagnostic"]["sample_manifests"][0]
    alternate = sensitivity(b, "alternate_seed")["diagnostic"]["sample_manifests"][0]
    expanded = sensitivity(b, "expanded_sample")["diagnostic"]["sample_manifests"][0]
    assert len(reduced["sample_ids"]) == 10 and len(expanded["sample_ids"]) == 35
    assert alternate["seed"] != q.run.options.seed
    assert set(reduced["sample_ids"]) <= set(expanded["population_ids"])


def test_predeclared_variant_label_must_match_cohort(repository, observation_factory, now):
    base, _, opt, _, ids = setup(repository, observation_factory, now)
    vv = variants(repository, base, ids, now, ("8m",))[0].model_copy(update={"label": "10m"})
    with pytest.raises(ValueError, match="label"):
        DecisionService(repository).analyze(
            opt.model_copy(
                update={"sensitivity": opt.sensitivity.model_copy(update={"cohorts": (vv,)})}
            )
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"max_runs": 9, "mode": "quick"},
        {"goals": (1000, 1000)},
        {"goals": (-1,)},
        {"cohorts": (), "required_families": ("route", "route")},
    ],
)
def test_invalid_budgets_and_grid_configuration(now, changes):
    with pytest.raises(ValueError):
        SensitivityPlan(declared_at=now, **changes)


def test_future_plan_is_rejected(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    with pytest.raises(ValueError, match="precede"):
        DecisionService(repository).analyze(
            opt.model_copy(
                update={
                    "sensitivity": opt.sensitivity.model_copy(
                        update={"declared_at": now + timedelta(seconds=1)}
                    )
                }
            )
        )


def test_alternative_channel_recruitment_cannot_change_silently(
    repository, observation_factory, now
):
    base, _, opt, _, ids = setup(repository, observation_factory, now)
    vv = variants(repository, base, ids, now, ("10m",))[0]
    changed = clone_cohort(
        repository,
        base.run.cohort_id,
        "wrong-entry-variant",
        changes={"publication_start": now - timedelta(days=90)},
    )
    vv = vv.model_copy(update={"cohort_id": changed})
    with pytest.raises(ValueError, match="channel recruitment"):
        DecisionService(repository).analyze(
            opt.model_copy(
                update={"sensitivity": opt.sensitivity.model_copy(update={"cohorts": (vv,)})}
            )
        )


def test_decision_rubric_requires_scope_and_unique_history():
    from youtube_niche_mcp.decision.models import DecisionRubric

    for changed in ({"required_axes": ()}, {"required_history": ("F10", "F10")}):
        with pytest.raises(ValueError):
            DecisionRubric(version="invalid", rules=(), **changed)


def test_alternative_context_must_match_alternative_frame(repository, observation_factory, now):
    base, q, opt, _, ids = setup(repository, observation_factory, now)
    vv = variants(repository, base, ids, now, ("8m",))[0].model_copy(
        update={"contextual_run_ids": (q.run.run_id,)}
    )
    with pytest.raises(ValueError, match="contextual run is incompatible"):
        DecisionService(repository).analyze(
            opt.model_copy(
                update={"sensitivity": opt.sensitivity.model_copy(update={"cohorts": (vv,)})}
            )
        )
