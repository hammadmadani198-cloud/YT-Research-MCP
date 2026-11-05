"""Adversarial public projections use retained frozen engines, never invented metrics."""

from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
from phase3_helpers import channel, options, video
from phase4_helpers import discovery
from phase5_helpers import review
from phase6_helpers import setup
from pydantic import SecretStr
from test_eligibility import claim
from test_historical_panels import setup_panels
from test_nexlev_evidence import ingest, record
from test_qualitative_dimensions import capacity, gap
from test_tools_phase7 import sort_config

from youtube_niche_mcp.analysis.service import AnalysisService
from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.decision.models import (
    DecisionOptions,
    DecisionRubric,
    PolicyClock,
    SensitivityPlan,
)
from youtube_niche_mcp.decision.service import DecisionService
from youtube_niche_mcp.eligibility.models import CohortDefinition, Subject
from youtube_niche_mcp.eligibility.repository import EligibilityRepository
from youtube_niche_mcp.history.retention import RetentionRepository, StoragePermission
from youtube_niche_mcp.qualitative.service import QualitativeService
from youtube_niche_mcp.tools.runtime import PublicSurface
from youtube_niche_mcp.tools.schemas import (
    CompareRequest,
    CompetitorCompareRequest,
    CompetitorRequest,
    CompetitorWatchRequest,
    DetailRequest,
    DiscoverRequest,
    NicheWatchRequest,
    ResearchRequest,
)


def detail(run):
    return DetailRequest(research_id=run.run.run_id, limit=20)


def dimensions(result):
    return {m.dimension: m for m in result.metrics}


@pytest.mark.anyio
async def test_supported_frame_and_route_sensitive_case(repository, observation_factory, now):
    _, _, opt, _, _ = setup(
        repository,
        observation_factory,
        now,
        values=[[15000] * 6, [100] * 6, [100] * 6],
        official_span=6,
    )
    opt = opt.model_copy(update={"rubric": opt.rubric.model_copy(update={"required_history": ()})})
    run = DecisionService(repository).analyze(opt)
    public = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_niche_research", ResearchRequest(research_id=run.run.run_id)
    )
    assert public.state == "weak_under_goal"
    assert public.confidence["F18"]["components"]["sensitivity"]["route"]["state"] == "sensitive"
    assert public.data["sensitivity_warnings"]


@pytest.mark.anyio
async def test_strong_limited_history_goal_and_creator_sort_preservation(
    repository, observation_factory, now
):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    opt = opt.model_copy(
        update={
            "rubric": opt.rubric.model_copy(update={"required_history": ()}),
            "creator": capacity(now, hours=1),
        }
    )
    run = DecisionService(repository).analyze(opt)
    surface = PublicSurface(Settings(), history=repository)
    public = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(research_id=run.run.run_id)
    )
    assert public.state in {"supported", "supported_with_caveats"}, public
    assert public.confidence["F18"]["assessment_scope"]["required_history"] == []
    sorted_public = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(research_id=run.run.run_id, sorting=sort_config())
    )
    assert (
        sorted_public.state == public.state
        and sorted_public.data["creator_fit"] == public.data["creator_fit"]
    )


