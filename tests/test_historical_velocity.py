from datetime import timedelta
from decimal import Decimal

import pytest
from phase3_helpers import metrics, video
from phase4_helpers import make_frame, point

from youtube_niche_mcp.analysis.historical_formulas import velocity
from youtube_niche_mcp.analysis.historical_models import HistoricalOptions, Window
from youtube_niche_mcp.analysis.historical_service import HistoricalService
from youtube_niche_mcp.analysis.history_gate import availability
from youtube_niche_mcp.analysis.repository import AnalysisUnavailable


@pytest.mark.parametrize(
    "values,hours,change",
    [
        ([0, 1000, 3000], [0, 24, 48], Decimal(1000) / 24),  # H1
        ([0, 2000, 3000], [0, 24, 48], -Decimal(1000) / 24),  # H2
        ([0, 720, 1920], [0, 72, 192], Decimal(0)),
        ([1000, 900, 1200], [0, 24, 96], Decimal(25) / 3),
    ],
)
def test_actual_rates_and_acceleration(repository, observation_factory, now, values, hours, change):
    at = now - timedelta(days=9)
    rows = [
        (
            1,
            video(1),
            at - timedelta(days=1),
            [point(at + timedelta(hours=h), v) for h, v in zip(hours, values, strict=True)],
        )
    ]
    vd, _ = make_frame(repository, observation_factory, now, "velocity", rows, now)
    options = HistoricalOptions(
        cutoff=now,
        age_days=30,
        goal=10000,
        creator_group_version="v1",
        observation_window=Window(start=at, end=now),
    )
    f = metrics(HistoricalService(repository).analyze(vd, options))["F10"]
    own = f.details["own_history"][0]
    assert own["state"] == "available"
    assert Decimal(own["details"]["acceleration"][0]["change_in_velocity"]) == pytest.approx(change)
    assert Decimal(own["details"]["intervals"][0]["elapsed_seconds"]) == hours[1] * 3600
    assert own["details"]["history_class"] == "OWN_HISTORY"
    assert (
        "negative_delta" in own["details"]["flags"]
        if values[1] < values[0]
        else not own["details"]["flags"]
    )


@pytest.mark.parametrize(
    "case,state,count",
    [
        ("two", "available", 2),
        ("current", "insufficient_history", 1),
        ("duplicate", "available", 2),
        ("conflict", "source_conflict", 0),
        ("missing_middle", "available", 2),
        ("out_of_order", "available", 3),
        ("future_available", "insufficient_history", 1),
        ("regime", "source_conflict", 0),
    ],
)
def test_snapshot_edges(repository, observation_factory, now, case, state, count):
    from test_analysis_integrity import snapshot, subject_video

    at = now - timedelta(days=3)
    a = snapshot(now, observation_id="a", observed_at=at, available_at=at, value=100)
    b = snapshot(now, observation_id="b", observed_at=now, available_at=now, value=400)
    points = [a, b]
    if case == "current":
        points = [b]
    if case == "duplicate":
        points.append(a.model_copy(update={"observation_id": "duplicate"}))
    if case == "conflict":
        points.append(a.model_copy(update={"value": 101, "observation_id": "conflicting"}))
    if case == "out_of_order":
        points = [
            b,
            a,
            a.model_copy(
                update={
                    "observation_id": "middle",
                    "value": 200,
                    "observed_at": at + timedelta(days=1),
                }
            ),
        ]
    if case == "future_available":
        points[-1] = b.model_copy(update={"available_at": now + timedelta(days=1)})
    if case == "regime":
        points[-1] = b.model_copy(update={"metric_definition": "changed"})
    r = velocity(subject_video(now, snapshots=tuple(points)), now, now, Window(start=at, end=now))
    assert r["state"] == state and r["details"]["observations"] == count
    if count == 2:
        assert r["details"]["acceleration_state"] == "insufficient_history"
        assert r["value"] == Decimal(300) / 72


def test_provider_auxiliary_separate_anomalies(repository, observation_factory, now):
    at = now - timedelta(days=10)
    rows = [
        (
            1,
            video(1),
            at - timedelta(days=1),
            [
                point(at + timedelta(days=d), v, "provider:nexlev.history")
                for d, v in [(0, 100), (1, 0), (3, 200)]
            ],
        )
    ]
    vd, _ = make_frame(repository, observation_factory, now, "provider", rows, now)
    opt = HistoricalOptions(
        cutoff=now,
        age_days=30,
        goal=10000,
        creator_group_version="v1",
        observation_window=Window(start=at, end=now),
        provider_history_policy="separate_auxiliary",
    )
    f = metrics(HistoricalService(repository).analyze(vd, opt))["F10"]
    assert f.state == "provider_history_only"
    assert f.details["own_history"][0]["value"] is None
    assert set(f.details["provider_history"][0]["details"]["flags"]) == {
        "negative_delta",
        "irregular_or_missing_dates",
        "rebound",
        "stale_timestamps",
        "zero_count",
    }
    assert not metrics(
        HistoricalService(repository).analyze(
            vd, opt.model_copy(update={"provider_history_policy": "exclude"})
        )
    )["F10"].details["provider_history"]


def test_replay_new_data_revocation_and_expiry(repository, observation_factory, now):
    at = now - timedelta(days=50)
    rows = [
        (1, video(1), at - timedelta(days=1), [point(at, 100), point(at + timedelta(days=1), 200)])
    ]
    vd, _ = make_frame(
        repository, observation_factory, now, "replay", rows, now - timedelta(days=1)
    )
    opt = HistoricalOptions(
        cutoff=now,
        age_days=30,
        goal=10000,
        creator_group_version="v1",
        observation_window=Window(start=at, end=now),
    )
    svc = HistoricalService(repository)
    first = svc.analyze(vd, opt)
    assert svc.analyze(vd, opt) == first == svc.inspect(first.run.run_id)
    repository.append(observation_factory(1000, entity_id=video(1), at=now))
    later = svc.analyze(vd, opt)
    assert later.run.run_id != first.run.run_id
    assert svc.inspect(first.run.run_id) == first
    repository.connection.execute("DELETE FROM retention_permissions")
    with pytest.raises(AnalysisUnavailable, match="dependency"):
        svc.inspect(first.run.run_id)


@pytest.mark.parametrize(
    "states,expected",
    [
        ([], "insufficient_history"),
        (["available"], "available"),
        (["available", "pending_maturity"], "partial_coverage"),
        (["partial_coverage", "partial_coverage"], "partial_coverage"),
        (["policy_permission_required"], "policy_permission_required"),
        (["source_conflict", "available"], "source_conflict"),
        (["pending_maturity"], "pending_maturity"),
    ],
)
def test_shared_history_gate(states, expected):
    assert availability(states) == expected
