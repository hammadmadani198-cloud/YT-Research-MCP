import copy
import json
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from youtube_niche_mcp.api.client import YouTubeClient
from youtube_niche_mcp.collectors.discovery import DiscoveryService
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.domain.foundation import Outcome
from youtube_niche_mcp.services.snapshots import SnapshotService


@pytest.mark.anyio
async def test_discovery_manifest_ranks_duplicates_bad_ids_and_route(repository, api_fixture, now):
    requests = []

    def handle(request):
        requests.append(request)
        index = 1 if request.url.params.get("pageToken") else 0
        return httpx.Response(200, json=api_fixture["discovery_pages"][index])

    settings = Settings(youtube_api_key=SecretStr("fixture-secret"))
    async with YouTubeClient(
        settings, transport=httpx.MockTransport(handle), clock=lambda: now
    ) as client:
        service = DiscoveryService(client, repository)
        manifest = await service.collect(
            "search-1",
            query="test query",
            filters={"regionCode": "PK", "relevanceLanguage": "en", "order": "date"},
            page_size=2,
        )
        assert manifest["run"]["route"] == "search.list"
        assert manifest["run"]["region"] == "PK"
        assert manifest["run"]["language"] == "en"
        assert manifest["run"]["sort_order"] == "date"
        assert manifest["run"]["page_size"] == 2
        assert manifest["run"]["outcome"] == "partial_response"
        assert json.loads(manifest["run"]["filters_json"])["parameters"]["q"] == "test query"
        assert [r["rank"] for r in manifest["results"]] == [1, 2, 3, 4, 5]
        assert [r["page_rank"] for r in manifest["results"]] == [1, 2, 1, 2, 3]
        assert [r["result_id"] for r in manifest["results"]][:3] == [
            "aaaaaaaaaaa",
            "bbbbbbbbbbb",
            "aaaaaaaaaaa",
        ]
        assert manifest["pages"][1]["request_token"] == "page-2"
        assert all(r["observed_at"] == r["available_at"] for r in manifest["results"])
        assert repository.connection.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 2
        assert (
            repository.connection.execute("SELECT COUNT(*) FROM video_observations").fetchone()[0]
            == 0
        )
        assert (
            await service.collect(
                "search-1",
                query="test query",
                filters={"regionCode": "PK", "relevanceLanguage": "en", "order": "date"},
                page_size=2,
            )
            == manifest
        )
        assert len(requests) == 2
        with pytest.raises(ValueError, match="replay"):
            await service.collect("search-1", query="changed")
        assert client.ledger.totals() == {"search": 2}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payloads,expected_pages,reason",
    [
        ([{"items": []}], 1, "ok"),
        ([{"items": [], "nextPageToken": "next"}, {"items": []}], 2, "ok"),
        (
            [{"items": [], "nextPageToken": "same"}, {"items": [], "nextPageToken": "same"}],
            2,
            "repeated_or_invalid_token",
        ),
        ([{"items": [], "nextPageToken": ["bad"]}], 1, "repeated_or_invalid_token"),
    ],
)
async def test_pagination_empty_single_multiple_and_repeated_token(
    payloads, expected_pages, reason, now
):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=payloads[len(calls) - 1])

    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        transport=httpx.MockTransport(handle),
        clock=lambda: now,
    ) as client:
        pages = [
            p
            async for p in client.pages(
                "search.list", {"part": "snippet", "q": "fixture", "maxResults": 1}
            )
        ]
        assert len(pages) == expected_pages
        assert pages[-1].reason == reason
        assert len(client.ledger.entries) == expected_pages


@pytest.mark.anyio
async def test_partial_failure_preserves_previous_results_and_failed_page(repository, now):
    count = 0

    def handle(request):
        nonlocal count
        count += 1
        if count == 1:
            return httpx.Response(
                200, json={"items": [{"id": {"videoId": "aaaaaaaaaaa"}}], "nextPageToken": "next"}
            )
        return httpx.Response(403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}})

    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        transport=httpx.MockTransport(handle),
        clock=lambda: now,
    ) as client:
        manifest = await DiscoveryService(client, repository).collect("partial", query="fixture")
    assert manifest["run"]["outcome"] == "quota_limited"
    assert len(manifest["results"]) == 1
    assert manifest["pages"][1]["reason"] == "quotaExceeded"
    assert manifest["pages"][1]["http_status"] == 403
    assert manifest["pages"][1]["request_token"] == "next"