@pytest.mark.anyio
async def test_all_gap_states_and_packaging_coverage(repository, observation_factory, now):
    _, q, opt, _, ids = setup(repository, observation_factory, now)
    service = QualitativeService(repository)
    expected = {
        "positive": "supported_gap",
        "comment_only": "possible_gap",
        "absent": "insufficient_demand_evidence",
        "served": "saturated",
        "no_supply": "insufficient_supply_evidence",
        "same": "insufficient_differentiation",
    }
    annotations = []
    for name in expected:
        change = (
            {"demand": name}
            if name in {"positive", "comment_only", "absent"}
            else {"supply": "served"}
            if name == "served"
            else {"supply": "unknown"}
            if name == "no_supply"
            else {"differentiated": False}
        )
        a = gap(now, scope="packaging", **change).model_copy(
            update={"annotation_id": "gap-" + name}
        )
        service.annotate(a)
        annotations.append(a.annotation_id)
    for i in range(3):
        a = review(
            now,
            dict(
                kind="packaging",
                video_id=ids[i],
                title_mechanisms=["question"],
                title_length=40,
                thumbnail_reviewed=i < 2,
                dominant_asset="diagram",
                composition="centered diagram",
                text_density="low",
            ),
            "pack-" + str(i),
        )
        service.annotate(a)
        annotations.append(a.annotation_id)
    newq = service.analyze(
        q.run.cohort_id,
        q.run.options.model_copy(
            update={"annotation_ids": (*q.run.options.annotation_ids, *annotations)}
        ),
        video_cohort_id=q.run.video_cohort_id,
    )
    run = DecisionService(repository).analyze(
        opt.model_copy(update={"qualitative_run_ids": (newq.run.run_id,)})
    )
    surface = PublicSurface(Settings(), history=repository)
    result = await surface.dispatch("youtube_niche_content_gaps", detail(run))
    states = {r["annotation_id"].removeprefix("gap-"): r["state"] for r in result.evidence}
    assert states == expected
    assert all(r["review"]["scope"] == "packaging" and r["topic_nodes"] for r in result.evidence)
    packaging = await surface.dispatch("youtube_niche_packaging", detail(run))
    patterns = dimensions(packaging)["packaging_patterns"].details
    assert patterns["thumbnail_review_count"] == 2 and patterns["unreviewed_thumbnails"] == 1
    assert patterns["compositions"] == {"centered diagram": 2}
    assert '"ctr"' not in packaging.model_dump_json()


@pytest.mark.anyio
@pytest.mark.parametrize("change", [{"goal": 25000}, {"age_days": 60}, {"own_minimum": 3}])
async def test_incompatible_measurements_are_not_compared(
    repository, observation_factory, now, change
):
    base, _, opt, _, _ = setup(repository, observation_factory, now)
    other = AnalysisService(repository).analyze(
        base.run.cohort_id,
        base.run.options.model_copy(update=change),
        video_cohort_id=base.run.video_cohort_id,
    )
    service = DecisionService(repository)
    run = service.analyze(opt)
    changed = service.analyze(
        opt.model_copy(
            update={
                "base_run_id": other.run.run_id,
                "qualitative_run_ids": (),
                **{k: v for k, v in change.items() if k in {"age_days", "goal"}},
            }
        )
    )
    result = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_niche_compare", CompareRequest(research_ids=(run.run.run_id, changed.run.run_id))
    )
    assert result.state == "incompatible_runs"


@pytest.mark.anyio
async def test_discovery_counts_dedup_weak_routes_and_no_false_absence(
    repository, observation_factory, now
):
    _, _, _, _, ids = setup(repository, observation_factory, now)
    discovery(
        repository,
        "declared-weak",
        now - timedelta(days=1),
        ids,
        query="weak case",
        route="official_search",
    )
    surface = PublicSurface(Settings(), history=repository)
    found = await surface.dispatch("youtube_niche_discover", DiscoverRequest(query="Synthetic"))
    assert len(found.evidence) == 1
    row = found.evidence[0]
    assert row["candidate_channel_count"] == 3 and row["candidate_video_count"] == 18
    assert row["weak_case_route_present"] and {r["provider"] for r in row["evidence_routes"]} == {
        "youtube",
        "nexlev",
    }
    repository.connection.execute("DELETE FROM discovery_runs")
    zero = await surface.dispatch("youtube_niche_discover", DiscoverRequest(query="Synthetic"))
    assert (
        zero.state == "available"
        and zero.evidence[0]["initial_evidence_state"] == "candidate_evidence"
    )
    assert zero.data["ranking"] == "none"


