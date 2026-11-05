from datetime import timedelta
from decimal import Decimal

import pytest
from phase3_helpers import channel, metrics, options, seed, video
from pydantic import ValidationError

from youtube_niche_mcp.analysis.models import Snapshot, VideoInput
from youtube_niche_mcp.analysis.outcomes import resolve
from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.analysis.service import AnalysisService
from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import Outcome as CaptureOutcome
from youtube_niche_mcp.eligibility.models import CohortMember, Subject


def subject_video(now, *, snapshots=(), state="included", **changes):
    body = dict(
        video_id=video(1),
        channel_id=channel(1),
        publication_at=now - timedelta(days=40),
        membership=CohortMember(
            subject=Subject(entity_kind="video", entity_id=video(1)),
            state=state,
            reason="Frozen fixture",
            independence_unit="channel:" + channel(1),
            independence_state="unknown",
        ),
        snapshots=snapshots,
    )
    body.update(changes)
    return VideoInput(**body)


def snapshot(now, **changes):
    body = dict(
        observation_id="official-snapshot",
        source="youtube:videos.list",
        source_kind="public_api",
        observed_at=now - timedelta(days=10),
        available_at=now - timedelta(days=10),
        expires_at=now + timedelta(days=20),
        value=12345,
        precision="exact",
        evidence_state="available",
        metric_definition="public-video-view-v1",
    )
    body.update(changes)
    return Snapshot(**body)


@pytest.mark.parametrize(
    "change,state",
    [
        ({}, "available"),
        ({"value": 0}, "available"),
        ({"source": "nexlev.video_details", "source_kind": "provider"}, "insufficient_history"),
        ({"precision": "rounded"}, "insufficient_history"),
        ({"precision": "approximate"}, "insufficient_history"),
        ({"observed_at": -11}, "insufficient_history"),
        ({"observed_at": -9}, "insufficient_history"),
        ({"available_at": 1}, "insufficient_history"),
        ({"observed_at": 1}, "insufficient_history"),
        ({"expires_at": 0}, "insufficient_history"),
        ({"value": None, "outcome": "deleted_or_private_unknown"}, "not_publicly_available"),
        ({"value": None, "outcome": "API_missing"}, "not_publicly_available"),
    ],
)
def test_shared_resolver_source_age_availability_expiry(now, change, state):
    change = {k: now + timedelta(days=v) if k.endswith("_at") else v for k, v in change.items()}
    v = subject_video(now, snapshots=(snapshot(now, **change),))
    o = resolve(v, options(now), now)
    assert o.state == state and (o.value is None) == (state != "available")


@pytest.mark.parametrize(
    "state,expected",
    [
        ("excluded", "excluded_format"),
        ("pending_classification", "classification_unknown"),
        ("source_conflict", "source_conflict"),
        ("insufficient_evidence", "classification_unknown"),
    ],
)
def test_frozen_membership_states(now, state, expected):
    o = resolve(subject_video(now, state=state, snapshots=(snapshot(now),)), options(now), now)
    assert o.state == expected and o.value is None


def test_tolerance_explicit_forward_window(now):
    s = snapshot(now, observed_at=now - timedelta(days=9), available_at=now - timedelta(days=9))
    v = subject_video(now, snapshots=(s,))
    assert resolve(v, options(now, tolerance_seconds=86400), now).value == 12345
    assert resolve(v, options(now, tolerance_seconds=86399), now).value is None
    early = snapshot(
        now, observed_at=now - timedelta(days=11), available_at=now - timedelta(days=11)
    )
    assert (
        resolve(
            v.model_copy(update={"snapshots": (early,)}), options(now, tolerance_seconds=86400), now
        ).value
        is None
    )


def test_deletion_preserves_valid_history_and_conflicts(now):
    good = snapshot(now)
    missing = snapshot(
        now,
        observation_id="removed",
        observed_at=now,
        available_at=now,
        value=None,
        outcome="deleted_or_private_unknown",
    )
    assert resolve(subject_video(now, snapshots=(good, missing)), options(now), now).value == 12345
    other = good.model_copy(update={"observation_id": "disagree", "value": 1})
    assert (
        resolve(subject_video(now, snapshots=(good, other)), options(now), now).state
        == "source_conflict"
    )


