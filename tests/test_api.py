import copy
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from youtube_niche_mcp.api.client import APIError, EntityResult, Page, YouTubeClient
from youtube_niche_mcp.api.contracts import ENDPOINTS, QuotaContract
from youtube_niche_mcp.api.quota import QuotaLedger
from youtube_niche_mcp.collectors.normalize import normalize, regime
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.domain.foundation import Outcome
from youtube_niche_mcp.domain.states import EvidenceState, Precision


def configured(**kwargs):
    return Settings(
        youtube_api_key=SecretStr("fixture-secret"), api_retry_delay_seconds=0, **kwargs
    )


@pytest.mark.anyio
async def test_hydrate_missing_ids_and_no_secret_url(api_fixture, now, caplog):
    requests = []

    def handle(request):
        requests.append(request)
        assert request.headers["X-Goog-Api-Key"] == "fixture-secret"
        assert "fixture-secret" not in str(request.url)
        assert "maxResults" not in request.url.params
        return httpx.Response(200, json={"items": [api_fixture["video"]]})

    async with YouTubeClient(
        configured(), transport=httpx.MockTransport(handle), clock=lambda: now
    ) as client:
        rows = await client.hydrate("video", ["aaaaaaaaaaa", "bbbbbbbbbbb", "aaaaaaaaaaa"])
        assert [row.outcome for row in rows] == [Outcome.AVAILABLE, Outcome.API_MISSING]
        missing = normalize(rows[1], "video", "missing-capture")
        assert missing.metrics == {}
        assert missing.outcome.evidence_state == EvidenceState.NOT_PUBLICLY_AVAILABLE
        assert len(requests) == len(client.ledger.entries) == 1
    assert "fixture-secret" not in caplog.text + repr(rows)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "status,reason,outcome,attempts",
    [
        (503, "backendError", Outcome.TRANSIENT_ERROR, 3),
        (429, "http_error", Outcome.TRANSIENT_ERROR, 3),
        (403, "rateLimitExceeded", Outcome.TRANSIENT_ERROR, 3),
        (403, "quotaExceeded", Outcome.QUOTA_LIMITED, 1),
        (403, "commentsDisabled", Outcome.UNAVAILABLE, 1),
        (400, "invalidParameter", Outcome.UNAVAILABLE, 1),
        (404, "videoNotFound", Outcome.DELETED_OR_PRIVATE_UNKNOWN, 1),
        (302, "http_error", Outcome.UNAVAILABLE, 1),
    ],
)
async def test_retry_rules_and_sanitized_errors(status, reason, outcome, attempts, now):
    def handle(request):
        return httpx.Response(
            status,
            json={
                "error": {
                    "errors": [{"reason": reason}],
                    "message": "fixture-secret",
                    "url": "https://example.test/?key=fixture-secret",
                }
            },
            headers={"Location": "https://example.test/"},
        )

    async with YouTubeClient(
        configured(), transport=httpx.MockTransport(handle), clock=lambda: now
    ) as client:
        with pytest.raises(APIError) as caught:
            await client.request("videos.list", {"part": "statistics", "id": "aaaaaaaaaaa"})
        assert caught.value.outcome == outcome
        assert caught.value.http_status == status
        assert len(client.ledger.entries) == attempts
        assert "fixture-secret" not in str(caught.value) + repr(vars(caught.value))


@pytest.mark.anyio
async def test_retry_success_and_transport_timeout(now):
    calls, delays = [], []

    def handle(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("secret in raw transport error", request=request)
        return httpx.Response(200, json={"items": []})

    async def sleep(seconds):
        delays.append(seconds)

    async with YouTubeClient(
        configured(), transport=httpx.MockTransport(handle), clock=lambda: now, sleep=sleep
    ) as client:
        page = await client.request("videos.list", {"part": "statistics", "id": "aaaaaaaaaaa"})
        assert page.outcome == Outcome.AVAILABLE
        assert len(calls) == 2
        assert delays == [0]
        assert client.ledger.totals() == {"general": 2}


@pytest.mark.anyio
async def test_no_key_no_network_or_quota():
    async with YouTubeClient(Settings()) as client:
        with pytest.raises(APIError, match="api_key_absent"):
            await client.request("videos.list", {"part": "statistics", "id": "aaaaaaaaaaa"})
        assert client.ledger.entries == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"items": "invalid"},
        {"items": [], "echo": "fixture-secret"},
        {"items": [], "access_token": "arbitrary"},
    ],
)
async def test_malformed_or_secret_response_not_returned(payload):
    async with YouTubeClient(
        configured(),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    ) as client:
        with pytest.raises(APIError, match="malformed_response"):
            await client.request("videos.list", {"part": "statistics", "id": "aaaaaaaaaaa"})


@pytest.mark.anyio
async def test_public_only_parameter_and_part_guard():
    async with YouTubeClient(configured()) as client:
        for endpoint, params in [
            ("captions.download", {"part": "snippet"}),
            ("channels.list", {"part": "snippet", "mine": True}),
            ("videos.list", {"part": "fileDetails", "id": "aaaaaaaaaaa"}),
            ("search.list", {"part": "snippet", "maxResults": 51}),
            ("videos.list", {"part": "snippet", "key": "fixture-secret"}),
        ]:
            with pytest.raises(ValueError):
                await client.request(endpoint, params)
        assert not client.ledger.entries


