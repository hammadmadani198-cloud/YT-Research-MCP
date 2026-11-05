"""Actual retained-service fixtures exercised through the public Phase 7 surface."""

import json
import os
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import anyio
import httpx
import pytest
from jsonschema import Draft202012Validator
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from phase3_helpers import channel
from phase6_helpers import result as internal_result
from phase6_helpers import setup
from pydantic import SecretStr

from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import migrate
from youtube_niche_mcp.db.schema import MIGRATIONS
from youtube_niche_mcp.db.status import integrity
from youtube_niche_mcp.decision.models import SortConfig, SortDimension
from youtube_niche_mcp.decision.service import DecisionService
from youtube_niche_mcp.history.retention import RetentionRepository, StoragePermission
from youtube_niche_mcp.qualitative.models import CreatorCapacity
from youtube_niche_mcp.server import create_server
from youtube_niche_mcp.services.catalog import PLANNED_TOOLS
from youtube_niche_mcp.tools.research import ResearchEngine
from youtube_niche_mcp.tools.runtime import PublicSurface
from youtube_niche_mcp.tools.schemas import (
    INPUTS,
    CompareRequest,
    CompetitorCompareRequest,
    CompetitorRequest,
    CompetitorWatchRequest,
    DetailRequest,
    DiscoverRequest,
    NicheWatchRequest,
    PublicResult,
    ResearchRequest,
    WatchProfile,
)
from youtube_niche_mcp.tools.serialization import project


@pytest.fixture
def researched(repository, observation_factory, now):
    base, qualitative, options, _, ids = setup(repository, observation_factory, now)
    decision = DecisionService(repository).analyze(options)
    return base, qualitative, options, decision, ids


@pytest.fixture
def surface(repository):
    return PublicSurface(Settings(), history=repository)


def sort_config():
    return SortConfig(
        version="synthetic-explicit",
        dimensions=(
            SortDimension(
                formula_id="F3",
                weight=1,
                low=0,
                high=1,
                direction="higher",
                benchmark_reference="Synthetic caller reference; no calibrated predictive claim",
            ),
        ),
    )


@pytest.mark.anyio
async def test_exact_names_schemas_descriptions_and_result_validation():
    async with Client(create_server(), raise_exceptions=True) as client:
        tools = (await client.list_tools()).tools
        assert sorted(t.name for t in tools) == sorted(PLANNED_TOOLS) == sorted(INPUTS)
        assert len(tools) == 15
        for tool in tools:
            assert len(tool.description) > 80
            Draft202012Validator.check_schema(tool.input_schema)
            Draft202012Validator.check_schema(tool.output_schema)
            assert tool.input_schema["required"] == ["request"]
            assert "request" in tool.input_schema["properties"]
            result = await client.call_tool(tool.name, {"request": {}})
            body = result.structured_content
            PublicResult.model_validate(body)
            Draft202012Validator(tool.output_schema).validate(body)
            assert body["state"] == "invalid_input"


@pytest.mark.anyio
@pytest.mark.parametrize("name", PLANNED_TOOLS)
async def test_validation_errors_never_echo_values(name):
    server = create_server(Settings(youtube_api_key=SecretStr("credential-marker")))
    for arguments in (
        {"request": {"secret": "credential-marker"}},
        {"request": {"bad": "C:\\private\\file"}},
        {"request": "token-value"},
        {"wrong": "SELECT * FROM secrets"},
    ):
        result = await server.call_tool(name, arguments)
        assert result.structured_content["state"] == "invalid_input"
        encoded = result.model_dump_json()
        assert all(
            v not in encoded
            for v in ("credential-marker", "C:\\private", "SELECT", "token-value", "Traceback")
        )


