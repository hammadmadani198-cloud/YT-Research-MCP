import json
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from youtube_niche_mcp.collectors.nexlev.client import (
    NexLevClient,
    NexLevError,
    ProviderQuotaLedger,
)
from youtube_niche_mcp.collectors.nexlev.contracts import (
    ENDPOINTS,
    CapabilityState,
    capability_report,
)
from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository
from youtube_niche_mcp.config import ConfigurationError, Settings
from youtube_niche_mcp.server import server_status

CHANNEL = "UC" + "a" * 22
VIDEO = "ZP7jTDAHryQ"


def settings(**kwargs):
    return Settings(
        nexlev_api_key=SecretStr("nexlev-fixture-secret"), api_retry_delay_seconds=0, **kwargs
    )


def test_secret_configuration_and_offline_status(tmp_path):
    s = Settings.from_env(
        {"NEXLEV_API_KEY": "nexlev-fixture-secret", "YTNMCP_DB_PATH": str(tmp_path / "absent/db")}
    )
    assert "nexlev-fixture-secret" not in repr(s) + s.model_dump_json() + json.dumps(
        s.safe_summary()
    )
    status = server_status(s)
    assert (
        status.phase == 8
        and len(status.planned_tools) == 15
        and len(status.implemented_tools) == 15
    )
    assert not s.db_path.parent.exists()
    states = {c["capability"]: c["state"] for c in status.nexlev_capabilities}
    assert states["transcripts"] == "available"
    assert states["semantic_niche_search"] == "orchestrator_only"
    with pytest.raises(ConfigurationError) as e:
        Settings.from_env({"YTNMCP_NEXLEV_TIMEOUT_SECONDS": "nexlev-fixture-secret"})
    assert "nexlev-fixture-secret" not in str(e.value)


@pytest.mark.anyio
async def test_no_key_no_request_no_quota(now):
    client = NexLevClient(Settings(), clock=lambda: now)
    try:
        with pytest.raises(NexLevError) as error:
            await client.request("channel_about", {"id": CHANNEL})
        assert error.value.state == CapabilityState.NOT_CONFIGURED
        assert client.quota.entries == []
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "status,state,attempts",
    [
        (401, "not_configured", 1),
        (403, "plan_restricted", 1),
        (429, "quota_limited", 1),
        (503, "temporarily_unavailable", 3),
        (404, "unsupported", 1),
    ],
)
@pytest.mark.anyio
async def test_safe_failures_and_capability_overrides(now, status, state, attempts):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "nexlev-fixture-secret"})

    client = NexLevClient(settings(), clock=lambda: now, transport=httpx.MockTransport(handle))
    try:
        with pytest.raises(NexLevError) as error:
            await client.request("channel_about", {"id": CHANNEL})
        assert error.value.state.value == state
        assert "nexlev-fixture-secret" not in str(error.value)
        assert len(calls) == attempts
        assert all("nexlev-fixture-secret" not in str(r.url) for r in calls)
        assert all(r.headers["Authorization"] == "Bearer nexlev-fixture-secret" for r in calls)
        assert client.quota.totals()["known_charged_cost"] == 0
        assert (
            next(c for c in client.capabilities() if c["capability"] == "channel_about")["state"]
            == state
        )
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_transport_failure_charge_unknown_and_success_retry(now):
    count = 0

    def handle(request):
        nonlocal count
        count += 1
        if count == 1:
            raise httpx.ReadTimeout("nexlev-fixture-secret", request=request)
        return httpx.Response(200, json={"channelId": CHANNEL})

    client = NexLevClient(settings(), clock=lambda: now, transport=httpx.MockTransport(handle))
    try:
        await client.request("channel_about", {"id": CHANNEL})
        assert client.quota.totals()["unknown_charge_requests"] == 1
        assert client.quota.totals()["known_charged_cost"] == 1
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_post_not_retried_and_private_routes_rejected(now):
    calls = []
    client = NexLevClient(
        settings(),
        clock=lambda: now,
        transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(503)),
    )
    try:
        with pytest.raises(NexLevError):
            await client.request("similar_channels", {"channelId": CHANNEL, "level": 4})
        assert len(calls) == 1 and client.quota.entries[0].documented_cost == 60
        with pytest.raises(NexLevError):
            await client.request("niche_finder.semantic", {"query": "industrial"})
        with pytest.raises(ValueError):
            await client.request("similar_thumbnails", {"text": "space"})
        with pytest.raises(ValueError):
            await client.request("transcript", {"videoId": VIDEO, "lang": "en"})
        assert len(calls) == 1
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_pagination_bounded_repeat_and_token_not_a_credential(now):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"continuation": "pagination-value", "data": []})

    client = NexLevClient(settings(), clock=lambda: now, transport=httpx.MockTransport(handle))
    try:
        assert (
            len([p async for p in client.pages("channel_videos", {"id": CHANNEL}, max_pages=1)])
            == 1
        )
        with pytest.raises(NexLevError):
            _ = [p async for p in client.pages("channel_videos", {"id": CHANNEL}, max_pages=5)]
        assert len(calls) == 3 and calls[-1].url.params["token"] == "pagination-value"
    finally:
        await client.aclose()


@pytest.mark.parametrize("final", ["completed", "failed", "partial", "unavailable", "pending"])
@pytest.mark.anyio
async def test_async_jobs_persist_and_stop(repository, now, final):
    repo = NexLevRepository(repository)
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            200,
            json=[{"job_id": "fixture-job", "cached": False}]
            if request.url.path.endswith("create")
            else {"status": final, "cached": True},
        )

    ledger = ProviderQuotaLedger(sink=repo.record_quota)
    client = NexLevClient(
        settings(),
        clock=lambda: now,
        transport=httpx.MockTransport(handle),
        quota=ledger,
        event_sink=repo.record_job_event,
    )
    try:
        result = await client.analysis_job(CHANNEL, max_polls=2, poll_seconds=0)
        assert result["state"] == ("timeout" if final == "pending" else final)
        assert len(calls) == (3 if final == "pending" else 2)
        assert (
            repository.connection.execute("SELECT COUNT(*) FROM provider_runs").fetchone()[0] >= 2
        )
        assert repository.connection.execute(
            "SELECT COUNT(*) FROM provider_quota_details"
        ).fetchone()[0] == len(calls)
        assert ledger.totals()["known_charged_cost"] == 20
    finally:
        await client.aclose()


def test_hourly_minute_quota_guard_and_no_invented_balance(now):
    ledger = ProviderQuotaLedger()
    for _ in range(20):
        ledger.record_response("youtube_search", now, 200, {}, {})
    with pytest.raises(NexLevError) as e:
        ledger.check_limit("youtube_search", now)
    assert e.value.state == CapabilityState.QUOTA
    ledger.check_limit("youtube_search", now + timedelta(seconds=61))
    assert ledger.totals()["account_balance"] is None
    assert {c["state"] for c in capability_report(False)} >= {
        "orchestrator_only",
        "unsupported",
        "owner_authorization_required",
    }
    assert len(ENDPOINTS) == 17
