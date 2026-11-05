from datetime import timedelta
from decimal import Decimal

import pytest
from phase3_helpers import channel, metrics, video
from phase4_helpers import make_frame, point
from test_historical_panels import setup_panels
from test_nexlev_evidence import ingest, record

from youtube_niche_mcp.analysis.historical_models import HistoricalOptions, Window
from youtube_niche_mcp.analysis.historical_service import HistoricalService
from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.collectors.nexlev.models import HistoryPoint
from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository


def test_actual_T2_daily_history_keeps_quantities_separate(repository, observation_factory, now):
    at = now - timedelta(days=11)
    vd, cd = make_frame(
        repository, observation_factory, now, "T2", [(1, video(1), at, [point(now, 999999)])], now
    )
    rec = record(now, route="nexlev.daily_analytics", kind="channel", entity=channel(1)).model_copy(
        update={
            "history": (
                HistoryPoint(date=at, subscribers=100, views=1000, videos=0),
                HistoryPoint(date=at + timedelta(days=1), subscribers=80, views=900, videos=0),
                HistoryPoint(date=at + timedelta(days=3), subscribers=200, views=2000, videos=0),
            )
        }
    )
    ingest(NexLevRepository(repository), "daily", rec)
    opt = HistoricalOptions(
        cutoff=now,
        age_days=30,
        goal=10000,
        creator_group_version="v1",
        observation_window=Window(start=at, end=now),
        provider_history_policy="separate_auxiliary",
    )
    svc = HistoricalService(repository)
    bundle = svc.analyze(cd, opt, video_cohort_id=vd)
    f = metrics(bundle)["F10"]
    assert f.state == "provider_history_only" and f.details["own_history"][0]["value"] is None
    series = {s["quantity"]: s for s in f.details["provider_history"] if "quantity" in s}
    assert set(series) == {"views", "subscribers", "videos"}
    assert series["views"]["trust_class"] == "T2"
    assert {"negative_delta", "rebound", "gap", "stale_series", "zero_video_count"} <= set(
        series["views"]["flags"]
    )
    assert series["views"]["intervals"][0]["delta"] == -100
    assert Decimal(series["views"]["intervals"][0]["rate"]) == -Decimal(100) / 24
    assert svc.inspect(bundle.run.run_id) == bundle
    repository.connection.execute("DELETE FROM provider_runs")
    with pytest.raises(AnalysisUnavailable):
        svc.inspect(bundle.run.run_id)


@pytest.mark.parametrize(
    "field,value",
    [
        ("outlier_score", 10000),
        ("vph", 999999),
        ("rpm", 100),
        ("monthly_revenue", 999999),
        ("monetized", True),
        ("geography", "US"),
    ],
)
def test_provider_proprietary_fields_never_enter_historical_equations(
    repository, observation_factory, now, field, value
):
    svc, nc, nv, opt = setup_panels(repository, observation_factory, now, [(1, 100)], [(1, 200)])
    before = svc.analyze(nc, opt, video_cohort_id=nv)
    ingest(
        NexLevRepository(repository),
        "proprietary",
        record(now, entity=video(101), **{field: value}),
    )
    after = svc.analyze(nc, opt, video_cohort_id=nv)
    assert before == after
    assert metrics(after)["F11"].value == 2 and not metrics(after)["F21"].details["newer_winners"]
