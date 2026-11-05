import json
from datetime import timedelta

import pytest
from pydantic import ValidationError

from youtube_niche_mcp.eligibility.models import Claim, Subject
from youtube_niche_mcp.eligibility.repository import EligibilityRepository
from youtube_niche_mcp.history.retention import RetentionRepository, StoragePermission


def test_permission_gated_statistics_survive_text_and_cache_expiry(
    repository, observation_factory, now
):
    r = RetentionRepository(repository)
    permission = StoragePermission(
        source="youtube:videos.list",
        approval_reference="synthetic-fixture-acceptance",
        verified_by="fixture:admin",
        verified_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1100),
        statistical_months=36,
    )
    r.record_permission(permission)
    oid = repository.append(observation_factory(25, title="Refresh-limited title"))
    assert len(r.snapshots("video", "a" * 11, now)) == 1
    row = r.snapshots("video", "a" * 11, now)[0]
    assert "title" not in row["statistics_json"] and "Refresh-limited" not in row["statistics_json"]
    repository.connection.execute(
        "INSERT INTO live_cache VALUES('fixture','youtube:videos.list','{}',?,?,?)",
        (
            now.isoformat(),
            (now + timedelta(hours=1)).isoformat(),
            (now + timedelta(hours=1)).isoformat(),
        ),
    )
    repository.clock = lambda: now + timedelta(days=31)
    deleted = repository.purge_expired()
    assert deleted["live_cache"] == 1 and deleted["source_records"] == 1
    assert repository.latest("video", "a" * 11, now) is None
    stats = repository.statistical_snapshots("video", "a" * 11, now)
    assert stats[0]["observation_id"] == oid
    assert json.loads(stats[0]["evidence_json"])["view_count"]["value"] == 25
    assert "metadata_json" not in stats[0]
    assert repository.existed("video", "a" * 11, now)
    repository.clock = lambda: now + timedelta(days=1101)
    repository.purge_expired()
    assert not repository.statistical_snapshots("video", "a" * 11, now)


def test_no_acceptance_no_extended_archive_and_independent_annotations_not_blanket_deleted(
    repository, observation_factory, now
):
    repository.append(observation_factory(0))
    e = EligibilityRepository(repository)
    subject = Subject(entity_kind="video", entity_id="a" * 11)
    human = Claim(
        subject=subject,
        field="faceless",
        value="faceless",
        basis="human_review",
        source="human:review",
        source_version="v1",
        observed_at=now,
        available_at=now,
        complete_review=True,
        reason="Independent annotation",
        data_origin="independent_annotation",
        permission_state="permitted",
    )
    e.append_claim(human)
    did, _ = e.evaluate(subject, "faceless_v1", at=now)
    external = human.model_copy(
        update={
            "source": "provider:faceless",
            "data_origin": "provider_data",
            "permission_state": "policy_required",
            "basis": "provider_label",
        }
    )
    e.append_claim(external)
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM statistical_history").fetchone()[0] == 0
    )
    repository.clock = lambda: now + timedelta(days=31)
    repository.purge_expired()
    assert not repository.statistical_snapshots("video", subject.entity_id, now)
    assert len(e.claims(subject, now)) == 1
    assert e.latest(subject, "faceless_v1", now)[0] == did


def test_permission_source_and_availability_scopes_no_retroactive_rescue(
    repository, observation_factory, now
):
    r = RetentionRepository(repository)
    r.record_permission(
        StoragePermission(
            source="youtube:channels.list",
            approval_reference="fixture:other-source",
            verified_by="fixture:admin",
            verified_at=now,
            expires_at=now + timedelta(days=400),
            statistical_months=12,
        )
    )
    repository.append(observation_factory(5))
    assert not r.snapshots("video", "a" * 11, now)
    with pytest.raises(ValidationError):
        StoragePermission(
            source="fixture",
            approval_reference="fixture",
            verified_by="fixture",
            verified_at=now,
            expires_at=now + timedelta(days=400),
            statistical_months=37,
        )
    with pytest.raises(ValueError, match="future verification"):
        r.record_permission(
            StoragePermission(
                source="fixture",
                approval_reference="fixture",
                verified_by="fixture",
                verified_at=now + timedelta(days=1),
                expires_at=now + timedelta(days=400),
                statistical_months=12,
            )
        )


def test_cache_purge_does_not_expire_valid_history(repository, observation_factory, now):
    repository.append(observation_factory(0))
    repository.connection.execute(
        "INSERT INTO live_cache VALUES('fixture','fixture','{}',?,?,?)",
        (now.isoformat(), now.isoformat(), now.isoformat()),
    )
    repository.purge_expired()
    assert repository.latest("video", "a" * 11, now)["view_count"] == 0


def test_external_claim_cannot_self_grant_permission_or_long_retention(repository, now):
    e = EligibilityRepository(repository)
    c = Claim(
        subject=Subject(entity_kind="video", entity_id="a" * 11),
        field="faceless",
        value="faceless",
        basis="provider_label",
        source="provider:fixture",
        source_version="v1",
        observed_at=now,
        available_at=now,
        reason="Provider label",
        expires_at=now + timedelta(days=31),
    )
    with pytest.raises(ValueError, match="verified integration"):
        e.append_claim(c)
    with pytest.raises(ValidationError, match="separately verified"):
        Claim.model_validate({**c.model_dump(mode="json"), "permission_state": "permitted"})
