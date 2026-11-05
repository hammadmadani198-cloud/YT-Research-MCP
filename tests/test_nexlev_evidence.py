import json
import sqlite3
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from youtube_niche_mcp.api.client import YouTubeClient
from youtube_niche_mcp.collectors.nexlev.client import NexLevClient, ProviderQuotaEntry, Response
from youtube_niche_mcp.collectors.nexlev.contracts import ROUTES
from youtube_niche_mcp.collectors.nexlev.models import (
    EvidenceBatch,
    FieldClaim,
    HistoryPoint,
    ProviderRecord,
)
from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository
from youtube_niche_mcp.collectors.nexlev.service import NexLevService
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import migrate
from youtube_niche_mcp.db.schema import MIGRATIONS, Migration
from youtube_niche_mcp.db.status import integrity
from youtube_niche_mcp.eligibility.models import Claim, Subject

PATTERNS = json.loads(
    (Path(__file__).parent / "fixtures/nexlev_patterns.json").read_text(encoding="utf-8")
)
CHANNEL = "UC" + "a" * 22
VIDEO = PATTERNS["dustrialize_video"]


def record(now, route="nexlev.video_details", kind="video", entity=VIDEO, **fields):
    from youtube_niche_mcp.collectors.nexlev.models import FIELD_TRUST

    return ProviderRecord(
        route=route,
        subject=Subject(entity_kind=kind, entity_id=entity),
        provider_record_id="provider-record",
        fetch_at=now,
        observed_at=now,
        available_at=now,
        provider_capture_at=now,
        claims=tuple(
            FieldClaim(field=k, value=v, trust_class=FIELD_TRUST[k]) for k, v in fields.items()
        ),
    )


def ingest(repo, name, r, discovery=None):
    return repo.ingest(
        EvidenceBatch(
            batch_id=name, route=r.route, fetch_at=r.fetch_at, records=(r,), discovery=discovery
        )
    )


def test_cross_route_publication_conflict_and_snapshot_variation(repository, now):
    repo = NexLevRepository(repository)
    left = record(now, publication_at=PATTERNS["publication_dates"][0])
    right = record(
        now, route="nexlev.small_channel_viral", publication_at=PATTERNS["publication_dates"][1]
    )
    ingest(repo, "left", left)
    ingest(repo, "right", right)
    assert len(repository.conflicts("video", VIDEO, now)) == 1
    assert len(repo.records(left.subject, now)) == 2
    early = now - timedelta(hours=1)
    first = record(early, "nexlev.channel_about", "channel", CHANNEL, subscriber_count=100)
    later = record(now, "nexlev.channel_videos", "channel", CHANNEL, subscriber_count=200)
    ingest(repo, "first", first)
    ingest(repo, "later", later)
    assert not repository.conflicts("channel", CHANNEL, now)
    assert len(repo.records(first.subject, now)) == 2
    assert (
        json.loads(repo.records(first.subject, now)[0]["record_json"])["provider_capture_at"]
        != now.isoformat()
    )


def test_finance_firewall_and_monetization_disagreement(repository, now):
    repo = NexLevRepository(repository)
    for index, status in enumerate(PATTERNS["monetization"]):
        ingest(
            repo,
            str(index),
            record(now, "nexlev.monetization_claim", "channel", CHANNEL, monetized=status),
        )
    ingest(
        repo,
        "money",
        record(
            now,
            "nexlev.geography_revenue_estimate",
            "channel",
            CHANNEL,
            monthly_revenue=PATTERNS["modeled_monthly_revenue"],
            rpm=4.5,
        ),
    )
    assert len(repository.conflicts("channel", CHANNEL, now)) == 1
    assert len(repo.records(Subject(entity_kind="channel", entity_id=CHANNEL), now)) == 3
    assert not repo.eligibility.claims(Subject(entity_kind="channel", entity_id=CHANNEL), now)
    assert repository.latest("channel", CHANNEL, now) is None
    with pytest.raises(ValueError):
        FieldClaim(field="rpm", value=4.5, trust_class="T1")