@pytest.mark.anyio
async def test_research_replay_query_chaining_and_zero_http(surface, researched, repository):
    _, _, _, decision, _ = researched
    initial = repository.connection.total_changes
    a = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(research_id=decision.run.run_id)
    )
    b = await surface.dispatch("youtube_niche_research", ResearchRequest(query="Synthetic"))
    assert a.research_id == b.research_id == decision.run.run_id
    assert a.reused_run and b.reused_run and a.state == "history_immature"
    assert a.confidence["level"] == "low" and a.confidence["F18"]
    assert "sorting_only_F17" not in a.data
    assert repository.connection.total_changes == initial
    assert not repository.connection.execute("SELECT 1 FROM quota_requests").fetchone()
    assert all(q["requests"] == 0 for q in a.quota)
    discovered = await surface.dispatch(
        "youtube_niche_discover", DiscoverRequest(query="Synthetic")
    )
    assert discovered.state == "available" and discovered.data["ranking"] == "none"
    assert discovered.evidence[0]["boundary_ids"] == [a.boundary["boundary_id"]]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mode,review,sensitivity", [("quick", 25, 8), ("standard", 100, 24), ("deep", 500, 48)]
)
async def test_modes_orchestrate_canonical_services(surface, researched, mode, review, sensitivity):
    base, qualitative, options, _, _ = researched
    request = ResearchRequest(
        research_id=base.run.run_id,
        mode=mode,
        advanced={
            "rubric": options.rubric,
            "review": {
                "review_ids": qualitative.run.options.annotation_ids,
                "premise_ids": qualitative.run.options.generated_candidate_ids,
            },
        },
    )
    a = await surface.dispatch("youtube_niche_research", request)
    assert a.research_id and a.data["mode"] == mode, a
    assert a.data["budget"]["review"] == review
    assert a.data["budget"]["sensitivity"] == sensitivity
    assert len(a.metrics) >= 25
    assert a.confidence["F18"] and a.provenance["analysis_run_ids"]
    b = await surface.dispatch("youtube_niche_research", request)
    assert b.research_id == a.research_id and b.reused_run


@pytest.mark.anyio
async def test_explicit_sorting_and_creator_fit(surface, researched, now):
    _, _, _, decision, _ = researched
    creator = CreatorCapacity(
        profile_id="synthetic",
        declared_at=now,
        expires_at=now + timedelta(days=5),
        hours_per_week=1,
        monthly_cash=1000,
        currency="USD",
        releases_per_week=1,
    )
    a = await surface.dispatch(
        "youtube_niche_research",
        ResearchRequest(
            research_id=decision.run.run_id, creator_profile=creator, sorting=sort_config()
        ),
    )
    assert a.research_id and a.data["sorting_only_F17"]["sorting_only"]
    assert (
        a.data["creator_fit"]["cases"][0]["compatibility"]["state"]
        == "incompatible_declared_constraints"
    )
    assert a.data["recommendation_state"] == internal_result(decision, "decision").state


@pytest.mark.anyio
@pytest.mark.parametrize(
    "case,changes,expected",
    [
        (
            "weak",
            {"values": [[12000, 100, 100, 100, 100, 100], [100] * 6, [100] * 6]},
            "weak_under_goal",
        ),
        ("high-rights", {"rights": "high"}, "high_rights_or_policy_dependency"),
        ("high-production", {"hours": 100}, "high_execution_burden"),
        ("immature", {}, "history_immature"),
        (
            "incomplete",
            {"complete": False, "values": [[100000, None, None, None, None, None]]},
            "insufficient_evidence",
        ),
    ],
)
async def test_frozen_decision_states_through_tool(
    repository, observation_factory, now, case, changes, expected
):
    _, _, options, _, _ = setup(repository, observation_factory, now, **changes)
    if case == "weak":
        options = options.model_copy(
            update={"rubric": options.rubric.model_copy(update={"required_history": ()})}
        )
    decision = DecisionService(repository).analyze(options)
    surface = PublicSurface(Settings(), history=repository)
    public = await surface.dispatch(
        "youtube_niche_research", ResearchRequest(research_id=decision.run.run_id)
    )
    assert public.state == expected and public.confidence["F18"], case
    assert public.state == internal_result(decision, "decision").state


@pytest.mark.anyio
@pytest.mark.parametrize(
    "focus",
    [
        "outliers",
        "content_gaps",
        "packaging",
        "audience_demand",
        "sustainability",
        "risk",
        "geo_language",
        "history",
    ],
)
async def test_focused_views_have_confidence_and_no_private_inference(surface, researched, focus):
    decision = researched[3]
    public = await surface.dispatch(
        "youtube_niche_" + focus, DetailRequest(research_id=decision.run.run_id)
    )
    assert public.research_id == decision.run.run_id and public.confidence["F18"], public
    serialized = public.model_dump_json()
    assert len(serialized.encode()) <= 120000
    assert not any(
        field in serialized
        for field in (
            '"transcript":',
            '"manifest":',
            '"db_path":',
            '"retention":',
            '"watch_time":',
            '"returning_viewers":',
        )
    )
    if focus == "outliers":
        assert public.evidence[0]["state"] == "candidate_hit"
        assert (
            "absolute_reach" in public.evidence[0]
            and "ordinary_channel_floor" in public.evidence[0]
        )
    if focus == "risk":
        assert set(public.data["risk_dimensions"]) == {
            "rights_reuse",
            "platform_policy",
            "factual_editorial",
            "production_dependency",
            "capacity",
            "policy_freshness",
        }