@pytest.mark.anyio
async def test_geo_language_basis_and_provider_firewall(repository, observation_factory, now):
    _, _, opt, _, ids = setup(repository, observation_factory, now, complete=False)
    e = EligibilityRepository(repository)
    freeze = now - timedelta(days=2)
    cases = [
        ("en", "human_review", True, "verified_english"),
        ("en-US", "default_audio_language", False, "likely_english"),
        ("mixed", "human_review", True, "mixed_language"),
        ("en", "text_language", False, "unknown"),
    ]
    for vid, (value, basis, complete, _) in zip(ids, cases, strict=False):
        e.append_claim(
            claim(
                freeze,
                "spoken_language",
                value,
                basis,
                subject=Subject(entity_kind="video", entity_id=vid),
                complete_review=complete,
            )
        )
    e.append_claim(
        claim(
            freeze,
            "spoken_language",
            "hi",
            "human_review",
            subject=Subject(entity_kind="video", entity_id=ids[4]),
            complete_review=True,
        )
    )
    e.append_claim(
        claim(
            freeze,
            "spoken_language",
            "en",
            "provider_label",
            subject=Subject(entity_kind="video", entity_id=ids[4]),
        )
    )
    ingest(
        NexLevRepository(repository),
        "geo",
        record(now, kind="channel", entity=channel(1), geography={"US": 70}, rpm=50),
    )
    ingest(
        NexLevRepository(repository),
        "translated-only",
        record(
            now,
            entity=ids[3],
            transcript_metadata={"selected_language": "en", "translated": True, "original": False},
        ),
    )
    run = DecisionService(repository).analyze(opt)
    result = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_niche_geo_language", detail(run)
    )
    by_id = {r["subject"]["entity_id"]: r for r in result.evidence}
    for vid, case in zip(ids, cases, strict=False):
        assert by_id[vid]["spoken_language"]["label"] == case[3]
    assert by_id[ids[4]]["spoken_language"]["state"] == "conflicting"
    assert any(
        r["field"] == "geography" and r["interpretation"] == "provider_estimate_context_only"
        for r in result.data["provider_geography_language_context"]
    )
    assert '"rpm"' not in result.model_dump_json()
    assert any(
        r["field"] == "transcript_metadata" and r["value"]["translated"]
        for r in result.data["provider_geography_language_context"]
    )
    assert by_id[ids[0]]["audience_country"]["state"] == "not_publicly_available"


@pytest.mark.anyio
async def test_risk_policy_clocks_stay_stale_after_sorting(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    receipt = PolicyClock(
        snapshot_id="stale",
        retrieved_at=now - timedelta(days=40),
        refresh_by=now - timedelta(days=10),
        available_at=now - timedelta(days=40),
        expires_at=now + timedelta(days=5),
        provenance_reference="Synthetic independent receipt",
    )
    opt = opt.model_copy(update={"policy_clocks": (receipt,)})
    run = DecisionService(repository).analyze(opt)
    surface = PublicSurface(Settings(), history=repository)
    public = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(research_id=run.run.run_id, sorting=sort_config())
    )
    assert public.confidence["level"] == "low"
    context = await surface.dispatch(
        "youtube_niche_risk", DetailRequest(research_id=public.research_id)
    )
    assert "policy_refresh_required" in context.model_dump_json()
    assert (
        dimensions(context)["rights_legal"].details["assets"][0]["state"]
        == "low_apparent_dependency"
    )
    assert '"legal_verdict"' not in context.model_dump_json()


@pytest.mark.anyio
@pytest.mark.parametrize("case", ["rising", "protocol", "coverage"])
async def test_history_panels_keep_available_and_unavailable_states(
    repository, observation_factory, now, case
):
    service, cid, vid, historical = setup_panels(
        repository,
        observation_factory,
        now,
        [(1, 10000), (2, 10000)],
        [(1, 20000), (2, 20000)],
        new_protocol={"query": "different"} if case == "protocol" else None,
        new_panel={"coverage_epoch": "changed"} if case == "coverage" else None,
    )
    base = AnalysisService(repository).analyze(
        cid, options(now, age_days=1, first_k=None), video_cohort_id=vid
    )
    h = service.analyze(cid, historical, video_cohort_id=vid)
    opt = DecisionOptions(
        cutoff=now,
        age_days=1,
        goal=10000,
        tolerance_seconds=0,
        base_run_id=base.run.run_id,
        historical_run_ids=(h.run.run_id,),
        rubric=DecisionRubric(version="explicit-synthetic", rules=()),
        sensitivity=SensitivityPlan(mode="quick", max_runs=8, declared_at=now),
    )
    run = DecisionService(repository).analyze(opt)
    result = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_niche_history", detail(run)
    )
    mm = dimensions(result)
    assert result.state == "available" and mm["F20"].value is None
    if case == "rising":
        assert Decimal(mm["F11"].value) == 2 and mm["F21"].state == "available"
    else:
        assert mm["F21"].state == (
            "unstable_discovery_protocol" if case == "protocol" else "coverage_not_comparable"
        )


