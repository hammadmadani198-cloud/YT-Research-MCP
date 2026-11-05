"""Q1–Q15 and qualitative decision semantics with independently declared expectations."""

from datetime import timedelta
from decimal import Decimal

import pytest
from phase5_helpers import pilot, premise, production, review, source, task

from youtube_niche_mcp.qualitative.dimensions import (
    content_gaps,
    faceless_feasibility,
    idea_feasibility,
    packaging_patterns,
    production_assessment,
    risk_assessment,
    saturation,
    series_structure,
    source_to_story,
)
from youtube_niche_mcp.qualitative.models import CreatorCapacity
from youtube_niche_mcp.qualitative.pilot import pilot_downside


def gap(now, **changes):
    body = dict(
        kind="gap",
        scope="content",
        demand="positive",
        demand_evidence_ids=("material-gap",),
        supply="inadequate",
        reviewed_alternative_ids=("material-gap",),
        differentiated=True,
        feasible_production=True,
        source_annotation_ids=("source",),
    )
    body.update(changes)
    return review(now, body, "gap")


def capacity(now, hours=24, cash=1000, **changes):
    body = dict(
        profile_id="creator",
        declared_at=now,
        expires_at=now + timedelta(days=20),
        currency="USD",
        hours_per_week=hours,
        monthly_cash=cash,
        releases_per_week=1,
        skills=(),
        narration=True,
        animation=True,
        footage_access=True,
        team_size=1,
    )
    body.update(changes)
    return CreatorCapacity(**body)


def test_Q1_high_demand_low_idea_depth(now):
    candidates = ["a", "b", "c"]
    rows = [source(now), premise(now, "a", finite_inventory=True)]
    result = idea_feasibility(rows, candidates)
    assert result["value"] == Decimal(1) / 3 and result["finite_inventory_ids"] == ["a"]
    assert len(result["unvalidated_ids"]) == 2
    assert content_gaps([source(now), gap(now)])["gaps"][0]["state"] == "supported_gap"


def test_Q2_broad_sustainable_inventory(now):
    ids = [str(i) for i in range(30)]
    rows = [source(now)] + [
        premise(
            now, i, family_node_ids=(f"family-{int(i) % 3}",), recurring_entities=(f"entity-{i}",)
        )
        for i in ids
    ]
    result = idea_feasibility(rows, ids)
    assert result["value"] == 1 and result["validated_distinct_count"] == 30
    assert len(result["viable_families"]) == 3 and result["human_minimum_10_met"]


def test_Q3_saturated_repeated_premises(now):
    ids = [str(i) for i in range(10)]
    rows = [source(now)] + [premise(now, i) for i in ids]
    rows += [
        review(
            now,
            dict(
                kind="relation",
                left_candidate_id="0",
                right_candidate_id=i,
                relation="near_duplicate",
            ),
            f"relation-{i}",
        )
        for i in ids[1:]
    ]
    result = idea_feasibility(rows, ids)
    assert result["value"] == Decimal("0.1") and result["duplicate_density"] == Decimal("0.9")
    assert len(saturation(rows, [])["canonical_near_duplicate_pairs"]) == 9


@pytest.mark.parametrize(
    "demand,expected",
    [
        ("absent", "insufficient_demand_evidence"),
        ("unknown", "insufficient_demand_evidence"),
        ("comment_only", "possible_gap"),
        ("positive", "supported_gap"),
    ],
)
def test_Q4_Q5_gap_demand_corroboration(now, demand, expected):
    assert content_gaps([source(now), gap(now, demand=demand)])["gaps"][0]["state"] == expected


@pytest.mark.parametrize(
    "changes,state",
    [
        ({"supply": "served"}, "saturated"),
        ({"supply": "unknown"}, "insufficient_supply_evidence"),
        ({"reviewed_alternative_ids": ()}, "insufficient_supply_evidence"),
        ({"differentiated": False}, "insufficient_differentiation"),
        ({"feasible_production": False}, "insufficient_differentiation"),
        ({"source_annotation_ids": ()}, "possible_gap"),
        ({"demand_evidence_ids": ()}, "insufficient_demand_evidence"),
    ],
)
def test_gap_missing_evidence(now, changes, state):
    assert content_gaps([source(now), gap(now, **changes)])["gaps"][0]["state"] == state


@pytest.mark.parametrize("scope", ["content", "packaging", "production"])
def test_gap_types_remain_separate(now, scope):
    result = content_gaps([source(now), gap(now, scope=scope)])["gaps"][0]
    assert result["scope"] == scope and result["state"] == "supported_gap"


