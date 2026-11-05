import json
from datetime import timedelta

import pytest
from phase3_helpers import metrics, video
from phase4_helpers import make_frame, point
from test_historical_catalog_posthit import catalog_fixture, post_fixture
from test_historical_panels import setup_panels

from youtube_niche_mcp.analysis.historical_models import HistoricalOptions, Window
from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.cli import main


def test_replay_protocol_snapshot_detects_mutation(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    first = svc.analyze(nc, opt, video_cohort_id=nv)
    assert svc.analyze(nc, opt, video_cohort_id=nv) == first == svc.inspect(first.run.run_id)
    repository.connection.execute(
        "UPDATE discovery_runs SET query='changed' WHERE run_id='new-run'"
    )
    with pytest.raises(AnalysisUnavailable, match="changed"):
        svc.inspect(first.run.run_id)
    later = svc.analyze(nc, opt, video_cohort_id=nv)
    assert (
        later.run.run_id != first.run.run_id
        and metrics(later)["F21"].state == "unstable_discovery_protocol"
    )


@pytest.mark.parametrize(
    "table",
    ["discovery_runs", "cohort_definitions", "creator_group_memberships", "classification_claims"],
)
def test_removed_dependency_blocks_read(repository, observation_factory, now, table):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    first = svc.analyze(nc, opt, video_cohort_id=nv)
    repository.connection.execute(f"DELETE FROM {table}")
    with pytest.raises(AnalysisUnavailable):
        svc.inspect(first.run.run_id)


def test_expiry_blocks_saved_result(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    first = svc.analyze(nc, opt, video_cohort_id=nv)
    repository.clock = lambda: now + timedelta(days=31)
    with pytest.raises(AnalysisUnavailable, match="expired"):
        svc.inspect(first.run.run_id)


def test_current_only_cannot_supply_momentum_winners_or_post_baseline(
    repository, observation_factory, now
):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    repository.connection.execute("DELETE FROM statistical_history")
    # Actual outcome rows removed; current lifetime counts cannot enter V(1).
    repository.connection.execute("DELETE FROM video_observations")
    repository.append(observation_factory(999999, at=now, entity_id=video(101)))
    ff = metrics(svc.analyze(nc, opt, video_cohort_id=nv))
    assert ff["F11"].value is None and ff["F11"].state == "insufficient_same_age_history"
    assert ff["F21"].state == "insufficient_panel_history"
    assert not ff["F21"].details["newer_winners"]


def test_F13_current_only_rejected(repository, observation_factory, now):
    svc, ev, opt = catalog_fixture(repository, observation_factory, now)
    repository.connection.execute(
        "DELETE FROM statistical_history WHERE observed_at<?", (now.isoformat(),)
    )
    repository.connection.execute(
        "DELETE FROM video_observations WHERE observed_at<?", (now.isoformat(),)
    )
    f = metrics(svc.analyze(ev, opt))["F13"]
    assert f.value is None and f.state in {"insufficient_history", "policy_permission_required"}


def test_F20_current_only_rejected(repository, observation_factory, now):
    svc, fv, opt = post_fixture(repository, observation_factory, now)
    repository.connection.execute("DELETE FROM statistical_history")
    repository.connection.execute("DELETE FROM video_observations")
    repository.append(observation_factory(9999999, at=now, entity_id=video(20)))
    f = metrics(svc.analyze(fv, opt))["F20"]
    assert f.value is None and f.state == "insufficient_history"


def test_future_panel_cannot_enter_past_cutoff(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    earlier = opt.model_copy(
        update={"newer": opt.newer.model_copy(update={"cutoff": now - timedelta(days=3)})}
    )
    with pytest.raises(ValueError, match="Future cohort"):
        svc.analyze(nc, earlier, video_cohort_id=nv)


def test_boundary_mismatch_rejected(repository, observation_factory, now):
    from youtube_niche_mcp.eligibility.models import Boundary

    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    boundary = Boundary(
        boundary_id="other", taxonomy_version="v1", node_ids=("other",), classifier_version="v1"
    )
    vv, cc = make_frame(
        repository,
        observation_factory,
        now,
        "different",
        [(1, video(201), now - timedelta(days=6), [point(now - timedelta(days=5), 10000)])],
        now - timedelta(days=2),
        boundary=boundary,
    )
    opt = opt.model_copy(
        update={"newer": opt.newer.model_copy(update={"cohort_id": cc, "video_cohort_id": vv})}
    )
    ff = metrics(svc.analyze(cc, opt, video_cohort_id=vv))
    assert ff["F11"].state == ff["F12"].state == ff["F21"].state == "insufficient_panel_history"


@pytest.mark.parametrize(
    "field,value", [("goal", 20000), ("tolerance_seconds", 1), ("provider_source_version", "v2")]
)
def test_goal_age_regime_comparability(repository, observation_factory, now, field, value):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)], new_panel={field: value}
    )
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F21"]
    assert f.state == (
        "unstable_discovery_protocol"
        if field == "provider_source_version"
        else "insufficient_panel_history"
    )