@pytest.mark.anyio
async def test_competitor_unknown_ownership_and_hybrid_conflict(
    repository, observation_factory, now
):
    _, _, opt, _, _ = setup(repository, observation_factory, now, known_groups=False)
    e = EligibilityRepository(repository)
    e.append_claim(
        claim(
            now,
            "faceless",
            "hybrid",
            "human_review",
            subject=Subject(entity_kind="channel", entity_id=channel(1)),
            complete_review=True,
        )
    )
    e.append_claim(
        claim(
            now,
            "faceless",
            "faceless",
            "provider_label",
            subject=Subject(entity_kind="channel", entity_id=channel(1)),
        )
    )
    run = DecisionService(repository).analyze(opt)
    result = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_competitor_compare",
        CompetitorCompareRequest(channel_ids=(channel(1), channel(2)), research_id=run.run.run_id),
    )
    assert result.evidence[0]["eligibility"]["faceless"]["state"] == "conflicting"
    assert result.evidence[0]["ownership"]["state"] == "unknown"
    assert result.evidence[0]["breakout_dependence"]["mature_videos"] == 6
    assert result.evidence[0]["confidence"]["F18"] is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    "provider,status", [("youtube", 403), ("youtube", 503), ("nexlev", 429), ("nexlev", 503)]
)
async def test_quota_and_degraded_refresh_preserve_research(
    repository, observation_factory, now, provider, status
):
    _, _, opt, _, ids = setup(repository, observation_factory, now)
    run = DecisionService(repository).analyze(opt)
    calls = []

    async def handler(request):
        calls.append(request.url.path)
        return httpx.Response(
            status,
            json={
                "error": {
                    "errors": [{"reason": "quotaExceeded" if status == 403 else "backendError"}],
                    "message": "synthetic failure",
                }
            },
        )

    if provider == "nexlev":
        RetentionRepository(repository).record_permission(
            StoragePermission(
                source="nexlev.similar_channels",
                approval_reference="synthetic",
                verified_by="test",
                verified_at=now - timedelta(days=1),
                expires_at=now + timedelta(days=1),
                statistical_months=1,
            )
        )
    surface = PublicSurface(
        Settings(
            youtube_api_key=SecretStr("test-key"),
            nexlev_api_key=SecretStr("test-nexlev"),
            api_max_retries=0,
        ),
        history=repository,
        youtube_transport=httpx.MockTransport(handler),
        nexlev_transport=httpx.MockTransport(handler),
    )
    plan = {"refresh": True, "request_id": "failure"}
    plan.update(
        {"video_ids": [ids[0]]}
        if provider == "youtube"
        else {"provider_policy": "prefer_nexlev", "similar_channel": channel(1)}
    )
    public = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(research_id=run.run.run_id, acquisition=plan)
    )
    assert public.research_id == run.run.run_id and public.state == "history_immature", public
    assert len(calls) == 1 and public.quota[0]["requests"] == 1
    assert any("provider_" in w for w in public.warnings)