@pytest.mark.anyio
async def test_compare_compatible_no_winner_and_incompatible_modes(surface, researched, repository):
    _, _, options, decision, _ = researched
    other = DecisionService(repository).analyze(options.model_copy(update={"f17": sort_config()}))
    result = await surface.dispatch(
        "youtube_niche_compare",
        CompareRequest(research_ids=(decision.run.run_id, other.run.run_id)),
    )
    assert result.state == "available" and result.data["winner"] is None
    assert result.evidence[0]["sorting_only_F17"] is None
    sorted_result = await surface.dispatch(
        "youtube_niche_compare",
        CompareRequest(research_ids=(decision.run.run_id, other.run.run_id), sorting=sort_config()),
    )
    assert sorted_result.evidence[0]["sorting_only_F17"]["sorting_only"]
    incompatible = DecisionService(repository).analyze(
        options.model_copy(
            update={
                "sensitivity": options.sensitivity.model_copy(
                    update={"mode": "quick", "max_runs": 8}
                )
            }
        )
    )
    failed = await surface.dispatch(
        "youtube_niche_compare",
        CompareRequest(research_ids=(decision.run.run_id, incompatible.run.run_id)),
    )
    assert failed.state == "incompatible_runs"


@pytest.mark.anyio
async def test_competitor_scope_and_compare(surface, researched):
    decision = researched[3]
    a = await surface.dispatch(
        "youtube_competitor_analyze",
        CompetitorRequest(channel_id=channel(1), research_id=decision.run.run_id),
    )
    assert a.state == "available" and Decimal(a.data["ordinary_floor"]["value"]) == 12000
    assert a.data["production_model"]["state"] == "channel_specific_review_unavailable"
    assert a.data["niche_context"]["research_id"] == decision.run.run_id
    assert (
        a.confidence["F18"] is None
    )  # niche confidence cannot be passed off as channel confidence
    b = await surface.dispatch(
        "youtube_competitor_compare",
        CompetitorCompareRequest(
            channel_ids=(channel(1), channel(2)), research_id=decision.run.run_id
        ),
    )
    assert b.state == "available" and len(b.evidence) == 2 and b.data["winner"] is None


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["niche", "competitor"])
async def test_watch_lifecycle_and_immutable_research(surface, researched, repository, kind):
    name = "youtube_niche_watchlist" if kind == "niche" else "youtube_competitor_watch"
    model = NicheWatchRequest if kind == "niche" else CompetitorWatchRequest
    subjects = (
        {"boundary_id": "boundary-v1", "target_channels": (channel(1),)}
        if kind == "niche"
        else {"channel_ids": (channel(1), channel(2))}
    )
    before = [
        tuple(r)
        for r in repository.connection.execute("SELECT * FROM analysis_runs ORDER BY run_id")
    ]
    profile = WatchProfile(
        desired_metrics=("history", "public_statistics"), cadence_days=7, history_required=True
    )
    created = await surface.dispatch(
        name, model(action="create", watch_id=kind + "-watch", profile=profile, **subjects)
    )
    assert created.state == "configured" and created.data["revision"] == 1
    assert created.data["last_checked_at"] is None and created.data["scheduler"] == "absent"
    replay = await surface.dispatch(
        name, model(action="create", watch_id=kind + "-watch", profile=profile, **subjects)
    )
    assert replay.data == created.data
    read = await surface.dispatch(name, model(action="read", watch_id=kind + "-watch"))
    assert read.data == created.data
    updated = await surface.dispatch(
        name,
        model(
            action="update",
            watch_id=kind + "-watch",
            profile=profile.model_copy(update={"cadence_days": 14}),
            expected_revision=1,
        ),
    )
    assert updated.data["revision"] == 2
    stale = await surface.dispatch(
        name, model(action="disable", watch_id=kind + "-watch", expected_revision=1)
    )
    assert stale.state == "revision_conflict"
    disabled = await surface.dispatch(
        name, model(action="disable", watch_id=kind + "-watch", expected_revision=2)
    )
    assert disabled.state == "disabled" and disabled.data["revision"] == 3
    missing = await surface.dispatch(name, model(action="read", watch_id="nonexistent"))
    assert missing.state == "not_found"
    assert before == [
        tuple(r)
        for r in repository.connection.execute("SELECT * FROM analysis_runs ORDER BY run_id")
    ]


