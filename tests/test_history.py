import json
import sqlite3
from datetime import timedelta, timezone

import pytest

from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import applied_migrations, migrate
from youtube_niche_mcp.db.schema import MIGRATIONS, Migration
from youtube_niche_mcp.db.status import integrity
from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import Decision, Observation, Outcome, timestamp
from youtube_niche_mcp.domain.states import EvidenceState


def test_frozen_v1_upgrade_and_new_schema(tmp_path):
    assert (
        MIGRATIONS[0].checksum == "df4ead10f9d64ecd7950b0c37717976e475bd2dd6e0a6ca1d047554509f12177"
    )
    with connect(tmp_path / "v1.sqlite3") as connection:
        assert migrate(connection, MIGRATIONS[:1]) == [1]
        old = tuple(applied_migrations(connection)[0])
        assert migrate(connection) == [2, 3, 4, 5, 6, 7]
        assert tuple(applied_migrations(connection)[0]) == old
        assert integrity(connection)["ok"]
        assert (
            connection.execute(
                "SELECT value FROM app_metadata WHERE key='schema_scope'"
            ).fetchone()[0]
            == "phase_5_qualitative"
        )


def test_failed_upgrade_preserves_existing_v1(tmp_path):
    broken = Migration(2, "broken", (*MIGRATIONS[1].statements, "INVALID SQL"))
    with connect(tmp_path / "v1.sqlite3") as connection:
        migrate(connection, MIGRATIONS[:1])
        with pytest.raises(sqlite3.OperationalError):
            migrate(connection, (MIGRATIONS[0], broken))
        assert [row["version"] for row in applied_migrations(connection)] == [1]
        assert not connection.execute("SELECT 1 FROM sqlite_master WHERE name='videos'").fetchone()
        assert integrity(connection)["ok"]


def test_two_captures_remain_and_duplicate_replay_is_idempotent(
    repository, observation_factory, now
):
    early = observation_factory(100, at=now - timedelta(hours=1), title="Old")
    later = observation_factory(200, title="New")
    first = repository.append(early)
    second = repository.append(later)
    assert repository.append(early) == first
    rows = repository.observations("video", "aaaaaaaaaaa", now)
    assert [row["view_count"] for row in rows] == [200, 100]
    assert rows[1]["observation_id"] == first
    assert rows[0]["observation_id"] == second
    assert (
        json.loads(
            repository.latest("video", "aaaaaaaaaaa", early.provenance.observed_at)["metadata_json"]
        )["title"]
        == "Old"
    )
    changed = observation_factory(999, at=early.provenance.observed_at, title="Old")
    with pytest.raises(ValueError, match="replay differs"):
        repository.append(changed)
    with pytest.raises(sqlite3.IntegrityError, match="Append-only"):
        repository.connection.execute(
            "UPDATE video_observations SET view_count=999 WHERE observation_id=?", (first,)
        )
    assert repository.latest("video", "aaaaaaaaaaa", now)["view_count"] == 200


def test_known_at_time_observed_available_first_seen_and_metadata(
    repository, observation_factory, now
):
    observed = now - timedelta(days=1)
    early = observation_factory(100, at=observed, available=now, title="Known later")
    repository.append(early)
    assert repository.latest("video", "aaaaaaaaaaa", now - timedelta(microseconds=1)) is None
    assert not repository.existed("video", "aaaaaaaaaaa", observed)
    assert repository.existed("video", "aaaaaaaaaaa", now)
    assert repository.latest("video", "aaaaaaaaaaa", now)["view_count"] == 100
    repository.append(observation_factory(200, at=now + timedelta(hours=1), title="Future title"))
    assert (
        json.loads(repository.latest("video", "aaaaaaaaaaa", now)["metadata_json"])["title"]
        == "Known later"
    )
    local_t = now.astimezone(timezone(timedelta(hours=5)))
    assert repository.latest("video", "aaaaaaaaaaa", local_t)["view_count"] == 100
    assert timestamp(local_t) == timestamp(now)


def test_decision_time_and_availability_never_leak(repository, now):
    decision = Decision(
        entity_kind="video",
        entity_id="aaaaaaaaaaa",
        decision_type="external_annotation",
        state=EvidenceState.CLASSIFICATION_UNKNOWN,
        source="human_annotation",
        reason="No automated classification",
        rule_version="annotation-v1",
        observed_at=now - timedelta(days=1),
        available_at=now,
        decided_at=now + timedelta(hours=1),
    )
    repository.record_decision(decision)
    assert repository.latest_decision("video", "aaaaaaaaaaa", "external_annotation", now) is None
    boundary = now + timedelta(hours=1)
    assert (
        repository.latest_decision("video", "aaaaaaaaaaa", "external_annotation", boundary)["state"]
        == "classification_unknown"
    )
    assert repository.record_decision(decision)
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM eligibility_decisions").fetchone()[0]
        == 1
    )


