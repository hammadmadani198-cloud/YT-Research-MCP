import json
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from youtube_niche_mcp.cli import main
from youtube_niche_mcp.collectors.nexlev.client import NexLevClient, NexLevError, Response
from youtube_niche_mcp.collectors.nexlev.models import FieldClaim, ProviderRecord
from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository
from youtube_niche_mcp.collectors.nexlev.service import NexLevService
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.eligibility.models import Subject, TaxonomyNode

CHANNEL = "UC" + "a" * 22
VIDEO = "ZP7jTDAHryQ"


@pytest.mark.parametrize(
    "operation", ["status", "capabilities", "quota", "contract", "cache-status"]
)
def test_provider_cli_offline_no_key_no_creation(tmp_path, capsys, operation):
    path = tmp_path / "absent/db.sqlite3"
    assert main(["--db", str(path), "provider", operation]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["offline"] and result["provider"] == "nexlev"
    assert not path.parent.exists()


@pytest.mark.parametrize(
    "route,parameters,payload,metric",
    [
        (
            "similar_channels",
            {"channelId": CHANNEL, "level": 2, "channelType": "all"},
            {
                "data": [
                    {"about": {"channelId": CHANNEL, "subscriberCount": 17}, "similarityScore": 72}
                ]
            },
            "semantic_similarity",
        ),
        (
            "similar_videos",
            {"videoId": VIDEO},
            [{"videoId": VIDEO, "viewCount": "7", "similarity_score": 85, "format_score": 92}],
            "format_similarity",
        ),
        (
            "similar_thumbnails",
            {"text": "space"},
            {"data": [{"id": VIDEO, "similarity": 0.8}]},
            "thumbnail_similarity",
        ),
    ],
)
@pytest.mark.anyio
async def test_similarity_acquisition_keeps_seed_rank_and_t4(
    repository, now, route, parameters, payload, metric
):
    repo = NexLevRepository(repository)
    client = NexLevClient(
        Settings(nexlev_api_key=SecretStr("provider-fixture")),
        clock=lambda: now,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)),
    )
    try:
        manifest = await NexLevService(client, repo).acquire(
            "similar", route, parameters, deep_mode=True
        )
        c = manifest["run"]["discovery"]
        assert c["mode"] == "similarity" and manifest["population_denominator"] is None
        if route != "similar_thumbnails":
            assert c["seed_id"] == parameters.get("channelId", parameters.get("videoId"))
        record = manifest["run"]["records"][0]
        assert record["rank"] == 1
        assert next(f for f in record["claims"] if f["field"] == metric)["trust_class"] == "T4"
        assert "audience_overlap" not in json.dumps(manifest)
        assert not repo.eligibility.claims(Subject.model_validate(record["subject"]), now)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_comments_reply_order_disabled_text_retention(repository, now):
    client = NexLevClient(Settings(), clock=lambda: now)
    repo = NexLevRepository(repository)
    service = NexLevService(client, repo)
    try:
        payload = {
            "comments": [
                {
                    "id": "c1",
                    "text": "question",
                    "replies": [{"id": "r1", "parentId": "c1", "text": "reply"}],
                }
            ],
            "continuation": "next-page",
            "disabled": False,
        }
        result = service.store_response(
            "comments", Response("nexlev.comments", now, now, payload), {"videoId": VIDEO}
        )
        value = result["run"]["records"][0]["claims"][0]["value"]
        assert value["ordering"] == "provider_order_unknown" and not value["disabled"]
        cached = service.text_cache.get("nexlev:text", "nexlev.comments", {"videoId": VIDEO})
        assert cached.payload["response"]["comments"][0]["replies"][0]["parentId"] == "c1"
        service.text_cache.clock = lambda: now + timedelta(hours=2)
        assert service.text_cache.get("nexlev:text", "nexlev.comments", {"videoId": VIDEO}) is None
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_translated_generated_and_missing_transcripts_preserved(repository, now):
    client = NexLevClient(Settings(), clock=lambda: now)
    repo = NexLevRepository(repository)
    service = NexLevService(client, repo)
    try:
        payload = [
            {
                "id": VIDEO,
                "translated": True,
                "original": False,
                "selected": {"title": "English (auto-generated)"},
                "transcript": [{"text": "translated text"}],
                "languageMenu": [{"title": "Hindi"}],
            }
        ]
        result = service.store_response(
            "track", Response("nexlev.transcript", now, now, payload), {"videoId": VIDEO}
        )
        value = result["run"]["records"][0]["claims"][0]["value"]
        assert value["translated"] and value["auto_generated"] and value["original"] is False
        assert value["track_languages"] == ["Hindi"]
        assert not repo.eligibility.claims(Subject(entity_kind="video", entity_id=VIDEO), now)
        empty = service.store_response(
            "missing", Response("nexlev.transcript", now, now, []), {"videoId": VIDEO}
        )
        assert empty["run"]["records"][0]["claims"][0]["value"]["available"] is False
    finally:
        await client.aclose()