@pytest.mark.anyio
async def test_new_frozen_frames_and_missing_rubric_are_safe(repository, observation_factory, now):
    base, q, opt, _, ids = setup(repository, observation_factory, now)
    c = repository.connection
    defs = [
        CohortDefinition.model_validate_json(
            c.execute(
                "SELECT definition_json FROM cohort_definitions WHERE cohort_id=?", (cid,)
            ).fetchone()[0]
        )
        for cid in (base.run.cohort_id, base.run.video_cohort_id)
    ]
    profile = {"channel_frame": defs[0], "video_frame": defs[1], "measurement": base.run.options}
    initial = c.total_changes
    surface = PublicSurface(Settings(), history=repository)
    failed = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(mode="quick", advanced=profile)
    )
    assert failed.state == "insufficient_evidence" and c.total_changes == initial
    freeze = defs[1].known_at
    e = EligibilityRepository(repository)
    for vid in ids:
        for field, value, basis in (
            ("duration_seconds", 600, "official_metadata"),
            ("surface_format", "standard_vod_confirmed", "official_surface"),
            ("faceless", "faceless", "human_review"),
        ):
            e.append_claim(
                claim(
                    freeze,
                    field,
                    value,
                    basis,
                    subject=Subject(entity_kind="video", entity_id=vid),
                    complete_review=True,
                )
            )
    profile.update(
        {
            "rubric": opt.rubric,
            "review": {
                "review_ids": q.run.options.annotation_ids,
                "premise_ids": q.run.options.generated_candidate_ids,
            },
        }
    )
    result = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(mode="quick", advanced=profile)
    )
    assert result.research_id and result.data["coverage"]["candidate_channels"] == 3, result
    assert result.provenance["cohort_id"].startswith("public-channels-")
    replay = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(mode="quick", advanced=profile)
    )
    assert replay.research_id == result.research_id and replay.reused_run


@pytest.mark.anyio
async def test_watch_target_changes_do_not_mutate_identity(repository, now):
    surface = PublicSurface(Settings(), history=repository)
    created = await surface.dispatch(
        "youtube_competitor_watch",
        CompetitorWatchRequest(
            action="create",
            watch_id="stable",
            channel_ids=(channel(1),),
            profile={"desired_metrics": ["history"]},
        ),
    )
    updated = await surface.dispatch(
        "youtube_competitor_watch",
        CompetitorWatchRequest(
            action="update",
            watch_id="stable",
            channel_ids=(channel(2),),
            profile={"desired_metrics": ["history"]},
            expected_revision=1,
        ),
    )
    assert created.state == "configured" and updated.state == "invalid_input"
    incompatible = await surface.dispatch(
        "youtube_niche_watchlist", NicheWatchRequest(action="read", watch_id="stable")
    )
    assert incompatible.state == "not_found"
    read = await surface.dispatch(
        "youtube_competitor_watch", CompetitorWatchRequest(action="read", watch_id="stable")
    )
    assert read.data["subject"]["channel_ids"] == [channel(1)] and read.data["revision"] == 1


@pytest.mark.anyio
async def test_relative_outlier_weak_absolute_and_provider_score_are_separate(
    repository, observation_factory, now
):
    base, q, opt, _, ids = setup(
        repository, observation_factory, now, values=[[100] * 5 + [1000], [12000] * 6, [15000] * 6]
    )
    modified = AnalysisService(repository).analyze(
        base.run.cohort_id,
        base.run.options.model_copy(update={"candidate_id": ids[5], "baseline_cutoff": now}),
        video_cohort_id=base.run.video_cohort_id,
    )
    run = DecisionService(repository).analyze(
        opt.model_copy(update={"base_run_id": modified.run.run_id})
    )
    ingest(
        NexLevRepository(repository),
        "outlier-context",
        record(now, entity=ids[5], outlier_score=99),
    )
    result = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_niche_outliers", detail(run)
    )
    candidate = next(r for r in result.evidence if r["video_id"] == ids[5])
    assert (
        candidate["state"] == "relative_outlier_candidate"
        and not candidate["absolute_goal_attained"]
    )
    assert candidate["absolute_reach"] == 1000 and candidate["relative_lift_F1"] is not None
    assert result.data["provider_outlier_context"][0]["canonical_metric"] is False
    assert (
        result.data["provider_outlier_context"][0]["interpretation"]
        == "provider_derived_context_only"
    )
    assert dimensions(result)["F7"].state == "insufficient_history"