def test_current_subscribers_cannot_backfill_publication(repository, observation_factory, now):
    channel_id = "UC" + "a" * 22
    publication = now - timedelta(days=10)
    repository.append(observation_factory(20000, kind="channel"))
    unknown = repository.publication_size(channel_id, publication)
    assert unknown.state == EvidenceState.INSUFFICIENT_HISTORY
    assert unknown.value is None
    repository.append(
        observation_factory(1000, kind="channel", at=publication - timedelta(hours=1))
    )
    assert repository.publication_size(channel_id, publication).value == 1000
    assert (
        repository.publication_size(channel_id, publication, tolerance=timedelta(minutes=30)).value
        is None
    )
    with pytest.raises(ValueError):
        repository.publication_size(channel_id, publication, tolerance=timedelta(days=90))


def test_source_conflict_preserves_both_and_conservative_preference(
    repository, observation_factory, now
):
    published = now - timedelta(days=5)
    official = repository.append(observation_factory(100, publication=published))
    provider = repository.append(
        observation_factory(
            100,
            publication=published - timedelta(days=2),
            source="provider:fixture",
            capture_id="provider",
        )
    )
    cid = repository.conflict(
        "video", "aaaaaaaaaaa", "publication_at", official, provider, detected_at=now
    )
    assert (
        repository.conflict(
            "video", "aaaaaaaaaaa", "publication_at", official, provider, detected_at=now
        )
        == cid
    )
    assert repository.conflicts("video", "aaaaaaaaaaa", now - timedelta(seconds=1)) == []
    assert (
        repository.conflicts("video", "aaaaaaaaaaa", now)[0]["preferred_source"]
        == "youtube:videos.list"
    )
    assert len(repository.observations("video", "aaaaaaaaaaa", now)) == 2
    assert (
        repository.latest("video", "aaaaaaaaaaa", now, source="youtube:videos.list")[
            "observation_id"
        ]
        == official
    )
    with pytest.raises(ValueError, match="do not conflict"):
        repository.conflict(
            "video", "aaaaaaaaaaa", "view_count", official, provider, detected_at=now
        )


def test_expired_evidence_excluded_then_explicitly_purged(repository, observation_factory, now):
    repository.append(observation_factory(100, at=now - timedelta(days=30)))
    repository.append(observation_factory(200))
    assert [r["view_count"] for r in repository.observations("video", "aaaaaaaaaaa", now)] == [200]
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM video_observations").fetchone()[0] == 2
    )
    deleted = repository.purge_expired()
    assert deleted["source_records"] == 1
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM video_observations").fetchone()[0] == 1
    )
    assert integrity(repository.connection)["ok"]


def test_capture_atomicity_with_outer_failure(repository, observation_factory):
    with pytest.raises(RuntimeError, match="target insert failed"), atomic(repository.connection):
        repository.append(observation_factory())
        raise RuntimeError("target insert failed")
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM video_observations").fetchone()[0] == 0
    )
    assert repository.connection.execute("SELECT COUNT(*) FROM source_records").fetchone()[0] == 0
    assert repository.connection.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 0


def test_illegal_mutated_capture_and_unknown_zero_rejected(repository, observation_factory):
    observation = observation_factory()
    changed = observation.model_copy(update={"outcome": Outcome.API_MISSING})
    with pytest.raises(ValueError, match="fabricated"):
        repository.append(changed)
    with pytest.raises(ValueError):
        Observation.model_validate({**observation.model_dump(), "entity_id": "bad"})
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM video_observations").fetchone()[0] == 0
    )


@pytest.mark.parametrize("outcome", list(Outcome))
def test_outcome_vocabulary_is_mapped(outcome):
    assert isinstance(outcome.evidence_state, EvidenceState)


def test_required_indexes_exist(repository):
    indexes = {
        row[0]
        for row in repository.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
    }
    assert {
        "channel_time",
        "video_time",
        "channels_first_seen",
        "videos_first_seen",
        "discovery_rank",
        "conflict_subject",
        "decision_subject",
        "source_expiry",
    } <= indexes
