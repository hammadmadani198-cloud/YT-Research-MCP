"""R1–R15 adversarial synthetic research cases, never empirical niche predictions."""

from datetime import timedelta
from decimal import Decimal

import pytest
from phase6_helpers import complete_history, result, setup

from youtube_niche_mcp.decision.confidence import robustness
from youtube_niche_mcp.decision.evidence import collect
from youtube_niche_mcp.decision.models import PolicyClock, SortConfig, SortDimension
from youtube_niche_mcp.decision.service import DecisionService
from youtube_niche_mcp.decision.sorting import sort_runs, sorting_index
from youtube_niche_mcp.decision.synthesis import assemble
from youtube_niche_mcp.qualitative.models import CreatorCapacity


def test_R1_strong_metrics_weak_coverage(repository, observation_factory, now):
    base, _, options, _, _ = setup(
        repository,
        observation_factory,
        now,
        complete=False,
        values=[[100000, None, None, None, None, None]],
    )
    bundle = DecisionService(repository).analyze(options)
    d = result(bundle, "decision").details
    assert d["evidence"]["coverage"]["videos"]["numerator"] == 1
    assert d["evidence"]["coverage"]["videos"]["denominator"] == 6
    assert result(bundle, "F18").state == "low"
    assert result(base, "F3").value == 1
    assert d["state"] != "supported"


@pytest.mark.parametrize(
    "case,values,expected",
    [
        ("R2", [[12000] * 6] * 3, "supported"),
        ("R11", [[12000, 100, 100, 100, 100, 100], [100] * 6, [100] * 6], "weak_under_goal"),
    ],
)
def test_robust_positive_and_negative_confidence(
    repository, observation_factory, now, case, values, expected
):
    base, q, opt, mm, _ = setup(repository, observation_factory, now, values=values)
    frame = DecisionService(repository).repository.load(
        base.run.cohort_id, base.run.video_cohort_id, base.run.options
    )
    evidence = collect(repository, frame, base, (q,), opt)
    mm.update({m.formula_id: m for m in q.metrics})
    mm = complete_history(mm)
    generic = assemble(
        mm, opt.rubric, policy_state="fresh", classifications=evidence["classifications"]
    )
    rows = [
        {
            "family": f,
            "label": f,
            "comparable": True,
            "same_decision": True,
            "material": False,
            "changed_axes": [],
            "run_id": f,
        }
        for f in opt.sensitivity.required_families
    ]
    r = robustness(evidence, generic, rows, opt)
    assert generic["state"] == expected, case
    assert r["confidence"] == "high", case
    assert r["specification_agreement"] == 1
    assert "not success probability" in r["warning"]


@pytest.mark.parametrize(
    "case,changed,flag",
    [
        ("R9", {"hours": 100}, "high_execution_burden"),
        ("R10", {"rights": "high"}, "high_rights_or_policy_dependency"),
        ("policy-risk", {"policy_flags": ("reused_content",)}, "high_rights_or_policy_dependency"),
    ],
)
def test_high_performance_does_not_erase_burden_or_rights(
    repository, observation_factory, now, case, changed, flag
):
    base, _, opt, _, _ = setup(repository, observation_factory, now, **changed)
    bundle = DecisionService(repository).analyze(opt)
    assert result(base, "F3").value == 1
    assert result(bundle, "decision").state == flag, case


