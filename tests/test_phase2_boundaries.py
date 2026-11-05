import json
import sqlite3
from datetime import timedelta

import pytest
from phase2_helpers import candidate, definition, seed

from youtube_niche_mcp.api.client import EntityResult, Page
from youtube_niche_mcp.cli import main
from youtube_niche_mcp.collectors.normalize import normalize
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import applied_migrations, migrate
from youtube_niche_mcp.db.schema import MIGRATIONS, Migration
from youtube_niche_mcp.db.status import integrity
from youtube_niche_mcp.domain.foundation import Outcome
from youtube_niche_mcp.eligibility.adapters import metadata_claims
from youtube_niche_mcp.eligibility.cohorts import CohortBuilder
from youtube_niche_mcp.eligibility.models import Claim, Subject
from youtube_niche_mcp.eligibility.rules import classify


@pytest.mark.parametrize("version", [0, 1, 2, 3, 4])
def test_frozen_v1_v2_and_atomic_upgrade_to_v3(tmp_path, version, now):
    assert (
        MIGRATIONS[0].checksum == "df4ead10f9d64ecd7950b0c37717976e475bd2dd6e0a6ca1d047554509f12177"
    )
    assert (
        MIGRATIONS[1].checksum == "c44e9bcca6a67d4007c209e306958ed31d02ef60f25aeeac01bb0bfae34a89c9"
    )
    with connect(tmp_path / "upgrade.sqlite3") as c:
        if version:
            migrate(c, MIGRATIONS[:version])
        before = tuple(tuple(r) for r in applied_migrations(c))
        if version == 2:
            c.execute("INSERT INTO channels VALUES (?,?)", ("UC" + "a" * 22, now.isoformat()))
            c.commit()
        assert migrate(c, MIGRATIONS[:5]) == list(range(version + 1, 6))
        assert tuple(tuple(r) for r in applied_migrations(c))[:version] == before
        assert integrity(c)["ok"]
        assert len(c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()) == 34
        if version == 2:
            assert c.execute("SELECT COUNT(*) FROM channels").fetchone()[0] == 1


def test_failed_v3_upgrade_leaves_v2_whole(tmp_path):
    with connect(tmp_path / "rollback.sqlite3") as c:
        migrate(c, MIGRATIONS[:2])
        before = tuple(tuple(r) for r in applied_migrations(c))
        broken = Migration(3, "broken", (*MIGRATIONS[2].statements, "INVALID SQL"))
        with pytest.raises(sqlite3.OperationalError):
            migrate(c, (*MIGRATIONS[:2], broken))
        assert tuple(tuple(r) for r in applied_migrations(c)) == before
        assert not c.execute(
            "SELECT 1 FROM sqlite_master WHERE name='classification_claims'"
        ).fetchone()
        assert integrity(c)["ok"]


@pytest.mark.parametrize(
    "parts,snippet,live,label",
    [
        ((), {"liveBroadcastContent": "none"}, {}, "unknown"),
        (("liveStreamingDetails",), {"liveBroadcastContent": "none"}, {}, "ordinary_vod"),
        ((), {"liveBroadcastContent": "live"}, {}, "currently_live"),
        ((), {"liveBroadcastContent": "upcoming"}, {}, "scheduled_live"),
        (
            ("liveStreamingDetails",),
            {"liveBroadcastContent": "none"},
            {"actualStartTime": "2026-10-01T00:00:00Z", "actualEndTime": "2026-10-01T01:00:00Z"},
            "archived_live",
        ),
    ],
)
def test_normalized_live_and_audio_metadata(now, parts, snippet, live, label):
    item = {
        "id": "a" * 11,
        "snippet": {
            **snippet,
            "title": "English title",
            "defaultAudioLanguage": "en-US",
            "defaultLanguage": "en",
        },
        "liveStreamingDetails": live,
        "contentDetails": {"duration": "PT8M"},
        "statistics": {"viewCount": "0"},
    }
    p = Page("videos.list", 1, None, now, now, now, {"items": [item]}, requested_parts=parts)
    observation = normalize(EntityResult("a" * 11, Outcome.AVAILABLE, p, item), "video", "fixture")
    claims = metadata_claims(observation)
    subject = Subject(entity_kind="video", entity_id="a" * 11)
    assert classify(subject, "live_status_v1", claims, decided_at=now).label == label
    language = classify(subject, "spoken_language_v1", claims, decided_at=now)
    assert language.label == "likely_english" and language.permission_state == "policy_required"
    assert classify(subject, "surface_format_v1", claims, decided_at=now).label == "unknown"