@pytest.mark.anyio
async def test_provider_history_only_is_auxiliary_and_no_history_backfill(
    repository, observation_factory, now
):
    from phase4_helpers import make_frame, point

    from youtube_niche_mcp.analysis.historical_models import HistoricalOptions, Window
    from youtube_niche_mcp.collectors.nexlev.models import HistoryPoint

    at = now - timedelta(days=11)
    vd, cd = make_frame(
        repository, observation_factory, now, "aux", [(1, video(1), at, [point(now, 999999)])], now
    )
    base = AnalysisService(repository).analyze(cd, options(now, first_k=None), video_cohort_id=vd)
    opt = DecisionOptions(
        cutoff=now,
        age_days=30,
        goal=10000,
        tolerance_seconds=0,
        base_run_id=base.run.run_id,
        rubric=DecisionRubric(version="synthetic", rules=()),
        sensitivity=SensitivityPlan(mode="deep", max_runs=48, declared_at=now),
    )
    rec = record(now, route="nexlev.daily_analytics", kind="channel", entity=channel(1)).model_copy(
        update={
            "history": (
                HistoryPoint(date=now - timedelta(days=2), views=100),
                HistoryPoint(date=now - timedelta(days=1), views=200),
            )
        }
    )
    ingest(NexLevRepository(repository), "aux-history", rec)
    request = ResearchRequest(
        research_id=base.run.run_id,
        mode="deep",
        advanced={
            "rubric": opt.rubric,
            "historical": HistoricalOptions(
                cutoff=now,
                age_days=30,
                tolerance_seconds=0,
                goal=10000,
                creator_group_version="synthetic",
                observation_window=Window(start=now - timedelta(days=3), end=now),
                provider_history_policy="separate_auxiliary",
            ),
        },
    )
    surface = PublicSurface(Settings(), history=repository)
    research = await surface.dispatch("youtube_niche_research", request)
    result = await surface.dispatch(
        "youtube_niche_history", DetailRequest(research_id=research.research_id)
    )
    assert result.state == "provider_history_only", dimensions(result)["F10"]
    assert (
        dimensions(result)["F10"].state == "provider_history_only"
        and dimensions(result)["F10"].value is None
    )
    assert dimensions(result)["F20"].value is None and dimensions(result)["F21"].value is None


@pytest.mark.anyio
async def test_declared_country_hidden_subscribers_sister_groups_and_expiry(repository, now):
    RetentionRepository(repository).record_permission(
        StoragePermission(
            source="youtube:channels.list",
            approval_reference="synthetic",
            verified_by="test",
            verified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=2),
            statistical_months=1,
        )
    )

    async def handler(request):
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": sid,
                        "snippet": {"title": "Synthetic", "country": "US"},
                        "statistics": {
                            "hiddenSubscriberCount": True,
                            "viewCount": "100",
                            "videoCount": "3",
                        },
                    }
                    for sid in (channel(1), channel(2))
                ]
            },
        )

    e = EligibilityRepository(repository)
    for sid in (channel(1), channel(2)):
        eid = e.append_claim(
            claim(
                now,
                "creator_relation",
                "shared",
                "public_disclosure",
                subject=Subject(entity_kind="channel", entity_id=sid),
            )
        )
        e.group_channel("shared", "shared", "creator", eid)
    surface = PublicSurface(
        Settings(youtube_api_key=SecretStr("test-key")),
        history=repository,
        youtube_transport=httpx.MockTransport(handler),
    )
    one = await surface.dispatch(
        "youtube_competitor_analyze",
        CompetitorRequest(
            channel_id=channel(1),
            acquisition={
                "refresh": True,
                "request_id": "hidden",
                "channel_ids": (channel(1), channel(2)),
            },
        ),
    )
    assert (
        one.data["current_public_statistics"]["subscriber_count"] is None
        and one.data["current_public_statistics"]["subscriber_hidden"]
    )
    assert one.data["declared_country"]["value"] == "US"
    both = await surface.dispatch(
        "youtube_competitor_compare", CompetitorCompareRequest(channel_ids=(channel(1), channel(2)))
    )
    assert both.evidence[0]["ownership"] == both.evidence[1]["ownership"]
    repository.clock = lambda: now + timedelta(days=1, seconds=1)
    expired = await surface.dispatch(
        "youtube_competitor_analyze", CompetitorRequest(channel_id=channel(1))
    )
    assert expired.data["declared_country"]["state"] == "unknown"
    assert expired.data["current_public_statistics"]["subscriber_count"] is None