@pytest.mark.parametrize(
    "field,value",
    [
        ("opportunity", 0.9),
        ("actual_revenue", 3000),
        ("retention", 75),
        ("verified_canonical", True),
        ("html", "<script>alert(1)</script>"),
    ],
)
def test_narrow_fields_never_admit_scoring_private_or_html(repository, now, field, value):
    repo = NexLevRepository(repository)
    r = record(now, title="plain").model_dump(mode="json")
    r["claims"] = [{"field": field, "value": value, "trust_class": "T5"}]
    with pytest.raises(ValueError):
        repo.ingest({"batch_id": "bad", "route": r["route"], "fetch_at": now, "records": [r]})
    assert repository.connection.execute("SELECT COUNT(*) FROM provider_runs").fetchone()[0] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"provider": "other"},
        {"route": "nexlev.private"},
        {"verified": True},
        {"access_mode": "documented_rest"},
    ],
)
def test_external_cannot_self_attest_or_change_provider(repository, now, change):
    r = record(now)
    batch = EvidenceBatch(
        batch_id="external", route=r.route, fetch_at=now, records=(r,)
    ).model_dump(mode="json")
    with pytest.raises(ValueError):
        NexLevRepository(repository).ingest({**batch, **change})


def test_replay_atomic_failure_and_append_only(repository, now):
    repo = NexLevRepository(repository)
    r = record(now, title="original")
    assert ingest(repo, "same", r) == ingest(repo, "same", r)
    with pytest.raises(ValueError):
        ingest(repo, "same", record(now, title="changed"))
    with pytest.raises(sqlite3.IntegrityError):
        repository.connection.execute("UPDATE provider_evidence SET route='changed'")
    bad = EvidenceBatch(
        batch_id="future",
        route=r.route,
        fetch_at=now,
        records=(r.model_copy(update={"available_at": now + timedelta(days=1)}),),
    )
    with pytest.raises(ValueError):
        repo.ingest(bad)
    assert not repo.manifest("future")["run"]


def test_semantic_vs_zero_filter_discovery_rank_dedup_and_no_census(repository, now):
    from youtube_niche_mcp.collectors.nexlev.models import DiscoveryContext

    repo = NexLevRepository(repository)
    context = DiscoveryContext(
        query="weak industrial",
        mode="semantic",
        total_results=450,
        limit=10,
        has_more=True,
        result_ceiling=500,
        filters={"maxSubs": 100},
    )
    r = record(now, "nexlev.niche_finder.semantic", "channel", CHANNEL, semantic_similarity=0.72)
    batch = EvidenceBatch(
        batch_id="semantic",
        route=r.route,
        fetch_at=now,
        records=(r.model_copy(update={"rank": 1}), r.model_copy(update={"rank": 2})),
        discovery=context,
    )
    manifest = repo.ingest(batch)
    assert manifest["occurrences"] == 2 and len(manifest["canonical_candidates"]) == 1
    assert manifest["population_denominator"] is None
    assert manifest["run"]["discovery"]["total_results"] == 450
    assert [
        row[0]
        for row in repository.connection.execute("SELECT rank FROM discovery_results ORDER BY rank")
    ] == [1, 2]
    zero = repo.ingest(
        EvidenceBatch(
            batch_id="zero",
            route="nexlev.niche_finder.filter",
            fetch_at=now,
            discovery=DiscoveryContext(query="*", mode="filter", total_results=0, has_more=False),
        )
    )
    assert zero["zero_result"] and zero["population_denominator"] is None
    assert zero["run"]["discovery"]["query"] == "*"