@pytest.mark.parametrize("audio,expected", [(None, "unknown"), ("en", "likely_english")])
def test_provider_text_language_stays_distinct_from_audio(
    observation_factory, now, audio, expected
):
    observation = observation_factory(source="provider:metadata")
    observation = observation.model_copy(
        update={
            "metadata": observation.metadata.model_copy(
                update={"default_language": "en", "default_audio_language": audio}
            )
        }
    )
    d = classify(
        Subject(entity_kind="video", entity_id="a" * 11),
        "spoken_language_v1",
        metadata_claims(observation),
        decided_at=now,
    )
    assert d.label == expected and d.state.value != "verified"


def test_channel_aggregate_partial_full_hybrid_coverage(repository, observation_factory, now):
    e, channel, videos, at = seed(repository, observation_factory, now, uploads=2)
    did, d = e.aggregate_faceless(channel.entity_id, at=at)
    assert d.label == "verified_faceless" and d.details["coverage"] == 1
    assert len(d.details["supporting_decision_ids"]) == 2
    c = Claim(
        subject=videos[0],
        field="faceless",
        value="host_central",
        basis="human_review",
        source="fixture:human_review",
        source_version="v2",
        observed_at=now,
        available_at=now,
        reason="Later recurring host review",
        complete_review=True,
        data_origin="independent_annotation",
        permission_state="permitted",
    )
    e.append_claim(c)
    e.evaluate(videos[0], "faceless_v1", at=now)
    _, updated = e.aggregate_faceless(channel.entity_id, at=now)
    assert updated.label == "hybrid" and updated.details["reviewed_eligible_video_count"] == 2
    assert e.latest(channel, "faceless_v1", at)[0] == did


def test_same_source_revisions_not_conflicts_but_alternatives_stay(
    repository, observation_factory, now
):
    e, channel, _, at = seed(repository, observation_factory, now)
    earlier = e.latest(channel, "current_small_v1_50k", at)
    c = Claim(
        subject=channel,
        field="subscriber_count",
        value={"count": 500000},
        basis="official_metadata",
        source="fixture:size",
        source_version="v2",
        observed_at=now,
        available_at=now,
        reason="Later growth",
        data_origin="independent_annotation",
        permission_state="permitted",
    )
    e.append_claim(c)
    _, d = e.evaluate(channel, "current_small_v1_50k", at=now)
    assert d.label == "known_not_small" and d.state.value == "excluded"
    assert len(e.claims(channel, now, "subscriber_count")) == 2
    assert e.latest(channel, "current_small_v1_50k", at) == earlier


def test_niche_entry_activity_independence_rules_have_explicit_states(now):
    subject = Subject(entity_kind="channel", entity_id="UC" + "a" * 22)

    def c(field, value, basis="human_review"):
        return Claim(
            subject=subject,
            field=field,
            value=value,
            basis=basis,
            source="fixture:review",
            source_version="v1",
            observed_at=now,
            available_at=now,
            reason="Independent review",
            data_origin="independent_annotation",
            permission_state="permitted",
        )

    entry = classify(
        subject,
        "niche_entry_v1",
        (c("niche_entry", {"first_observed_niche_entry": (now - timedelta(days=1)).isoformat()}),),
        decided_at=now,
    )
    assert entry.label == "first_observed_niche_entry" and entry.state.value == "uncertain"
    activity = classify(
        subject,
        "activity_v1",
        (
            c(
                "activity",
                {"first_observed": (now - timedelta(days=150)).isoformat(), "publications": []},
            ),
        ),
        decided_at=now,
    )
    assert (
        activity.label == "currently_inactive_observed"
        and activity.details["permanent_exit"] == "unknown"
    )
    assert (
        classify(
            subject,
            "creator_independence_v1",
            (c("creator_relation", "group", "production_style"),),
            decided_at=now,
        ).label
        == "unknown"
    )
    assert (
        classify(
            subject,
            "creator_independence_v1",
            (c("creator_relation", "group", "public_disclosure"),),
            decided_at=now,
        ).label
        == "documented_group"
    )


def test_publication_conflict_stays_in_cohort_provenance(repository, observation_factory, now):
    e, _, videos, at = seed(repository, observation_factory, now)
    first = repository.latest("video", videos[0].entity_id, now)["observation_id"]
    other = observation_factory(
        0,
        entity_id=videos[0].entity_id,
        source="provider:date",
        at=now,
        publication=now - timedelta(days=10),
    )
    second = repository.append(other)
    cid = repository.conflict(
        "video", videos[0].entity_id, "publication_at", first, second, detected_at=now
    )
    frame = CohortBuilder(e).freeze(definition(now, "eligible_long_form"), (candidate(videos[0]),))
    assert frame[0].state.value == "source_conflict" and cid in frame[0].evidence_ids


@pytest.mark.parametrize("command", ["eligibility", "taxonomy", "cohort"])
def test_phase2_cli_inspection_offline_no_db_creation(tmp_path, capsys, command):
    db = tmp_path / "absent" / "database.sqlite3"
    operation = "rules" if command == "eligibility" else "status"
    assert main(["--db", str(db), command, operation]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] and not db.parent.exists()