def test_pending_globally_not_miss(repository, observation_factory, now):
    vd, cd, _, opt = seed(
        repository,
        observation_factory,
        now,
        [[None]],
        topics=["a"],
        entry_days=20,
        publication_days=20,
    )
    bundle = AnalysisService(repository).analyze(cd, opt, video_cohort_id=vd)
    result = metrics(bundle)
    assert bundle.outcomes[0].state == "pending_maturity"
    for fid in ("F3", "F4", "F5", "F7", "F19"):
        assert result[fid].value is None and result[fid].pending == 1
    assert result["F3"].details["misses"] == 0
    assert result["F22"].details["u"] == 1 and result["F22"].details["upper"] == "1"


def test_unknown_globally_not_zero(repository, observation_factory, now):
    vd, cd, _, opt = seed(repository, observation_factory, now, [[None], [0]], topics=["a", "b"])
    result = metrics(AnalysisService(repository).analyze(cd, opt, video_cohort_id=vd))
    assert result["F3"].details["misses"] == 1 and result["F3"].unknown == 1
    assert result["F5"].value == 0 and result["floor"].details["observed_zero_count"] == 1
    assert result["F4"].details["unknown_entrants"] == 1 and result["F19"].value is None
    assert result["F22"].details["upper"] == "0.5"


def test_no_history_permission_not_lifetime_backfill(repository, observation_factory, now):
    vd, _, _, opt = seed(repository, observation_factory, now, [[20000]], permissions=False)
    result = metrics(AnalysisService(repository).analyze(vd, opt))
    assert result["F3"].value is None
    assert result["F3"].unknown == 1
    assert result["F5"].value is None


def test_provider_only_target_count_rejected(repository, observation_factory, now):
    vd, _, ids, opt = seed(repository, observation_factory, now, [[None]])
    pub = now - timedelta(days=200)
    repository.append(
        observation_factory(
            999999, entity_id=ids[0], at=pub + timedelta(days=30), source="provider:nexlev"
        )
    )
    f = metrics(AnalysisService(repository).analyze(vd, opt))["F3"]
    assert f.value is None and f.unknown == 1


def test_future_data_future_freeze_and_changed_identity(repository, observation_factory, now):
    vd, _, ids, opt = seed(repository, observation_factory, now, [[12345]])
    service = AnalysisService(repository)
    first = service.analyze(vd, opt)
    pub = now - timedelta(days=200)
    future = observation_factory(
        99999,
        entity_id=ids[0],
        at=pub + timedelta(days=30),
        available=now + timedelta(days=1),
        capture_id="future-unavailable",
    )
    repository.append(future)
    assert service.analyze(vd, opt) == first
    earlier = opt.model_copy(update={"cutoff": now - timedelta(days=3)})
    with pytest.raises(ValueError, match="Future"):
        service.analyze(vd, earlier)
    changed = observation_factory(
        99999,
        entity_id=ids[0],
        at=pub + timedelta(days=30),
        available=now,
        capture_id="newly-available",
    )
    repository.append(changed)
    second = service.analyze(vd, opt)
    assert second.run.run_id != first.run.run_id
    assert (
        second.outcomes[0].state == "source_conflict" and service.inspect(first.run.run_id) == first
    )


def test_duplicate_discovery_routes_cannot_multiply_frame(repository, observation_factory, now):
    vd, _, _, opt = seed(repository, observation_factory, now, [[10000, 10000]])
    service = AnalysisService(repository)
    first = service.analyze(vd, opt)
    # Discovery multiplicity cannot change frozen canonical membership PKs.
    assert first.metrics == service.analyze(vd, opt).metrics
    assert metrics(first)["F3"].denominator == 2
    assert repository.connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0] == 1


