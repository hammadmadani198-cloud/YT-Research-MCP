from datetime import timedelta
from decimal import Decimal

import pytest
from phase3_helpers import metrics, video
from phase4_helpers import make_frame, point
from test_analysis_integrity import snapshot, subject_video
from test_historical_panels import setup_panels

from youtube_niche_mcp.analysis.historical_formulas import catalog, entry_bucket, momentum, velocity
from youtube_niche_mcp.analysis.historical_models import HistoricalOptions, Window
from youtube_niche_mcp.analysis.historical_service import HistoricalService


def test_research_winner_illustration_exact_denominators(repository, observation_factory, now):
    from youtube_niche_mcp.analysis.historical_formulas import winner_change

    old = {
        "winners": set(range(12)),
        "unknown_outcome_units": set(),
        "roster": set(range(16)),
        "entry": {},
    }
    new = {
        "winners": set(range(6)) | set(range(12, 16)),
        "unknown_outcome_units": set(),
        "roster": set(range(16)),
        "entry": {i: "verified_entrant" if i in {12, 13, 14} else "incumbent" for i in range(16)},
    }
    f = winner_change(old, new, "available")
    assert f["details"]["replacement_share"] == Decimal("0.4")
    assert f["details"]["incumbent_persistence"] == Decimal("0.5")
    assert f["details"]["verified_entrant_share"] == Decimal("0.3")
    assert f["details"]["fractions"]["replacement_share"] == {"numerator": 4, "denominator": 10}


def test_no_catalog_endpoints_is_unknown_not_zero(now):
    from youtube_niche_mcp.analysis.models import AnalysisFrame
    from youtube_niche_mcp.eligibility.models import Boundary

    v = subject_video(
        now, snapshots=(snapshot(now, observed_at=now, available_at=now, value=900000),)
    )
    boundary = Boundary(
        boundary_id="test", taxonomy_version="v1", node_ids=("niche",), classifier_version="v1"
    )
    frame = AnalysisFrame(
        cohort_id="test",
        video_cohort_id="test",
        kind="eligible_long_form",
        boundary=boundary,
        freeze_at=now - timedelta(days=30),
        video_freeze_at=now - timedelta(days=30),
        members=(v.membership,),
        videos=(v,),
        input_ids=(),
        expires_at=None,
        input_hash="test",
    )
    opt = HistoricalOptions(
        cutoff=now,
        age_days=30,
        goal=10000,
        creator_group_version="v1",
        catalog_window=Window(start=now - timedelta(days=30), end=now),
        catalog_start_cohort="test",
    )
    f = catalog(frame, frame, opt, now)
    assert f["value"] is None and f["state"] == "insufficient_history"


@pytest.mark.parametrize(
    "field,change",
    [
        ("evidence_state", "approximate"),
        ("precision", "rounded"),
        ("outcome", "API_missing"),
        ("expires_at", "expired"),
    ],
)
def test_nonexact_or_unretained_points_do_not_count(now, field, change):
    a = snapshot(now)
    b = a.model_copy(
        update={"observation_id": "b", "observed_at": now, "available_at": now, "value": 50000}
    )
    if change == "expired":
        change = now - timedelta(seconds=1)
    a = a.model_copy(update={field: change})
    f = velocity(
        subject_video(now, snapshots=(a, b)),
        now,
        now,
        Window(start=now - timedelta(days=30), end=now),
    )
    assert f["value"] is None and f["details"]["observations"] == 1


def test_same_age_pending_counts_exposed(repository, observation_factory, now):
    svc, nc, nv, opt = setup_panels(
        repository, observation_factory, now, [(1, 10000)], [(1, 10000)]
    )
    opt = opt.model_copy(
        update={
            "older": opt.older.model_copy(update={"age_days": 10}),
            "newer": opt.newer.model_copy(update={"age_days": 10}),
        }
    )
    f = metrics(svc.analyze(nc, opt, video_cohort_id=nv))["F11"]
    assert f.value is None and f.details["older"]["pending"] == f.details["newer"]["pending"] == 1


def test_provider_only_outlier_snapshot_rejected_even_auxiliary(now):
    a = snapshot(now, source_kind="provider", source="provider:nexlev.outlier", value=100)
    b = a.model_copy(
        update={"observation_id": "b", "observed_at": now, "available_at": now, "value": 1000000}
    )
    assert (
        velocity(
            subject_video(now, snapshots=(a, b)),
            now,
            now,
            Window(start=now - timedelta(days=30), end=now),
            provider=True,
        )["value"]
        is None
    )


def test_old_account_new_niche_uses_only_entry_clock(now):
    from youtube_niche_mcp.eligibility.models import CohortMember, Subject

    m = CohortMember(
        subject=Subject(entity_kind="channel", entity_id="UC" + "a" * 22),
        state="included",
        reason="fixture",
        independence_unit="channel:test",
        independence_state="unknown",
        entry_status={
            "first_observed_niche_entry": (now - timedelta(days=2)).isoformat(),
            "account_created_at": "2007-01-01T00:00:00Z",
        },
    )
    assert entry_bucket([m], Window(start=now - timedelta(days=3), end=now)) == "verified_entrant"


def test_missing_catalog_chronology_cannot_be_recreated(repository, observation_factory, now):
    from test_historical_catalog_posthit import catalog_fixture

    svc, ev, opt = catalog_fixture(repository, observation_factory, now)
    repository.connection.execute("DELETE FROM classification_claims WHERE field='publication_at'")
    # Frozen member references are now unreadable, so calculation itself cannot claim completeness.
    from youtube_niche_mcp.analysis.repository import AnalysisUnavailable

    with pytest.raises(AnalysisUnavailable):
        svc.analyze(ev, opt)


def test_empty_momentum_denominator_undefined():
    old = dict(
        aggregate=Decimal(0),
        state="available",
        measurement_definitions=["v1"],
        channel_medians={"a": Decimal(0)},
    )
    new = dict(
        aggregate=Decimal(100),
        state="available",
        measurement_definitions=["v1"],
        channel_medians={"a": Decimal(100)},
    )
    f = momentum(old, new)
    assert f["value"] is None and f["denominator"] == 0 and f["details"]["relative_change"] is None


def test_sister_channels_are_one_winner_unit(repository, observation_factory, now):
    from youtube_niche_mcp.analysis.historical_formulas import winners
    from youtube_niche_mcp.analysis.historical_models import Panel
    from youtube_niche_mcp.analysis.historical_service import measurement
    from youtube_niche_mcp.analysis.outcomes import resolve

    at = now - timedelta(days=5)
    vd, cd = make_frame(
        repository,
        observation_factory,
        now,
        "sisters",
        [
            (1, video(1), at, [point(at + timedelta(days=1), 20000)]),
            (2, video(2), at, [point(at + timedelta(days=1), 30000)]),
        ],
        now,
        group_shared=True,
    )
    p = Panel(
        cohort_id=cd,
        video_cohort_id=vd,
        cutoff=now,
        publication=Window(start=at, end=now),
        age_days=1,
        goal=10000,
        capability_mode="fixture",
        provider_source_version="v1",
        coverage_reference="fixture",
        coverage_epoch="v1",
        creator_group_version="v1",
    )
    opt = HistoricalOptions(cutoff=now, age_days=1, goal=10000, creator_group_version="v1")
    frame = HistoricalService(repository).repository.load(cd, vd, measurement(opt))
    oo = [resolve(v, measurement(opt), now) for v in frame.videos]
    assert winners(frame, oo, p, None)["winners"] == {"group:shared"}
