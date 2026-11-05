from datetime import timedelta
from decimal import Decimal

import pytest
from phase3_helpers import metrics, video
from phase4_helpers import discovery, make_frame, point

from youtube_niche_mcp.analysis.historical_models import HistoricalOptions, Panel, Window
from youtube_niche_mcp.analysis.historical_service import HistoricalService


def setup_panels(
    repository,
    factory,
    now,
    old_values,
    new_values,
    *,
    new_protocol=None,
    new_panel=None,
    entries=None,
    new_roster=(1, 2, 3),
):
    oldat, newat = now - timedelta(days=12), now - timedelta(days=6)
    oldrows = [
        (ci, video(i + 1), oldat, [point(oldat + timedelta(days=1), v)])
        for i, (ci, v) in enumerate(old_values)
    ]
    newrows = [
        (ci, video(i + 101), newat, [point(newat + timedelta(days=1), v)])
        for i, (ci, v) in enumerate(new_values)
    ]
    ov, oc = make_frame(repository, factory, now, "older", oldrows, now - timedelta(days=9))
    nv, nc = make_frame(
        repository,
        factory,
        now,
        "newer",
        newrows,
        now - timedelta(days=2),
        entries=entries,
        roster=new_roster,
    )
    discovery(repository, "old-run", now - timedelta(days=9), [r[1] for r in oldrows])
    discovery(
        repository,
        "new-run",
        now - timedelta(days=2),
        [r[1] for r in newrows],
        **(new_protocol or {}),
    )
    common = dict(
        age_days=1,
        goal=10000,
        capability_mode="official",
        provider_source_version="v1",
        coverage_reference="enumerated bounded fixture",
        coverage_epoch="v1",
        creator_group_version="v1",
    )
    old = Panel(
        cohort_id=oc,
        video_cohort_id=ov,
        cutoff=now - timedelta(days=9),
        publication=Window(start=oldat - timedelta(days=1), end=oldat + timedelta(days=2)),
        discovery_run_ids=("old-run",),
        **common,
    )
    new = Panel(
        cohort_id=nc,
        video_cohort_id=nv,
        cutoff=now,
        publication=Window(start=newat - timedelta(days=1), end=newat + timedelta(days=2)),
        discovery_run_ids=("new-run",),
        **common,
    )
    if new_panel:
        new = new.model_copy(update=new_panel)
    opt = HistoricalOptions(
        cutoff=now,
        age_days=1,
        goal=10000,
        creator_group_version="v1",
        older=old,
        newer=new,
        recent_entry=new.publication,
    )
    return HistoricalService(repository), nc, nv, opt


@pytest.mark.parametrize("new,expected", [(15000, "1.5"), (10000, "1"), (5000, "0.5")])
def test_H3_H4_demand_direction(repository, observation_factory, now, new, expected):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000), (2, 10000)], [(1, new), (2, new)]
    )
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F11"]
    assert f.value == Decimal(expected)
    assert f.details["relative_change"] == str(Decimal(expected) - 1)
    assert f.details["older"]["channels"] == 2
    assert f.details["matched_ratio"] == expected


def test_prolific_channel_does_not_dominate(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository,
        observation_factory,
        now,
        [(1, 100), (2, 100), (3, 100)],
        [(1, 100)] * 30 + [(2, 1000), (3, 1000)],
    )
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F11"]
    assert f.value == 10 and Decimal(f.details["newer"]["video_weighted_median"]) == 100


@pytest.mark.parametrize(
    "count,delta", [(1, Decimal("-0.5")), (2, Decimal(0)), (3, Decimal("0.5"))]
)
def test_H5_supply_named_quantities(repository, observation_factory, now, count, delta):
    svc, nc, nv, opt = setup_panels(
        repository,
        observation_factory,
        now,
        [(1, 100), (2, 200)],
        [(ci, 100) for ci in range(1, count + 1)],
    )
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F12"]
    assert f.value == delta and f.state == "available"
    assert f.details["changes"]["eligible_videos"]["relative_change"] == str(delta)
    assert f.details["census"] is False


@pytest.mark.parametrize(
    "protocol",
    [
        {"query": "different"},
        {"provider": "nexlev"},
        {"filters": {"type": "channel"}},
        {"route": "playlistItems.list"},
        {"version": "expanded routes"},
    ],
)
def test_material_protocol_changes_rejected(repository, observation_factory, now, protocol):
    svc, nc, nv, opt = setup_panels(
        repository,
        observation_factory,
        now,
        [(1, 10000)],
        [(1, 10000), (2, 20000)],
        new_protocol=protocol,
    )
    ff = metrics(svc.analyze(nc, opt, video_cohort_id=nv))
    assert ff["F12"].state == ff["F21"].state == "unstable_discovery_protocol"
    assert ff["F12"].value is None and "replacement_share" not in ff["F21"].details


@pytest.mark.parametrize(
    "changes",
    [
        {"coverage_epoch": "semantic index backfill"},
        {"capability_mode": "broader"},
        {"age_days": 2},
        {"creator_group_version": "v2"},
    ],
)
def test_H6_H12_panel_changes(repository, observation_factory, now, changes):
    svc, nc, nv, opt = setup_panels(
        repository,
        observation_factory,
        now,
        [(1, 10000)],
        [(1, 10000), (2, 20000)],
        new_panel=changes,
    )
    ff = metrics(svc.analyze(nc, opt, video_cohort_id=nv))
    expected = (
        "coverage_not_comparable"
        if "coverage_epoch" in changes
        else "unstable_discovery_protocol"
        if "capability_mode" in changes
        else "insufficient_panel_history"
    )
    assert ff["F12"].state == ff["F21"].state == expected


def test_incomplete_pagination_disclosed(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository,
        observation_factory,
        now,
        [(1, 10000)],
        [(1, 10000)],
        new_protocol={"partial": True},
    )
    assert metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F12"].state == "partial_coverage"


@pytest.mark.parametrize(
    "old,new,replacement,persistence",
    [
        ([(1, 20000)], [(1, 20000)], "0", "1"),  # H11
        ([(1, 20000)], [(2, 20000)], "1", "0"),  # H10
        ([(1, 20000), (2, 20000)], [(2, 20000), (3, 20000)], "0.5", "0.5"),
        ([(1, 0)], [(1, 0)], None, None),
    ],
)
def test_winner_dynamics_denominators(
    repository, observation_factory, now, old, new, replacement, persistence
):
    svc, nc, nv, opt = setup_panels(repository, observation_factory, now, old, new)
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F21"]
    assert f.details["replacement_share"] == replacement
    assert f.details["incumbent_persistence"] == persistence
    assert f.value is None and f.details["fractions"]["replacement_share"]["denominator"] == (
        0 if replacement is None else len(new)
    )


def test_verified_niche_entrant_and_unknown_not_incumbent(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository,
        observation_factory,
        now,
        [(1, 20000)],
        [(1, 20000), (2, 20000), (3, 20000)],
        entries={2: now - timedelta(days=6), 3: None},
    )
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F21"]
    assert f.details["counts"]["verified_entrants"] == 1
    assert f.details["counts"]["unknown_entry"] == 1
    assert f.details["counts"]["incumbents"] == 1
    assert Decimal(f.details["verified_entrant_share"]) == Decimal(1) / 3
    assert f.details["entrant_bounds"] == [str(Decimal(1) / 3), str(Decimal(2) / 3)]


def test_roster_expansion_rejected(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 20000)], [(1, 20000)], new_roster=(1, 2, 3, 4)
    )
    assert (
        metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F21"].state == "coverage_not_comparable"
    )