def test_no_catalog_review_no_miss_and_no_zero_uploads(repository, observation_factory, now):
    vd, cd, _, opt = seed(repository, observation_factory, now, [[], [100]])
    result = metrics(
        AnalysisService(repository).analyze(
            cd, opt.model_copy(update={"coverage": ()}), video_cohort_id=vd
        )
    )
    assert result["F19"].details["unknown_entrants"] == 2 and result["F19"].details["attempts"] == 1
    assert result["F19"].value is None and result["F4"].value is None


def test_independent_run_replay_immutable_expiry_and_purge(repository, observation_factory, now):
    import sqlite3

    vd, _, _, opt = seed(repository, observation_factory, now, [[10000]])
    service = AnalysisService(repository)
    first = service.analyze(vd, opt)
    repository.clock = lambda: now + timedelta(hours=1)
    assert service.analyze(vd, opt) == first
    with pytest.raises(sqlite3.IntegrityError, match="Append-only"):
        repository.connection.execute('UPDATE analysis_metric_results SET formula_version="bad"')
    repository.clock = lambda: now + timedelta(days=29)
    with pytest.raises(AnalysisUnavailable, match="retention"):
        service.inspect(first.run.run_id)
    assert repository.purge_expired()["analysis_runs"] == 1


def test_missing_topic_and_conflicted_topic_coverage(repository, observation_factory, now):
    vd, _, _, opt = seed(repository, observation_factory, now, [[15000]])
    f = metrics(AnalysisService(repository).analyze(vd, opt))
    assert f["F8"].state == "insufficient_classification_coverage"
    assert (
        f["F9"].details["topics"]["HHI"] is None and f["F9"].details["unclassified_mass"] == 15000
    )


def test_multilabel_mass_split_and_taxonomy_future_ignored(repository, observation_factory, now):
    import json

    from youtube_niche_mcp.eligibility.models import Claim, NicheMembership, TaxonomyNode
    from youtube_niche_mcp.eligibility.repository import EligibilityRepository

    vd, _, ids, opt = seed(repository, observation_factory, now, [[12000]], topics=["a"])
    e = EligibilityRepository(repository)
    at = now - timedelta(days=2)
    e.add_node(
        TaxonomyNode(
            node_id="b",
            taxonomy_version="topics-v1",
            label="B",
            level="topic_family",
            parent_id="niche",
            available_at=at,
        )
    )
    subject = Subject(entity_kind="video", entity_id=ids[0])
    for topic, state, when, source in [
        ("b", "included", at, "second"),
        ("a", "excluded", now, "later"),
    ]:
        c = Claim(
            subject=subject,
            field="niche_membership",
            value={"node_id": topic, "state": state},
            basis="human_review",
            source=source,
            source_version="v1",
            observed_at=when,
            available_at=when,
            reason="Synthetic review",
            data_origin="independent_annotation",
            permission_state="permitted",
        )
        eid = e.append_claim(c)
        e.assign_niche(
            NicheMembership(
                subject=subject,
                node_id=topic,
                taxonomy_version="topics-v1",
                state=state,
                confidence="high",
                evidence_ids=(eid,),
                rule_version="topic-v1",
                source=source,
                decided_at=when,
                available_at=when,
                reason="Synthetic review",
            )
        )
    f = metrics(AnalysisService(repository).analyze(vd, opt))
    assert f["F8"].value == 2 and f["F9"].details["topics"]["mass"] == {"a": "6000", "b": "6000"}
    definition = json.loads(
        repository.connection.execute(
            "SELECT definition_json FROM cohort_definitions WHERE cohort_id=?", (vd,)
        ).fetchone()[0]
    )
    definition["boundary"]["taxonomy_version"] = "different"
    # API rejects a mismatched auxiliary frozen video frame, never mixes taxonomies.
    from phase3_helpers import frozen

    from youtube_niche_mcp.eligibility.models import CohortDefinition

    definition["cohort_id"] = "wrong-boundary"
    frozen(repository.connection, CohortDefinition.model_validate(definition), ())
    with pytest.raises(ValueError, match="different niche"):
        AnalysisService(repository).analyze("wrong-boundary", opt, video_cohort_id=vd)