@pytest.mark.anyio
async def test_batch_stats_opt_in_failures_upload_clock(api_fixture, now):
    async with YouTubeClient(configured(), clock=lambda: now) as client:
        with pytest.raises(APIError, match="batch_not_enabled"):
            await client.request(
                "videos.batchGetStats", {"part": "statistics", "id": "aaaaaaaaaaa"}
            )
        assert client.ledger.entries == []
    async with YouTubeClient(
        configured(batch_stats_enabled=True),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=api_fixture["batch"])
        ),
        clock=lambda: now,
    ) as client:
        rows = await client.hydrate("video", ["aaaaaaaaaaa", "bbbbbbbbbbb"], batch_stats=True)
        observed = normalize(rows[0], "video", "batch-capture")
        assert observed.metadata.upload_at.isoformat() == "2026-09-18T12:00:00+00:00"
        assert observed.metadata.publication_at is None
        assert rows[1].outcome == Outcome.DELETED_OR_PRIVATE_UNKNOWN
        assert normalize(rows[1], "video", "batch-capture").metrics == {}
        assert client.ledger.totals() == {"video_stats": 1}


def test_normalization_hidden_rounded_and_publication(api_fixture, now):
    def result(name, kind):
        item = api_fixture[name]
        page = Page(f"{kind}s.list", 1, None, now, now, now, {"items": [item]})
        return normalize(EntityResult(item["id"], Outcome.AVAILABLE, page, item), kind, name)

    channel = result("channel", "channel")
    assert channel.metrics["subscriber_count"].value == 12300
    assert channel.metrics["subscriber_count"].state == EvidenceState.APPROXIMATE
    assert channel.provenance.precision == Precision.ROUNDED
    assert channel.metrics["subscriber_count"].provenance.precision == Precision.ROUNDED
    assert channel.metrics["view_count"].provenance.precision == Precision.EXACT
    assert channel.metadata.account_created_at.year == 2020
    assert channel.metadata.publication_at is None
    hidden = result("hidden_channel", "channel")
    assert hidden.metrics["subscriber_count"].value is None
    assert hidden.metrics["view_count"].value is None
    video = result("video", "video")
    assert video.metadata.publication_at.isoformat() == "2026-09-20T12:00:00+00:00"
    assert video.metadata.upload_at is None
    assert video.metrics["view_count"].value == 100
    assert "cumulative-mixed" in video.metric_definition
    assert "pre-2026" in regime(now - timedelta(days=60))


@pytest.mark.parametrize("invalid", [True, "-1", "NaN", "100.3", "١٠٠"])
def test_malformed_counts_are_partial_not_zero(api_fixture, now, invalid):
    item = copy.deepcopy(api_fixture["video"])
    item["statistics"]["viewCount"] = invalid
    page = Page("videos.list", 1, None, now, now, now, {"items": [item]})
    observation = normalize(
        EntityResult(item["id"], Outcome.AVAILABLE, page, item), "video", "bad-count"
    )
    assert observation.outcome == Outcome.PARTIAL_RESPONSE
    assert observation.metrics == {}


@pytest.mark.anyio
async def test_chunk_accounting_override_and_database_sink(repository, now, api_fixture):
    endpoints = dict(ENDPOINTS)
    endpoints["videos.list"] = replace(endpoints["videos.list"], cost=3, bucket="custom")
    ledger = QuotaLedger(
        QuotaContract(version="deployment-override", endpoints=endpoints), repository.record_quota
    )
    async with YouTubeClient(
        configured(api_batch_size=1),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"items": [api_fixture["video"]]})
        ),
        ledger=ledger,
        clock=lambda: now,
    ) as client:
        results = await client.hydrate("video", ["aaaaaaaaaaa", "bbbbbbbbbbb"])
        assert len(results) == 2
        assert ledger.totals() == {"custom": 6}
    rows = repository.connection.execute("SELECT * FROM quota_requests").fetchall()
    assert len(rows) == 2
    assert all(row["contract_version"] == "deployment-override" for row in rows)
    assert all(row["request_count"] == 1 for row in rows)


@pytest.mark.anyio
async def test_comment_playlists_and_reply_routes(api_fixture):
    paths = []

    def handle(request):
        paths.append(request.url.path)
        if request.url.path.endswith("commentThreads"):
            return httpx.Response(403, json=api_fixture["comments_disabled"])
        return httpx.Response(200, json={"items": []})

    async with YouTubeClient(configured(), transport=httpx.MockTransport(handle)) as client:
        comments = [p async for p in client.comment_threads("aaaaaaaaaaa")]
        assert comments[0].outcome == Outcome.UNAVAILABLE
        assert comments[0].reason == "commentsDisabled"
        assert len([p async for p in client.playlists("UC" + "a" * 22)]) == 1
        assert len([p async for p in client.replies("top-level-comment")]) == 1
        assert client.ledger.totals() == {"general": 3}
    assert paths == ["/youtube/v3/commentThreads", "/youtube/v3/playlists", "/youtube/v3/comments"]