def test_weak_zero_and_provider_history_never_backfill(repository, now):
    repo = NexLevRepository(repository)
    r = record(
        now, "nexlev.suggested_catalog", "channel", CHANNEL, subscriber_count=0, view_count=7
    )
    ingest(repo, "weak", r)
    stored = repo.records(r.subject, now)[0]
    assert "provider_zero_requires_hydration" in json.loads(stored["anomalies_json"])
    assert repository.publication_size(CHANNEL, now).value is None
    points = tuple(
        HistoryPoint(
            date=now - timedelta(days=d),
            subscribers=s,
            videos=0,
            data_fetched_at=now + timedelta(days=1),
        )
        for d, s in zip(PATTERNS["daily_offsets"], PATTERNS["daily_subscribers"], strict=True)
    )
    from youtube_niche_mcp.collectors.nexlev.models import DiscoveryContext

    h = record(now, "nexlev.daily_analytics", "channel", CHANNEL).model_copy(
        update={"history": points, "rank": 1}
    )
    ingest(repo, "history", h, DiscoveryContext(mode="catalog", requested_history_days=90))
    stored = repo.records(h.subject, now)
    flags = set(json.loads(next(r for r in stored if r["route"] == h.route)["anomalies_json"]))
    assert {
        "negative_delta",
        "implausible_rebound",
        "gap",
        "partial_window",
        "impossible_count",
        "timestamp_conflict",
        "stale_series",
        "implausible_all_zero_video_count",
    } <= flags
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM statistical_history").fetchone()[0] == 0
    )
    assert repository.publication_size(CHANNEL, now).value is None


@pytest.mark.anyio
async def test_official_hydration_preserves_provider_and_selects_public_facts(repository, now):
    repo = NexLevRepository(repository)
    r = record(
        now, publication_at=PATTERNS["publication_dates"][0], duration_seconds=300, view_count=7
    )
    ingest(repo, "provider", r)

    def official(request):
        assert request.url.host == "www.googleapis.com"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": VIDEO,
                        "snippet": {
                            "title": "Official",
                            "channelId": CHANNEL,
                            "publishedAt": PATTERNS["publication_dates"][1],
                            "liveBroadcastContent": "none",
                        },
                        "statistics": {"viewCount": "123"},
                        "contentDetails": {"duration": "PT10M"},
                    }
                ]
            },
        )

    yt = YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        clock=lambda: now,
        transport=httpx.MockTransport(official),
    )
    nl = NexLevClient(Settings(), clock=lambda: now)
    try:
        result = await NexLevService(nl, repo).hydrate(yt, r.subject, capture_id="canonical")
        assert result[0]["public_values"]["view_count"] == 123
        assert result[0]["public_values"]["duration_seconds"] == 600
        assert result[0]["canonical_source"] == "youtube:videos.list"
        assert len(repo.records(r.subject, now)) == 1
        conflicts = repository.conflicts("video", VIDEO, now)
        assert {c["field"] for c in conflicts} >= {
            "publication_at",
            "duration_seconds",
            "view_count",
        }
        assert all(c["preferred_source"] == "youtube:videos.list" for c in conflicts)
        assert repository.latest("video", VIDEO, now)["view_count"] == 123
    finally:
        await yt.__aexit__(None, None, None)
        await nl.aclose()


def test_bridged_provider_confidence_cannot_override_sample(repository, now):
    repo = NexLevRepository(repository)
    r = record(now, "nexlev.faceless_classifier", "video", PATTERNS["bridged_video"], faceless=True)
    r = r.model_copy(update={"confidence": 0.98})
    ingest(repo, "bridged", r)
    _, decision = repo.eligibility.evaluate(r.subject, "faceless_v1", at=now)
    assert decision.label != "verified_faceless"
    repo.eligibility.append_claim(
        Claim(
            subject=r.subject,
            field="faceless",
            value="hybrid",
            basis="sample_review",
            source="independent_sample_01_04_01_10",
            source_version="sample-v1",
            observed_at=now,
            available_at=now,
            reason=PATTERNS["independent_sample"],
            data_origin="independent_annotation",
        )
    )
    _, decision = repo.eligibility.evaluate(r.subject, "faceless_v1", at=now)
    assert decision.label in {"hybrid", "unknown"} and decision.conflicts
    assert len(repo.eligibility.claims(r.subject, now)) == 2