@pytest.mark.anyio
async def test_pagination_context_expiry_and_owner(surface, researched, repository, now):
    request = DetailRequest(research_id=researched[3].run.run_id, limit=2)
    a = await surface.dispatch("youtube_niche_outliers", request)
    b = await surface.dispatch(
        "youtube_niche_outliers", request.model_copy(update={"cursor": a.next_cursor})
    )
    assert a.next_cursor and {r["video_id"] for r in a.evidence}.isdisjoint(
        r["video_id"] for r in b.evidence
    )
    c = await surface.dispatch(
        "youtube_niche_geo_language", request.model_copy(update={"cursor": a.next_cursor})
    )
    assert c.state == "invalid_input"
    await surface.dispatch(
        "youtube_competitor_watch",
        CompetitorWatchRequest(
            action="create",
            watch_id="expiring",
            channel_ids=(channel(1),),
            profile={"desired_metrics": ["history"]},
            expires_at=now + timedelta(seconds=1),
        ),
    )
    other = await surface.dispatch(
        "youtube_competitor_watch",
        CompetitorWatchRequest(action="read", watch_id="expiring", owner_context="someone-else"),
    )
    assert other.state == "not_found"
    repository.clock = lambda: now + timedelta(seconds=2)
    expired = await surface.dispatch(
        "youtube_competitor_watch", CompetitorWatchRequest(action="read", watch_id="expiring")
    )
    assert expired.state == "not_found"


@pytest.mark.parametrize("version", range(7))
def test_all_prior_schemas_to_v7(tmp_path, version):
    with connect(tmp_path / "upgrade.sqlite3") as c:
        if version:
            migrate(c, MIGRATIONS[:version])
        assert migrate(c) == list(range(version + 1, 8))
        assert migrate(c) == [] and integrity(c)["ok"]
        assert len(c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()) == 36


@pytest.mark.anyio
async def test_provider_absent_permission_and_no_network(surface, researched, repository, now):
    request = ResearchRequest(
        research_id=researched[3].run.run_id,
        acquisition={"refresh": True, "request_id": "explicit", "video_ids": [researched[4][0]]},
    )
    absent = await surface.dispatch("youtube_niche_research", request)
    assert absent.state == "provider_not_configured"
    configured = PublicSurface(Settings(youtube_api_key=SecretStr("test-key")), history=repository)
    # The synthetic fixture permits videos.list.
    # Channel metadata permission is absent; HTTP must not start.
    request = request.model_copy(
        update={
            "acquisition": request.acquisition.model_copy(update={"channel_ids": (channel(1),)})
        }
    )
    gated = await configured.dispatch("youtube_niche_research", request)
    assert gated.state == "permission_required"
    assert not repository.connection.execute("SELECT 1 FROM quota_requests").fetchone()


@pytest.mark.anyio
async def test_explicit_mock_refresh_quota_and_replay(repository, now, observation_factory):
    calls = []

    async def handler(request):
        calls.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": channel(1),
                        "snippet": {"title": "Synthetic", "country": "US"},
                        "statistics": {
                            "subscriberCount": "100",
                            "viewCount": "200",
                            "videoCount": "3",
                        },
                    }
                ]
            },
        )

    RetentionRepository(repository).record_permission(
        StoragePermission(
            source="youtube:channels.list",
            approval_reference="synthetic",
            verified_by="test",
            verified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=1),
            statistical_months=1,
        )
    )
    surface = PublicSurface(
        Settings(youtube_api_key=SecretStr("test-key")),
        history=repository,
        youtube_transport=httpx.MockTransport(handler),
    )
    request = CompetitorRequest(
        channel_id=channel(1),
        acquisition={"refresh": True, "request_id": "bounded-refresh", "channel_ids": [channel(1)]},
    )
    a = await surface.dispatch("youtube_competitor_analyze", request)
    assert (
        a.state == "available"
        and a.quota[0]["requests"] == 1
        and a.quota[0]["actual_charged_cost"] is None
    )
    assert a.data["current_public_statistics"]["subscriber_count"] == 100
    assert a.data["declared_country"]["value"] == "US"
    assert "not audience" in a.data["declared_country"]["scope"]
    b = await surface.dispatch("youtube_competitor_analyze", request)
    assert b.state == "available" and len(calls) == 1 and b.quota[0]["requests"] == 0
    assert "test-key" not in b.model_dump_json()