def test_Q6_faceless_expensive(now):
    face = review(
        now,
        dict(
            kind="faceless",
            checked_paths=("animation", "archive"),
            central_host_required=False,
            field_footage_required=False,
            expert_interview_required=True,
        ),
        "faceless",
    )
    prod = production(
        now,
        tasks=(
            task(30, 500, "edit_animation", required_skills=("animation",)),
            task(20, 700, "rights"),
        ),
    )
    assert faceless_feasibility([face])["paths"][0]["state"] == "reviewed_path"
    assert production_assessment([prod], None, None)["value"] == 50


def test_Q7_easy_production_weak_sources(now):
    rows = [source(now, credible=False), premise(now, "x"), production(now, 2, 0)]
    assert production_assessment(rows, None, None)["value"] == 2
    assert idea_feasibility(rows, ["x"])["value"] == 0
    assert source_to_story(rows)["unverified_or_weak_ids"] == ["source"]


@pytest.mark.parametrize(
    "dependency,clearance,state",
    [
        ("high", "required", "high_clearance_dependency"),
        ("low", "verified", "low_apparent_dependency"),
        ("moderate", "required", "moderate_clearance_burden"),
        ("low", "uncertain", "uncertain"),
        ("unknown", "required", "uncertain"),
    ],
)
def test_Q8_Q9_asset_rights(now, dependency, clearance, state):
    a = review(
        now,
        dict(
            kind="rights",
            asset_id="asset",
            asset_type="archive",
            dependency=dependency,
            clearance=clearance,
            license_reference="Synthetic checked license" if clearance == "verified" else None,
        ),
    )
    r = risk_assessment([a], now)
    assert r["rights_legal"]["assets"][0]["state"] == state
    assert r["platform_policy"]["state"] == "unknown"


def test_Q9_source_rich_diversity(now):
    rows = [
        source(now),
        source(now, "academic", category="academic", primary=False),
        source(now, "archive", category="archive"),
    ]
    r = source_to_story(rows)
    assert len(r["categories"]) == 3 and r["single_fragile_source_dependency"] is False
    assert r["secondary_source_ids"] == ["academic"]


@pytest.mark.parametrize(
    "domain",
    ["medical", "legal", "finance", "crime", "geopolitics", "history_controversy", "science"],
)
def test_Q10_factual_burden_is_not_allegation(now, domain):
    a = review(
        now,
        dict(
            kind="factual",
            domain=domain,
            verification_burden="high",
            identifiable_entity=True,
            allegation_verification_needed=True,
            disputed_claims=True,
            volatile=True,
            correction_burden="high",
        ),
    )
    r = risk_assessment([a], now)
    assert r["factual_editorial"]["reviews"][0]["verification_burden"] == "high"
    assert r["rights_legal"]["state"] == "unknown"


def test_Q11_series_structure(now):
    rows = [
        review(
            now,
            dict(
                kind="continuation",
                from_candidate=str(i),
                to_candidate=str(i + 1),
                structure="chronological",
                compatible=True,
                exhaustible=False,
            ),
            str(i),
        )
        for i in range(4)
    ]
    r = series_structure(rows, [str(i) for i in range(5)])
    assert r["continuation_depth"] == 5 and r["compatible_link_count"] == 4
    assert not r["finite_exhaustible_concern"]


def test_playlist_is_not_continuation_validation(now):
    a = review(
        now,
        dict(
            kind="continuation",
            from_candidate="a",
            to_candidate="b",
            structure="category",
            compatible=True,
            exhaustible=True,
            playlist_only=True,
        ),
    )
    r = series_structure([a], ["a", "b"])
    assert r["compatible_link_count"] == 0 and r["finite_exhaustible_concern"]


def test_cycle_does_not_invent_infinite_series(now):
    rows = [
        review(
            now,
            dict(
                kind="continuation",
                from_candidate=a,
                to_candidate=b,
                structure="entity",
                compatible=True,
                exhaustible=None,
            ),
            a,
        )
        for a, b in [("a", "b"), ("b", "a")]
    ]
    r = series_structure(rows, ["a", "b"])
    assert r["cycle_present"] and r["continuation_depth"] is None