def test_language_false_positive_and_subtitle_translation_not_audio(repository, now):
    from youtube_niche_mcp.collectors.nexlev.models import DiscoveryContext

    repo = NexLevRepository(repository)
    r = record(
        now, "nexlev.faceless_outliers.semantic", title="English ASCII", spoken_language="hi"
    )
    ingest(
        repo,
        "englishOnly",
        r.model_copy(update={"rank": 1}),
        DiscoveryContext(
            query="English industrial", mode="semantic", filters={"englishOnly": True}
        ),
    )
    _, decision = repo.eligibility.evaluate(r.subject, "spoken_language_v1", at=now)
    assert decision.label == "non_english"
    with pytest.raises(ValueError):
        record(
            now,
            spoken_language="en",
            transcript_metadata={"selected_language": "en", "translated": True},
        )


@pytest.mark.parametrize(
    "translated,generated,available",
    [(True, False, True), (False, True, True), (None, None, False)],
)
@pytest.mark.anyio
async def test_transcript_metadata_and_expiry(repository, now, translated, generated, available):
    repo = NexLevRepository(repository)
    client = NexLevClient(Settings(), clock=lambda: now)
    service = NexLevService(client, repo)
    try:
        payload = [
            {
                "id": VIDEO,
                "selected": {"title": "English (auto-generated)" if generated else "English"},
                "transcript": [{"startMs": "0", "text": "caption sample"}] if available else [],
                "languageMenu": [{"title": "Hindi"}, {"title": "English"}],
            }
        ]
        service.store_response(
            "text", Response("nexlev.transcript", now, now, payload), {"videoId": VIDEO}
        )
        record_json = repo.records(Subject(entity_kind="video", entity_id=VIDEO), now)[0][
            "record_json"
        ]
        assert "caption sample" not in record_json
        assert "contract_review_required" in record_json
        assert service.text_cache.get("nexlev:text", "nexlev.transcript", {"videoId": VIDEO})
        service.text_cache.clock = lambda: now + timedelta(hours=2)
        assert (
            service.text_cache.get("nexlev:text", "nexlev.transcript", {"videoId": VIDEO}) is None
        )
        assert repo.records(Subject(entity_kind="video", entity_id=VIDEO), now)
        repository.clock = lambda: now + timedelta(days=2)
        assert not repo.records(Subject(entity_kind="video", entity_id=VIDEO), now)
        repository.purge_expired()
        assert (
            repository.connection.execute("SELECT COUNT(*) FROM provider_runs").fetchone()[0] == 0
        )
    finally:
        await client.aclose()


def test_external_quota_unknown_not_invented(repository, now):
    repo = NexLevRepository(repository)
    repo.record_quota(
        ProviderQuotaEntry(
            "nexlev.niche_finder.semantic",
            1,
            None,
            None,
            "nexlev_external_plan_unknown",
            now.isoformat(),
            access_mode="external_orchestrated",
        )
    )
    row = repository.connection.execute("SELECT * FROM provider_quota_details").fetchone()
    assert row["documented_cost"] is None and row["charged_cost"] is None


def test_v3_frozen_and_v4_failed_migration_atomic(tmp_path):
    assert (
        MIGRATIONS[2].checksum == "7296eb9bec26ba21ea8caa0f6be50895e7944fd987d06106b08e873ee588ae7d"
    )
    with connect(tmp_path / "v3.sqlite3") as c:
        migrate(c, MIGRATIONS[:3])
        broken = Migration(4, "broken", (*MIGRATIONS[3].statements, "INVALID SQL"))
        with pytest.raises(sqlite3.OperationalError):
            migrate(c, (*MIGRATIONS[:3], broken))
        assert not c.execute("SELECT 1 FROM sqlite_master WHERE name='provider_runs'").fetchone()
        assert migrate(c, MIGRATIONS[:4]) == [4] and integrity(c)["ok"]
    assert all(r.startswith("nexlev.") for r in ROUTES)