@pytest.mark.anyio
async def test_uploads_enumeration_and_bounded_search(repository, api_fixture, now):
    requests = []

    def handle(request):
        requests.append(request)
        index = 1 if request.url.params.get("pageToken") else 0
        return httpx.Response(200, json=api_fixture["uploads_pages"][index])

    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        transport=httpx.MockTransport(handle),
        clock=lambda: now,
    ) as client:
        pages = [p async for p in client.uploads("UU" + "a" * 22)]
        assert len(pages) == 2
        manifest = await DiscoveryService(client, repository).collect(
            "uploads", route="playlistItems.list", filters={"playlistId": "UU" + "a" * 22}
        )
        assert manifest["run"]["mode"] == "uploads_catalog"
        assert [r["result_id"] for r in manifest["results"]] == ["aaaaaaaaaaa", "bbbbbbbbbbb"]
        bounded = [p async for p in client.uploads("UU" + "a" * 22, max_pages=1)]
        assert bounded[-1].reason == "page_limit"
        assert bounded[-1].outcome == Outcome.PARTIAL_RESPONSE
    assert all(r.url.path.endswith("playlistItems") for r in requests)


@pytest.mark.anyio
async def test_snapshot_replay_no_new_requests_and_missing_preserved(repository, api_fixture, now):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "items": [
                    api_fixture["channel"]
                    if request.url.path.endswith("channels")
                    else api_fixture["video"]
                ]
            },
        )

    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        transport=httpx.MockTransport(handle),
        clock=lambda: now,
    ) as client:
        service = SnapshotService(client, repository)
        first = await service.capture(
            "snapshot-1", video_ids=["aaaaaaaaaaa", "bbbbbbbbbbb"], channel_ids=["UC" + "a" * 22]
        )
        assert first["job"]["status"] == "partial_response"
        assert [r["outcome"] for r in first["targets"]] == ["available", "available", "API_missing"]
        assert all(
            r["request_at"] <= r["captured_at"] <= r["available_at"] for r in first["targets"]
        )
        assert (
            await service.capture(
                "snapshot-1",
                video_ids=["bbbbbbbbbbb", "aaaaaaaaaaa"],
                channel_ids=["UC" + "a" * 22],
            )
            == first
        )
        assert len(requests) == 2
        with pytest.raises(ValueError, match="replay"):
            await service.capture("snapshot-1", video_ids=["aaaaaaaaaaa"])
    missing = repository.latest("video", "bbbbbbbbbbb", now)
    assert missing["view_count"] is None
    assert missing["outcome"] == "API_missing"
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM video_observations").fetchone()[0] == 2
    )


@pytest.mark.anyio
async def test_later_snapshot_adds_capture_and_no_fake_history(repository, api_fixture, now):
    time = [now]
    value = [100]

    def handle(request):
        item = copy.deepcopy(api_fixture["video"])
        item["statistics"]["viewCount"] = str(value[0])
        return httpx.Response(200, json={"items": [item]})

    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        transport=httpx.MockTransport(handle),
        clock=lambda: time[0],
    ) as client:
        service = SnapshotService(client, repository)
        await service.capture("first", video_ids=["aaaaaaaaaaa"])
        time[0] += timedelta(hours=1)
        value[0] = 200
        await service.capture("second", video_ids=["aaaaaaaaaaa"])
    assert [
        row["view_count"] for row in repository.observations("video", "aaaaaaaaaaa", time[0])
    ] == [200, 100]
    assert repository.latest("video", "aaaaaaaaaaa", now - timedelta(seconds=1)) is None


@pytest.mark.anyio
async def test_snapshot_quota_per_id_failure(repository, api_fixture, now):
    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(403, json=api_fixture["quota"])
        ),
        clock=lambda: now,
    ) as client:
        result = await SnapshotService(client, repository).capture(
            "quota-job", video_ids=["aaaaaaaaaaa", "bbbbbbbbbbb"]
        )
    assert all(
        row["outcome"] == "quota_limited" and row["reason"] == "quotaExceeded"
        for row in result["targets"]
    )
    assert all(row["http_status"] == 403 for row in result["targets"])
    assert all(
        row["view_count"] is None for row in repository.observations("video", "aaaaaaaaaaa", now)
    )


@pytest.mark.anyio
async def test_failed_discovery_without_key_has_manifest(repository, now):
    async with YouTubeClient(Settings(), clock=lambda: now) as client:
        result = await DiscoveryService(client, repository).collect("no-key", query="fixture")
        assert client.ledger.entries == []
    assert result["pages"][0]["reason"] == "api_key_absent"
    assert result["results"] == []
    assert result["run"]["outcome"] == "unavailable"