def test_shorts_live_uncertain_followups_explicit(repository, observation_factory, now):
    vd, _, ids, opt = seed(
        repository, observation_factory, now, [[20000, 15000, 15000]], member_state="excluded"
    )
    # Entire excluded frame never enters a baseline/floor/demand outcome denominator.
    f = metrics(
        AnalysisService(repository).analyze(vd, opt.model_copy(update={"anchor_id": ids[0]}))
    )
    assert f["F3"].excluded == 3 and f["F3"].denominator == 0 and f["F5"].value is None


def test_analysis_bulk_reads_deep_sized_frame(repository, observation_factory, now):
    with atomic(repository.connection):
        vd, cd, _, opt = seed(
            repository, observation_factory, now, [[15000] * 30 for _ in range(100)]
        )
    queries = []
    repository.connection.set_trace_callback(
        lambda sql: queries.append(sql) if sql.lstrip().startswith("SELECT") else None
    )
    result = AnalysisService(repository).analyze(cd, opt, video_cohort_id=vd, persist=False)
    repository.connection.set_trace_callback(None)
    assert len(result.outcomes) == 3000 and metrics(result)["F3"].denominator == 3000
    assert len(queries) <= 12  # fixed bulk queries, no per-video DB fetch


@pytest.mark.parametrize(
    "change",
    [
        {"age_days": 0},
        {"tolerance_seconds": -1},
        {"pooling_k": 0},
        {"goal": -1},
        {"classification_minimum": Decimal("1.1")},
        {"baseline_cutoff": "future", "candidate_id": video(1)},
    ],
)
def test_invalid_configuration(now, change):
    if change.get("baseline_cutoff") == "future":
        change["baseline_cutoff"] = now + timedelta(days=1)
    with pytest.raises(ValidationError):
        options(now, **change)


def test_public_surface_completed_without_formula_changes():
    from youtube_niche_mcp.services.catalog import IMPLEMENTED_TOOLS, PLANNED_TOOLS

    assert IMPLEMENTED_TOOLS == PLANNED_TOOLS and len(IMPLEMENTED_TOOLS) == 15


def test_followups_mature_private_pending_and_anchor_exclusion(
    repository, observation_factory, now
):
    vd, _, ids, opt = seed(
        repository,
        observation_factory,
        now,
        [[20000, 15000, None, None]],
        entry_days=50,
        spacing=10,
    )
    removal = observation_factory(0, entity_id=ids[2], at=now, capture_id="removed-followup")
    removal = removal.model_copy(
        update={
            "outcome": CaptureOutcome.DELETED_OR_PRIVATE_UNKNOWN,
            "metrics": {},
        }
    )
    repository.append(removal)
    f = metrics(
        AnalysisService(repository).analyze(vd, opt.model_copy(update={"anchor_id": ids[0]}))
    )["F7"]
    window = f.details["windows"]["5"]
    assert [p["state"] for p in window["positions"]] == [
        "available",
        "not_publicly_available",
        "pending_maturity",
        "not_yet_occurred",
        "not_yet_occurred",
    ]
    assert window["R_k"] is None and window["actual_followups"] == 3


def test_f2_contributing_peer_channel_balance(repository, observation_factory, now):
    vd, _, ids, opt = seed(
        repository, observation_factory, now, [[300], [10] * 20, [1000]], publication_days=40
    )
    # A separate candidate later than the peer publications, with no own prior outcomes.
    from youtube_niche_mcp.analysis.baselines import baseline

    frame = AnalysisService(repository).repository.load(vd, None, opt)
    candidate = frame.videos[0].model_copy(update={"publication_at": now - timedelta(days=35)})
    frame = frame.model_copy(update={"videos": (candidate, *frame.videos[1:])})
    outcome_rows = tuple(resolve(v, opt, now) for v in frame.videos)
    b, pooled, detail = baseline(
        frame, outcome_rows, opt.model_copy(update={"candidate_id": ids[0], "baseline_cutoff": now})
    )
    assert b == pooled and detail["peer_videos"] == 21 and detail["peer_channels"] == 2
    assert Decimal(detail["peer_log"]) > Decimal(detail["peer_video_weighted_log"])
