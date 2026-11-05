from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from youtube_niche_mcp.api.client import YouTubeClient
from youtube_niche_mcp.collectors.discovery import DiscoveryService
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.db.status import integrity
from youtube_niche_mcp.domain.foundation import Metadata, Outcome
from youtube_niche_mcp.services.capabilities import operational_status


@pytest.mark.anyio
@pytest.mark.parametrize("summary", [None, [], {"failedVideoIds": "bad"}, {"failedVideoIds": [1]}])
async def test_malformed_batch_summary_per_id_partial(api_fixture, summary):
    payload = {"items": [api_fixture["batch"]["items"][0]], "summary": summary}
    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret"), batch_stats_enabled=True),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    ) as client:
        rows = await client.hydrate("video", ["aaaaaaaaaaa", "bbbbbbbbbbb"], batch_stats=True)
    assert all(row.outcome == Outcome.PARTIAL_RESPONSE and row.item is None for row in rows)


@pytest.mark.anyio
async def test_discovery_expiry_and_policy_cascades(repository, observation_factory, now):
    time = [now]
    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"items": [{"id": {"videoId": "aaaaaaaaaaa"}}]}
            )
        ),
        clock=lambda: time[0],
    ) as client:
        service = DiscoveryService(client, repository)
        await service.collect("expire-run", query="fixture")
        official = repository.append(observation_factory())
        provider = repository.append(observation_factory(200, source="provider:fixture"))
        repository.conflict(
            "video", "aaaaaaaaaaa", "view_count", official, provider, detected_at=now
        )
        time[0] += timedelta(days=30)
        assert service.manifest("expire-run")["retention_state"] == "expired"
        repository.clock = lambda: time[0]
        assert repository.conflicts("video", "aaaaaaaaaaa", time[0]) == []
        deleted = repository.purge_expired()
    assert deleted["discovery_runs"] == 1
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM discovery_results").fetchone()[0] == 0
    )
    assert repository.connection.execute("SELECT COUNT(*) FROM discovery_pages").fetchone()[0] == 0
    assert repository.connection.execute("SELECT COUNT(*) FROM source_conflicts").fetchone()[0] == 0
    assert integrity(repository.connection)["ok"]


def test_publication_and_provider_clocks_distinct_and_normalized(now):
    metadata = Metadata(
        account_created_at=now - timedelta(days=300),
        publication_at=now,
        upload_at=now - timedelta(days=2),
        playlist_added_at=now + timedelta(hours=1),
        provider_index_at=now + timedelta(days=1),
    )
    assert (
        len(
            {
                metadata.account_created_at,
                metadata.publication_at,
                metadata.upload_at,
                metadata.playlist_added_at,
                metadata.provider_index_at,
            }
        )
        == 5
    )
    assert Metadata(publication_at="2026-10-02T11:00:00+05:00").publication_at == now


def test_failure_and_future_captures_do_not_enable_history(repository, observation_factory, now):
    from datetime import UTC, datetime

    from youtube_niche_mcp.domain.foundation import Observation

    actual = datetime.now(UTC)
    base = observation_factory(at=actual)
    failed = Observation.model_validate(
        {**base.model_dump(), "outcome": Outcome.API_MISSING, "metrics": {}}
    )
    repository.append(failed)
    dbpath = repository.connection.execute("PRAGMA database_list").fetchone()[2]
    settings = Settings(db_path=dbpath)
    assert operational_status(settings)["history_count"] == 0
    repository.append(observation_factory(at=actual + timedelta(days=1)))
    assert operational_status(settings)["history_count"] == 0
    repository.append(observation_factory(at=actual - timedelta(minutes=1)))
    assert operational_status(settings)["history_count"] == 1