def test_discovery_later_than_old_cutoff_not_backdated(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    opt = opt.model_copy(
        update={"older": opt.older.model_copy(update={"discovery_run_ids": ("new-run",)})}
    )
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F12"]
    assert f.state == "insufficient_panel_history" and f.value is None


def test_partial_same_age_and_winner_outcomes_not_misses(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000), (2, 20000)]
    )
    repository.connection.execute("DELETE FROM video_observations WHERE video_id=?", (video(102),))
    repository.connection.execute(
        "DELETE FROM statistical_history WHERE entity_id=?", (video(102),)
    )
    ff = metrics(svc.analyze(nc, opt, video_cohort_id=nv))
    assert ff["F11"].state == ff["F21"].state == "partial_coverage"
    assert ff["F11"].details["newer"]["unknown"] == 1
    assert ff["F21"].details["later_unknown_outcomes"] == ["group:creator2"]


def test_pending_same_age_not_miss(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)], new_panel={"age_days": 10}
    )
    assert (
        metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F11"].state
        == "insufficient_panel_history"
    )


def test_search_total_ignored_and_protocol_timestamps_excluded(
    repository, observation_factory, now
):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000), (2, 10000)]
    )
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F12"]
    assert (
        f.value == 1
        and f.details["discovery_protocol_ids"][0] == f.details["discovery_protocol_ids"][1]
    )
    assert f.details["changes"]["eligible_videos"]["newer"] == 2
    assert "total_results" not in json.dumps(f.details)


def test_bulk_reads_constant_in_video_count(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)] * 300, [(1, 10000)] * 300
    )
    statements = []
    repository.connection.set_trace_callback(statements.append)
    svc.analyze(nc, opt, video_cohort_id=nv, persist=False)
    repository.connection.set_trace_callback(None)
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 60


def test_CLI_offline_formulas_and_historical_run(
    repository, observation_factory, now, tmp_path, capsys
):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    path = tmp_path / "options.json"
    path.write_text(opt.model_dump_json(), encoding="utf-8")
    db = repository.connection.execute("PRAGMA database_list").fetchone()[2]
    repository.connection.commit()
    assert main(["analysis", "formulas"]) == 0
    assert json.loads(capsys.readouterr().out)["historical_formulas"] == [
        "F10",
        "F11",
        "F12",
        "F13",
        "F20",
        "F21",
    ]
    assert (
        main(
            [
                "--db",
                db,
                "analysis",
                "historical",
                "--cohort",
                nc,
                "--video-cohort",
                nv,
                "--options",
                str(path),
            ]
        )
        == 0
    )
    bundle = json.loads(capsys.readouterr().out)
    assert bundle["run"]["formula_version"] == "phase4-v1"
    assert main(["--db", db, "analysis", "inspect", bundle["run"]["run_id"]]) == 0
    assert json.loads(capsys.readouterr().out)["run"]["run_id"] == bundle["run"]["run_id"]


def test_analytics_has_no_HTTP_dependency():
    from pathlib import Path

    root = Path(__file__).parents[1] / "src/youtube_niche_mcp/analysis"
    assert all(
        "import httpx" not in p.read_text() and "YouTubeClient" not in p.read_text()
        for p in root.glob("*.py")
    )


@pytest.mark.parametrize(
    "change",
    [
        {"old_age_days": 30},
        {
            "catalog_window": Window(start="2026-10-01T00:00:00Z", end="2026-10-02T00:00:00Z"),
            "catalog_start_cohort": "frame",
        },
        {"anchor_id": video(1)},
        {
            "cutoff": "2026-09-01T00:00:00Z",
            "observation_window": Window(start="2026-10-01T00:00:00Z", end="2026-10-02T00:00:00Z"),
        },
    ],
)
def test_invalid_history_options_rejected(now, change):
    with pytest.raises(ValueError):
        HistoricalOptions(
            **(
                {"cutoff": now, "age_days": 30, "goal": 10000, "creator_group_version": "v1"}
                | change
            )
        )