@pytest.mark.anyio
async def test_factual_high_and_missing_reviews_are_visible(repository, observation_factory, now):
    base, q, opt, _, _ = setup(repository, observation_factory, now)
    svc = QualitativeService(repository)
    high = review(
        now,
        {
            "kind": "factual",
            "domain": "crime",
            "verification_burden": "high",
            "identifiable_entity": True,
            "allegation_verification_needed": True,
            "disputed_claims": True,
            "volatile": True,
            "correction_burden": "high",
        },
        "high-factual",
    )
    svc.annotate(high)
    newq = svc.analyze(
        q.run.cohort_id,
        q.run.options.model_copy(
            update={
                "annotation_ids": tuple(a for a in q.run.options.annotation_ids if a != "factual")
                + (high.annotation_id,)
            }
        ),
        video_cohort_id=q.run.video_cohort_id,
    )
    run = DecisionService(repository).analyze(
        opt.model_copy(update={"qualitative_run_ids": (newq.run.run_id,)})
    )
    surface = PublicSurface(Settings(), history=repository)
    result = await surface.dispatch("youtube_niche_risk", detail(run))
    assert (
        dimensions(result)["factual_editorial"].details["reviews"][0]["verification_burden"]
        == "high"
    )
    empty = DecisionService(repository).analyze(opt.model_copy(update={"qualitative_run_ids": ()}))
    missing = await surface.dispatch("youtube_niche_risk", detail(empty))
    assert {"rights_legal", "platform_policy", "factual_editorial"} <= set(
        missing.data["missing_dimensions"]
    )
    assert missing.confidence["critical_missing_evidence"]


@pytest.mark.anyio
async def test_demand_repeatability_and_shallow_inventory_are_explicit(
    repository, observation_factory, now
):
    base, q, opt, _, _ = setup(repository, observation_factory, now)
    run = DecisionService(repository).analyze(opt)
    surface = PublicSurface(Settings(), history=repository)
    demand = await surface.dispatch("youtube_niche_audience_demand", detail(run))
    assert (
        Decimal(dimensions(demand)["F3"].value) == 1
        and Decimal(dimensions(demand)["F8"].value) == 1
    )
    assert Decimal(dimensions(demand)["F9"].value) < Decimal("0.5")
    broad = await surface.dispatch("youtube_niche_sustainability", detail(run))
    assert Decimal(dimensions(broad)["F15"].value) == 1
    assert "F11" in broad.data["missing_dimensions"]
    shallow = QualitativeService(repository).analyze(
        q.run.cohort_id,
        q.run.options.model_copy(
            update={
                "annotation_ids": tuple(
                    a
                    for a in q.run.options.annotation_ids
                    if not a.startswith("premise-") or a in {"premise-0", "premise-1"}
                )
            }
        ),
        video_cohort_id=q.run.video_cohort_id,
    )
    changed = DecisionService(repository).analyze(
        opt.model_copy(update={"qualitative_run_ids": (shallow.run.run_id,)})
    )
    result = await surface.dispatch("youtube_niche_sustainability", detail(changed))
    assert Decimal(dimensions(result)["F15"].value) == Decimal(2) / 30
    assert result.confidence["history_maturity"]["immature"]