def test_configured_secret_rejected_in_external_ingestion_and_quota(repository, now):
    from youtube_niche_mcp.collectors.nexlev.client import ProviderQuotaEntry

    repo = NexLevRepository(repository, Settings(nexlev_api_key=SecretStr("private-nexlev-secret")))
    r = ProviderRecord(
        route="nexlev.video_details",
        subject=Subject(entity_kind="video", entity_id=VIDEO),
        provider_record_id="r",
        fetch_at=now,
        observed_at=now,
        available_at=now,
        claims=(FieldClaim(field="title", value="private-nexlev-secret", trust_class="T1"),),
    )
    with pytest.raises(ValueError) as e:
        repo.ingest(
            {
                "batch_id": "s",
                "route": r.route,
                "fetch_at": now,
                "records": [r.model_dump(mode="json")],
            }
        )
    assert "private-nexlev-secret" not in str(e.value)
    with pytest.raises(ValueError):
        repo.record_quota(
            ProviderQuotaEntry("private-nexlev-secret", 1, None, None, "external", now.isoformat())
        )
    assert repository.connection.execute("SELECT COUNT(*) FROM provider_runs").fetchone()[0] == 0


@pytest.mark.anyio
async def test_taxonomy_many_to_many_aliases_are_annotations(repository, now):
    repo = NexLevRepository(repository)
    client = NexLevClient(Settings(), clock=lambda: now)
    try:
        for node in ("history", "engineering"):
            repo.eligibility.add_node(
                TaxonomyNode(
                    node_id=node, taxonomy_version="v1", label=node, level="niche", available_at=now
                )
            )
        result = NexLevService(client, repo).map_taxonomy(
            Subject(entity_kind="channel", entity_id=CHANNEL),
            "Industrial History",
            [("history", "v1"), ("engineering", "v1")],
            at=now,
        )
        assert len(result["internal_aliases"]) == 2 and not result["membership_assignment"]
        assert (
            repository.connection.execute("SELECT COUNT(*) FROM niche_memberships").fetchone()[0]
            == 0
        )
        assert len(repo.records(Subject(entity_kind="channel", entity_id=CHANNEL), now)) == 1
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_unavailable_nexlev_does_not_change_official_capabilities(now):
    from youtube_niche_mcp.services.capabilities import capabilities

    settings = Settings(
        youtube_api_key=SecretStr("youtube-fixture"), nexlev_api_key=SecretStr("provider-fixture")
    )
    before = capabilities(settings)
    client = NexLevClient(
        settings, clock=lambda: now, transport=httpx.MockTransport(lambda r: httpx.Response(403))
    )
    try:
        with pytest.raises(NexLevError):
            await client.request("channel_about", {"id": CHANNEL})
        assert capabilities(settings) == before
        assert client.capabilities()[5]["network_probed"]
    finally:
        await client.aclose()