@pytest.mark.anyio
async def test_missing_db_and_unexpected_exception_are_safe(tmp_path, monkeypatch):
    missing = tmp_path / "missing" / "research.sqlite3"
    surface = PublicSurface(Settings(db_path=missing))
    result = await surface.dispatch("youtube_niche_discover", DiscoverRequest(query="anything"))
    assert result.state == "insufficient_evidence" and not missing.parent.exists()

    def explode(*args):
        raise RuntimeError("private-path and SQL diagnostic marker")

    monkeypatch.setattr(ResearchEngine, "boundaries", explode)
    with connect(tmp_path / "existing.sqlite3") as c:
        migrate(c)
    public = await PublicSurface(Settings(db_path=tmp_path / "existing.sqlite3")).dispatch(
        "youtube_niche_discover", DiscoverRequest(query="anything")
    )
    assert public.state == "internal_error" and "secret" not in public.model_dump_json()


@pytest.mark.stdio
@pytest.mark.anyio
async def test_real_stdio_representative_calls(researched, repository, tmp_path):
    base, _, options, decision, _ = researched
    other = DecisionService(repository).analyze(options.model_copy(update={"f17": sort_config()}))
    repository.connection.commit()
    database = repository.connection.execute("PRAGMA database_list").fetchone()[2]
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "youtube_niche_mcp.server"],
        cwd=tmp_path,
        env={**os.environ, "YTNMCP_DB_PATH": database},
    )
    cases = [
        ("youtube_niche_research", {"research_id": decision.run.run_id}),
        ("youtube_niche_compare", {"research_ids": [decision.run.run_id, other.run.run_id]}),
        (
            "youtube_competitor_analyze",
            {"channel_id": channel(1), "research_id": decision.run.run_id},
        ),
        (
            "youtube_competitor_watch",
            {
                "action": "create",
                "watch_id": "stdio-watch",
                "channel_ids": [channel(1)],
                "profile": {"desired_metrics": ["public_statistics"]},
            },
        ),
    ]
    with anyio.fail_after(60):
        async with Client(params, read_timeout_seconds=30) as client:
            assert sorted(t.name for t in (await client.list_tools()).tools) == sorted(
                PLANNED_TOOLS
            )
            for name, request in cases:
                response = await client.call_tool(name, {"request": request})
                body = PublicResult.model_validate(response.structured_content)
                # This legacy synthetic cohort has October 2026 retention windows.
                # A real stdio subprocess uses the actual clock; once evidence expires,
                # permission_required is the correct safe outcome, not a regression.
                assert body.state in {
                    "history_immature", "available", "configured", "permission_required"
                }, (name, body)
                assert all(q["requests"] == 0 for q in body.quota)


def test_projection_withholds_sensitive_or_large_payload():
    data = project(
        {
            "transcript": "full raw text",
            "manifest": {"raw": "secret"},
            "safe": "C:\\private\\path",
            "large": list(range(1000)),
            "api_key": "sensitive",
        }
    )
    assert "transcript" not in data and "manifest" not in data and "api_key" not in data
    assert data["safe"] == "[withheld]" and data["large"][-1]["omitted_items"] == 980


@pytest.mark.anyio
async def test_documented_contract_matches_executable_models():
    schemas = json.loads(
        (Path(__file__).resolve().parent.parent / "docs/phase-7-schemas.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(schemas) == set(INPUTS)
    async with Client(create_server()) as client:
        for tool in (await client.list_tools()).tools:
            documented = schemas[tool.name]["inputSchema"]
            actual = tool.input_schema
            assert {k: v for k, v in documented.items() if k != "title"} == {
                k: v for k, v in actual.items() if k != "title"
            }
            assert schemas[tool.name]["outputSchema"] == tool.output_schema
