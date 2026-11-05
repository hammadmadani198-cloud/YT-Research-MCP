from datetime import timedelta
from decimal import Decimal

import pytest
from phase3_helpers import metrics, video
from phase4_helpers import make_frame, point

from youtube_niche_mcp.analysis.historical_models import HistoricalOptions, Window
from youtube_niche_mcp.analysis.historical_service import HistoricalService


def catalog_fixture(
    repo, factory, now, *, old_delta=30000, new_delta=70000, missing=False, negative=False
):
    start = now - timedelta(days=30)
    oldrow = (1, video(1), now - timedelta(days=200), [point(start, 100000)])
    sv, _ = make_frame(repo, factory, now, "catalog-start", [oldrow], start)
    points = oldrow[3] + ([] if missing else [point(now, 100000 + (-1 if negative else old_delta))])
    rows = [
        (1, video(1), oldrow[2], points),
        (
            2,
            video(2),
            start + timedelta(days=1),
            [point(start + timedelta(days=2), 1000), point(now, 1000 + new_delta)],
        ),
    ]
    ev, _ = make_frame(repo, factory, now, "catalog-end", rows, now)
    opt = HistoricalOptions(
        cutoff=now,
        age_days=30,
        goal=10000,
        creator_group_version="v1",
        catalog_window=Window(start=start, end=now),
        catalog_start_cohort=sv,
        old_age_days=90,
    )
    return HistoricalService(repo), ev, opt


@pytest.mark.parametrize(
    "old,new,share",
    [(30000, 70000, Decimal("0.3")), (1000, 0, Decimal(1)), (0, 1000, Decimal(0)), (0, 0, None)],
)
def test_H7_incremental_catalog_contribution(repository, observation_factory, now, old, new, share):
    svc, ev, opt = catalog_fixture(
        repository, observation_factory, now, old_delta=old, new_delta=new
    )
    f = metrics(svc.analyze(ev, opt))["F13"]
    assert f.value == share and f.numerator == old and f.denominator == old + new
    assert f.details["increments"]["new_release"] == new
    assert f.details["new_release_exposure_partial"]
    assert f.details["old_age_days"] == 90


@pytest.mark.parametrize(
    "missing,negative,state", [(True, False, "partial_coverage"), (False, True, "source_conflict")]
)
def test_catalog_missing_endpoint_and_correction(
    repository, observation_factory, now, missing, negative, state
):
    svc, ev, opt = catalog_fixture(
        repository, observation_factory, now, missing=missing, negative=negative
    )
    f = metrics(svc.analyze(ev, opt))["F13"]
    assert f.state == state
    if negative:
        assert f.value is None and f.details["increments"]["old"] == -1
    else:
        assert f.details["missing_intervals"] == 1


def test_deleted_video_retained_endpoints(repository, observation_factory, now):
    from youtube_niche_mcp.domain.foundation import Outcome

    svc, ev, opt = catalog_fixture(repository, observation_factory, now)
    obs = observation_factory(0, at=now, entity_id=video(1), capture_id="deleted")
    repository.append(
        obs.model_copy(update={"outcome": Outcome.DELETED_OR_PRIVATE_UNKNOWN, "metrics": {}})
    )
    f = metrics(svc.analyze(ev, opt))["F13"]
    assert f.value == Decimal("0.3")


def post_fixture(
    repo, factory, now, *, pre=True, post=True, post_values=None, late_pre=False, pending=False
):
    t0 = now - timedelta(days=60)
    pre_rows = (
        [
            (
                1,
                video(i + 1),
                now - timedelta(days=120 - i),
                [point(now - timedelta(days=90 - i), v)],
            )
            for i, v in enumerate([1000, 2000, 2000, 3000, 4000])
        ]
        if pre
        else []
    )
    if late_pre:
        pre_rows.append(
            (
                1,
                video(40),
                now - timedelta(days=91),
                [point(now - timedelta(days=61), 999999, available=now)],
            )
        )
    anchor = (1, video(20), now - timedelta(days=90), [point(t0, 100000)])
    pv, _ = make_frame(repo, factory, now, "pre", pre_rows + [anchor], t0)
    post_rows = (
        [
            (1, video(i + 21), t0 + timedelta(days=i + 1), [point(t0 + timedelta(days=i + 31), v)])
            for i, v in enumerate(post_values or [2000, 3000, 4000, 5000, 100000])
        ]
        if post
        else []
    )
    if pending:
        post_rows[-1] = (1, video(25), now - timedelta(days=2), [point(now, 999999)])
    fv, _ = make_frame(repo, factory, now, "post", pre_rows + [anchor] + post_rows, now)
    opt = HistoricalOptions(
        cutoff=now,
        age_days=30,
        goal=10000,
        creator_group_version="v1",
        anchor_at=t0,
        anchor_id=video(20),
        pre_anchor_cohort=pv,
        first_k=5,
    )
    return HistoricalService(repo), fv, opt


@pytest.mark.parametrize(
    "post_values,pre_median,post_median",
    [([2000, 3000, 4000, 5000, 100000], 2000, 4000), ([100, 200, 300, 400, 100000], 2000, 300)],
)
def test_H8_H9_post_hit_baseline(
    repository, observation_factory, now, post_values, pre_median, post_median
):
    svc, fv, opt = post_fixture(repository, observation_factory, now, post_values=post_values)
    f = metrics(svc.analyze(fv, opt))["F20"]
    assert f.value == Decimal(post_median + 1) / Decimal(pre_median + 1)
    assert Decimal(f.details["pre_median"]) == pre_median
    assert Decimal(f.details["post_median"]) == post_median
    assert video(20) not in [
        o["video_id"] for o in f.details["pre_sequence"] + f.details["post_sequence"]
    ]
    assert f.details["post_hits"] == 1 and f.details["post_count"] == 5
    assert "Non-causal" in f.details["interpretation"]
    assert f.value != 2


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"pre": False}, "insufficient_history"),
        ({"post": False}, "insufficient_history"),
        ({"pending": True}, "partial_coverage"),
        ({"late_pre": True}, "available"),
    ],
)
def test_post_hit_missing_pending_future_pre(
    repository, observation_factory, now, changes, expected
):
    svc, fv, opt = post_fixture(repository, observation_factory, now, **changes)
    f = metrics(svc.analyze(fv, opt))["F20"]
    assert f.state == expected
    if changes.get("late_pre"):
        assert f.value == Decimal(4001) / 2001
        assert video(40) not in [o["video_id"] for o in f.details["pre_sequence"]]
    if changes.get("pending"):
        assert f.details["pending"] == 1


def test_first_known_anchor_and_later_huge_hit_do_not_change_pre(
    repository, observation_factory, now
):
    svc, fv, opt = post_fixture(repository, observation_factory, now)
    rule = opt.model_copy(update={"anchor_id": None, "anchor_channel_id": "UC" + f"{1:022d}"})
    f = metrics(svc.analyze(fv, rule))["F20"]
    assert f.details["anchor_id"] == video(20)
    before = f.details["pre_sequence"]
    repository.append(observation_factory(999999999, at=now, entity_id=video(25)))
    assert metrics(svc.analyze(fv, rule))["F20"].details["pre_sequence"] == before
