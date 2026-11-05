"""Additional completeness checks: declared inputs, concurrency-free offline execution."""

from datetime import timedelta

import pytest
from phase5_helpers import pilot, production, review, source, task
from test_qualitative_dimensions import capacity

from youtube_niche_mcp.qualitative.dimensions import (
    content_gaps,
    idea_feasibility,
    production_assessment,
    series_structure,
    source_to_story,
)
from youtube_niche_mcp.qualitative.models import PilotProfile
from youtube_niche_mcp.qualitative.packaging import parse_title
from youtube_niche_mcp.qualitative.pilot import pilot_downside


@pytest.mark.parametrize("field", ["rpm", "revenue", "cpm", "expected_income", "roi"])
def test_pilot_income_fields_rejected(now, field):
    body = pilot(now).model_dump(mode="json")
    body[field] = 10
    with pytest.raises(ValueError):
        PilotProfile.model_validate(body)


@pytest.mark.parametrize("capability", ["narration", "animation", "footage_access"])
def test_capacity_required_capabilities(now, capability):
    p = production(now, required_capabilities=(capability,))
    assert (
        production_assessment([p], capacity(now, **{capability: False}), None)["cases"][0][
            "compatibility"
        ]["state"]
        == "incompatible_declared_constraints"
    )
    assert (
        production_assessment([p], capacity(now, **{capability: None}), None)["cases"][0][
            "compatibility"
        ]["state"]
        == "unknown"
    )


def test_task_narration_requires_declared_capability(now):
    p = production(now, tasks=(task(1, 0, "narration"),))
    assert (
        production_assessment([p], capacity(now, narration=False), None)["cases"][0][
            "compatibility"
        ]["state"]
        == "incompatible_declared_constraints"
    )


def test_required_team_size(now):
    p = production(now, required_team_size=2)
    assert (
        production_assessment([p], capacity(now), None)["cases"][0]["compatibility"]["state"]
        == "incompatible_declared_constraints"
    )


def test_unchecked_sources_are_unknown(now):
    assert source_to_story([source(now, checked=False)])["state"] == "unknown"


def test_unreviewed_candidates_are_not_zero(now):
    r = idea_feasibility([], ["a", "b"])
    assert r["value"] is None and r["state"] == "unknown"


def test_model_gap_is_only_possible(now):
    a = review(
        now,
        dict(
            kind="gap",
            scope="content",
            demand="positive",
            demand_evidence_ids=("material-review",),
            supply="inadequate",
            reviewed_alternative_ids=("material-review",),
            differentiated=True,
            feasible_production=True,
            source_annotation_ids=("source",),
        ),
        source_type="model",
        model_version="fixture",
        prompt_version="fixture",
    )
    assert content_gaps([source(now), a])["gaps"][0]["state"] == "possible_gap"


@pytest.mark.parametrize(
    "title,features",
    [
        ("How did it work?", ("question",)),
        ("5 mechanisms explained", ("statement", "number")),
        ("Why these 2 systems?", ("question", "number")),
    ],
)
def test_title_parser_is_bounded_and_descriptive(title, features):
    p = parse_title("synthetic", title)
    assert p.title_mechanisms == features and p.title_length == len(title)
    assert not p.thumbnail_reviewed and p.promise_structure is None


def test_pilot_delay_and_earlier_cash_outflow(now):
    p = pilot(now)
    releases = list(p.releases)
    releases[-1] = releases[-1].model_copy(
        update={"delay_days": 7, "cash_outflow_at": now + timedelta(days=2)}
    )
    p = p.model_copy(update={"releases": tuple(releases)})
    r = pilot_downside(p)
    assert r["complete_K_mature_not_before"] == (now + timedelta(days=65)).isoformat()
    outflow = next(row for row in r["outflow_schedule"] if row["label"] == releases[-1].release_id)
    assert outflow["at"] == (now + timedelta(days=2)).isoformat() and r["planned_cash_loss"] == 400


def test_maximum_budget_continuation_graph_without_recursion(now):
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
        for i in range(499)
    ]
    result = series_structure(rows, [str(i) for i in range(500)])
    assert result["continuation_depth"] == 500 and not result["cycle_present"]