@pytest.mark.anyio
async def test_old_catalog_incremental_history_is_not_current_lifetime_count(
    repository, observation_factory, now
):
    from test_historical_catalog_posthit import catalog_fixture

    svc, vd, historical = catalog_fixture(repository, observation_factory, now)
    cid = "catalog-end-entrants"
    base = AnalysisService(repository).analyze(cid, options(now, first_k=None), video_cohort_id=vd)
    h = svc.analyze(cid, historical, video_cohort_id=vd)
    opt = DecisionOptions(
        cutoff=now,
        age_days=30,
        tolerance_seconds=0,
        goal=10000,
        base_run_id=base.run.run_id,
        historical_run_ids=(h.run.run_id,),
        rubric=DecisionRubric(version="synthetic", rules=()),
        sensitivity=SensitivityPlan(mode="quick", max_runs=8, declared_at=now),
    )
    run = DecisionService(repository).analyze(opt)
    result = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_niche_history", detail(run)
    )
    f = dimensions(result)["F13"]
    assert f.state == "partial_coverage" and Decimal(f.value) == Decimal("0.3"), f
    assert Decimal(f.numerator) == 30000 and Decimal(f.denominator) == 100000


@pytest.mark.anyio
async def test_creator_override_preserves_retained_pilot_and_case(
    repository, observation_factory, now
):
    from phase5_helpers import pilot

    base, q, opt, _, _ = setup(repository, observation_factory, now)
    q2 = QualitativeService(repository).analyze(
        q.run.cohort_id,
        q.run.options.model_copy(update={"pilot": pilot(now)}),
        video_cohort_id=q.run.video_cohort_id,
    )
    run = DecisionService(repository).analyze(
        opt.model_copy(update={"qualitative_run_ids": (q2.run.run_id,)})
    )
    result = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_niche_research",
        ResearchRequest(research_id=run.run.run_id, creator_profile=capacity(now, hours=1)),
    )
    assert result.research_id, result
    assert dimensions(result)["F23"].value is not None
    assert result.data["creator_fit"]["cases"]


@pytest.mark.anyio
async def test_expired_provider_replay_does_not_charge_unpersistable_identity(repository, now):
    RetentionRepository(repository).record_permission(
        StoragePermission(
            source="nexlev.similar_channels",
            approval_reference="synthetic",
            verified_by="test",
            verified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=5),
            statistical_months=1,
        )
    )
    calls = []

    async def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"data": [{"channelId": channel(2), "title": "Synthetic"}]})

    surface = PublicSurface(
        Settings(nexlev_api_key=SecretStr("test-nexlev")),
        history=repository,
        nexlev_transport=httpx.MockTransport(handler),
    )
    request = CompetitorRequest(
        channel_id=channel(1),
        acquisition={
            "refresh": True,
            "request_id": "similarity",
            "provider_policy": "prefer_nexlev",
            "similar_channel": channel(1),
        },
    )
    first = await surface.dispatch("youtube_competitor_analyze", request)
    assert len(calls) == 1 and first.quota[0]["requests"] == 1, first
    repository.clock = lambda: now + timedelta(days=2)
    replay = await surface.dispatch("youtube_competitor_analyze", request)
    assert len(calls) == 1 and replay.quota[0]["requests"] == 0, replay
    assert replay.quota[0]["quota_state"] == "expired_identity_requires_new_request"


@pytest.mark.anyio
async def test_maximum_comparison_preserves_all_rows_and_confidence(
    repository, observation_factory, now
):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    service = DecisionService(repository)
    ids = tuple(
        service.analyze(
            opt.model_copy(
                update={"f17": sort_config().model_copy(update={"version": f"maximum-{i}"})}
            )
        ).run.run_id
        for i in range(10)
    )
    result = await PublicSurface(Settings(), history=repository).dispatch(
        "youtube_niche_compare", CompareRequest(research_ids=ids)
    )
    assert result.state == "available" and len(result.evidence) == 10, result
    assert {r["research_id"] for r in result.evidence} == set(ids)
    assert all(r["confidence"]["F18"] for r in result.evidence)
    assert len(result.model_dump_json().encode()) <= 120000 and result.data["winner"] is None