def test_R7_current_evidence_history_immature(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    bundle = DecisionService(repository).analyze(opt)
    assert result(bundle, "decision").state == "history_immature"
    assert set(result(bundle, "decision").details["history_maturity"]["immature"]) == {
        "F10",
        "F11",
        "F12",
        "F13",
        "F20",
        "F21",
    }
    assert result(bundle, "F18").state == "low"


@pytest.mark.parametrize(
    "case,hours,fit",
    [
        ("R12", 1, "incompatible_declared_constraints"),
        ("R13", 40, "compatible_declared_constraints"),
    ],
)
def test_creator_fit_separate_from_generic(repository, observation_factory, now, case, hours, fit):
    base, _, opt, _, _ = setup(repository, observation_factory, now)
    creator = CreatorCapacity(
        profile_id=case,
        declared_at=now,
        expires_at=now + timedelta(days=5),
        hours_per_week=hours,
        monthly_cash=10000,
        currency="USD",
        releases_per_week=1,
        skills=(),
        team_size=1,
        narration=True,
        animation=True,
        footage_access=True,
    )
    service = DecisionService(repository)
    generic = service.analyze(opt)
    specific = service.analyze(opt.model_copy(update={"creator": creator}))
    gd, sd = result(generic, "decision"), result(specific, "decision")
    assert gd.state == sd.state
    assert gd.details["axes"] == sd.details["axes"]
    assert gd.details["confidence"] == sd.details["confidence"]
    assert sd.details["creator_fit"]["cases"][0]["compatibility"]["state"] == fit
    assert service.repository.read(base.run.run_id) == base


def config(fid, direction="higher", essential=True):
    return SortConfig(
        version="caller-v1",
        dimensions=(
            SortDimension(
                formula_id=fid,
                weight=1,
                low=0,
                high=1 if fid == "F3" else 20,
                direction=direction,
                essential=essential,
                benchmark_reference="Synthetic external benchmark",
            ),
        ),
    )


def test_R14_sorting_order_never_changes_decision(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now, rights="high")
    s = DecisionService(repository)
    high = s.analyze(opt.model_copy(update={"f17": config("F3")}))
    low = s.analyze(opt.model_copy(update={"f17": config("F3", "lower")}))
    assert result(high, "F17").value == 100 and result(low, "F17").value == 0
    assert (
        result(high, "decision").state
        == result(low, "decision").state
        == "high_rights_or_policy_dependency"
    )
    assert result(high, "F18") == result(low, "F18").model_copy(
        update={"analysis_run_id": high.run.run_id, "input_manifest_hash": high.run.input_hash}
    )
    ordered = sort_runs(
        [{"run_id": b.run.run_id, "value": result(b, "F17").value} for b in (low, high)]
    )
    assert ordered[0]["run_id"] == high.run.run_id


def test_R15_stale_policy_clock_does_not_revive_content(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    receipt = PolicyClock(
        snapshot_id="expired-policy",
        retrieved_at=now - timedelta(days=40),
        refresh_by=now - timedelta(days=10),
        available_at=now - timedelta(days=40),
        expires_at=now + timedelta(days=5),
        provenance_reference="Independent retained retrieval receipt; no policy text",
    )
    b = DecisionService(repository).analyze(opt.model_copy(update={"policy_clocks": (receipt,)}))
    d = result(b, "decision").details
    assert "policy_refresh_required" in d["risk_gates"]
    assert result(b, "F18").state == "low"
    assert d["evidence"]["policy"]["snapshots"][-1]["substantive_evidence"] is False


def test_f17_missing_essential_and_disclosed_partial(repository, observation_factory, now):
    _, _, _, mm, _ = setup(repository, observation_factory, now)
    assert sorting_index(mm, config("F1"))["state"] == "insufficient_dimensions"
    cfg = SortConfig(
        version="caller-v2",
        allow_partial=True,
        dimensions=(*config("F3").dimensions, *config("F1", essential=False).dimensions),
    )
    partial = sorting_index(mm, cfg)
    assert partial["state"] == "partial_index" and partial["excluded"] == ["F1"]
    assert partial["included_weight_denominator"] == 1


@pytest.mark.parametrize(
    "fid", ["provider_rpm", "revenue", "monetization", "T4", "outlier_score", "F18", "decision"]
)
def test_f17_provider_and_confidence_firewall(fid):
    with pytest.raises(ValueError):
        config(fid)


@pytest.mark.parametrize(
    "field", ["revenue", "rpm", "auxiliary", "provider_daily_history", "finding"]
)
def test_rule_path_firewall(field):
    from youtube_niche_mcp.decision.models import MetricRule

    with pytest.raises(ValueError):
        MetricRule(
            formula_id="F16",
            path=(field,),
            direction="at_most",
            threshold=Decimal(10),
            reference="Caller",
        )


@pytest.mark.parametrize(
    "fid,state",
    [("F10", "partial_coverage"), ("F12", "protocol_changed"), ("F13", "provider_only")],
)
def test_history_states_block_high_confidence(repository, observation_factory, now, fid, state):
    base, q, opt, mm, _ = setup(repository, observation_factory, now)
    frame = DecisionService(repository).repository.load(
        base.run.cohort_id, base.run.video_cohort_id, base.run.options
    )
    evidence = collect(repository, frame, base, (q,), opt)
    mm.update({m.formula_id: m for m in q.metrics})
    mm = complete_history(mm)
    mm[fid] = mm[fid].model_copy(update={"state": state})
    generic = assemble(
        mm, opt.rubric, policy_state="fresh", classifications=evidence["classifications"]
    )
    assert fid in generic["history_maturity"]["immature"]
    assert generic["history_maturity"]["measurements"][fid]["state"] == state
    assert robustness(evidence, generic, [], opt)["confidence"] == "low"


def test_fresh_policy_receipt_does_not_discredit_retained_policy(
    repository, observation_factory, now
):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    receipt = PolicyClock(
        snapshot_id="fresh-receipt",
        retrieved_at=now - timedelta(days=1),
        refresh_by=now + timedelta(days=1),
        available_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=2),
        provenance_reference="Retained clock",
    )
    b = DecisionService(repository).analyze(opt.model_copy(update={"policy_clocks": (receipt,)}))
    assert result(b, "decision").details["evidence"]["policy"]["state"] == "fresh"


def test_documented_winner_projection_preserves_unknown_entrant_state(
    repository, observation_factory, now
):
    from youtube_niche_mcp.decision.sensitivity import winner_ownership_diagnostic

    _, _, _, mm, _ = setup(repository, observation_factory, now)
    metric = mm["F3"].model_copy(
        update={
            "formula_id": "F21",
            "details": {
                "older_winners": ["a", "b"],
                "newer_winners": ["b", "c"],
            },
        }
    )
    d = winner_ownership_diagnostic(metric, {"a", "b"})
    assert d["replacement_share"] == 0 and d["incumbent_persistence"] == Decimal("0.5")
    assert d["verified_entrant_share"] is None
    assert metric.details["newer_winners"] == ["b", "c"]