@pytest.mark.parametrize(
    "hours,state",
    [(6, "incompatible_declared_constraints"), (24, "compatible_declared_constraints")],
)
def test_Q12_Q13_declared_capacity(now, hours, state):
    rows = [production(now)]
    burden = production_assessment(rows, None, None)
    r = production_assessment(rows, capacity(now, hours), None)
    assert r["value"] == burden["value"] == 12
    assert r["cases"][0]["compatibility"]["state"] == state
    if hours == 24:
        assert (
            r["cases"][0]["compatibility"]["releases_per_week_capacity_before_additional_overhead"]
            == 2
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"skills": None},
        {"hours_per_week": None},
        {"monthly_cash": None},
        {"releases_per_week": None},
        {"currency": "PKR"},
    ],
)
def test_capacity_missing_inputs_unknown(now, changes):
    r = production_assessment([production(now)], capacity(now, **changes), None)
    assert r["cases"][0]["compatibility"]["state"] == "unknown"


def test_Q14_limited_pilot_runway(now):
    r = pilot_downside(pilot(now, runway_until=now + timedelta(days=20)))
    assert r["planned_cash_loss"] == 400 and r["planned_hours"] == 50
    assert r["cash_limit_exceeded"] and not r["runway_covers_K_maturity"]
    assert r["first_mature_not_before"] == (now + timedelta(days=30)).isoformat()
    assert r["complete_K_mature_not_before"] == (now + timedelta(days=58)).isoformat()


def test_Q15_evidence_runway_no_income(now):
    r = pilot_downside(pilot(now, 10, runway_until=now + timedelta(days=100)))
    assert r["planned_attempts"] == 10 and r["planned_cash_loss"] == 700
    assert not r["income_assumed"] and r["evidence_requirements"]["F19"]["ten_attempts_planned"]
    assert r["runway_covers_K_maturity"] and r["peak_no_income_deficit"] == 700
    assert all(
        v["history_state"].startswith("unresolved") for v in r["evidence_requirements"].values()
    )


def test_pilot_revisions_and_overhead(now):
    r = pilot_downside(
        pilot(now, evaluation_hours=3, overhead_hours=7, contracted_overhead_cash=20)
    )
    assert r["planned_hours"] == 60 and r["planned_cash_loss"] == 420
    assert r["outflow_schedule"][-1]["cumulative_no_income_deficit"] == 420


def test_no_creator_economics():
    r = pilot_downside(None)
    assert r["value"] is None and r["state"] == "creator_input_required"


def test_multilabel_premise_count_conserved(now):
    r = idea_feasibility([source(now), premise(now, "x", family_node_ids=("a", "b"))], ["x"])
    assert r["value"] == 1 and r["viable_families"] == ["a", "b"]


def test_title_rewrites_do_not_count_as_ideas(now):
    first = premise(now, "a")
    second = premise(
        now,
        "b",
        subject=first.payload.subject,
        viewer_promise=first.payload.viewer_promise,
        mechanism=first.payload.mechanism,
        long_form_treatment=first.payload.long_form_treatment,
    )
    r = idea_feasibility([source(now), first, second], ["a", "b"])
    assert r["value"] == Decimal("0.5")


def test_uncertain_relation_has_no_precise_f15(now):
    a = review(
        now,
        dict(kind="relation", left_candidate_id="a", right_candidate_id="b", relation="uncertain"),
    )
    r = idea_feasibility([source(now), premise(now, "a"), premise(now, "b"), a], ["a", "b"])
    assert r["value"] is None and r["state"] == "source_conflict"


@pytest.mark.parametrize(
    "relation", ["distinct", "same_topic_different_mechanism", "same_mechanism_different_subject"]
)
def test_distinct_relations_keep_premises(now, relation):
    a = review(
        now, dict(kind="relation", left_candidate_id="a", right_candidate_id="b", relation=relation)
    )
    assert (
        idea_feasibility([source(now), premise(now, "a"), premise(now, "b"), a], ["a", "b"])[
            "value"
        ]
        == 1
    )


@pytest.mark.parametrize("layout_count", [1, 3])
def test_packaging_public_patterns(now, layout_count):
    rows = [
        review(
            now,
            dict(
                kind="packaging",
                video_id=str(i),
                title_length=40,
                title_mechanisms=("question",),
                promise_structure="explanation",
                thumbnail_reviewed=True,
                face="no_face",
                dominant_asset="map",
                text_density="low",
                composition=f"layout-{i % layout_count}",
            ),
            str(i),
        )
        for i in range(3)
    ]
    r = packaging_patterns(rows)
    assert r["title_mechanisms"] == {"question": 3} and len(r["compositions"]) == layout_count
    assert r["title_length_median"] == 40 and "CTR" in r["limitations"][0]
