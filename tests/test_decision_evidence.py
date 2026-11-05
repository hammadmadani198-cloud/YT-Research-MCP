"""R8 field conflicts, provider dependence, classification quality and review coverage."""

from datetime import timedelta

import pytest
from phase3_helpers import channel
from phase5_helpers import review
from phase6_helpers import result, setup
from test_nexlev_evidence import ingest, record

from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository
from youtube_niche_mcp.decision.service import DecisionService
from youtube_niche_mcp.domain.foundation import Metadata
from youtube_niche_mcp.eligibility.models import Claim, Subject
from youtube_niche_mcp.eligibility.repository import EligibilityRepository
from youtube_niche_mcp.qualitative.service import QualitativeService


def claim(repository, now, field, sid, value, basis="provider_label"):
    at = now - timedelta(days=2)
    return EligibilityRepository(repository).append_claim(
        Claim(
            subject=Subject(
                entity_kind="channel" if sid.startswith("UC") else "video", entity_id=sid
            ),
            field=field,
            value=value,
            basis=basis,
            source="Independent fixture record of provider output",
            source_version="provider-fixture-v1",
            observed_at=at,
            available_at=at,
            reason="Synthetic attributed external-label review; no confidence promotion",
            data_origin="independent_annotation",
            permission_state="permitted",
        )
    )


@pytest.mark.parametrize(
    "field,sid,value", [("faceless", channel(1), False), ("spoken_language", "v0000000001", "fr")]
)
def test_R8_provider_human_field_conflicts(repository, observation_factory, now, field, sid, value):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    claim(repository, now, field, sid, value)
    b = DecisionService(repository).analyze(opt)
    d = result(b, "decision").details
    classification = d["evidence"]["classifications"][field]
    assert sid in classification["conflicted_ids"]
    assert any(c["field"] == field for c in d["evidence"]["conflicts"])
    assert result(b, "F18").state == "low"


def test_official_provider_publication_conflict_is_not_averaged(
    repository, observation_factory, now
):
    base, _, opt, _, ids = setup(repository, observation_factory, now)
    pub = base.outcomes[0].publication_at
    official = observation_factory(
        15000, entity_id=ids[0], publication=pub, at=now, capture_id="detail-official"
    ).model_copy(update={"metadata": Metadata(channel_id=channel(1), publication_at=pub)})
    provider = observation_factory(
        99999,
        entity_id=ids[0],
        source="provider:nexlev.details",
        publication=pub + timedelta(days=7),
        at=now,
        capture_id="detail-provider",
    ).model_copy(
        update={"metadata": Metadata(channel_id=channel(1), publication_at=pub + timedelta(days=7))}
    )
    oid = repository.append(official)
    pid = repository.append(provider)
    cid = repository.conflict("video", ids[0], "publication_at", oid, pid, detected_at=now)
    b = DecisionService(repository).analyze(opt)
    conflicts = result(b, "decision").details["evidence"]["conflicts"]
    assert any(
        c.get("conflict_id") == cid and c["preferred_source"] == "youtube:videos.list"
        for c in conflicts
    )
    assert result(b, "F18").state == "low"
    assert b.outcomes == base.outcomes


def test_financial_provider_conflicts_are_excluded(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    repo = NexLevRepository(repository)
    for i, v in enumerate((False, True)):
        ingest(
            repo,
            "monetization-" + str(i),
            record(now, "nexlev.monetization_claim", "channel", channel(1), monetized=v),
        )
    b = DecisionService(repository).analyze(opt)
    e = result(b, "decision").details["evidence"]
    assert e["ignored_financial_conflict_ids"]
    assert not e["conflicts"]
    assert all("rpm" not in a for a in result(b, "decision").details["axes"])


def test_provider_only_classification_loses_evidence(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now, complete=False)
    for i in range(1, 4):
        claim(repository, now, "faceless", channel(i), True)
    b = DecisionService(repository).analyze(opt)
    d = result(b, "decision").details
    item = d["evidence"]["classifications"]["faceless"]
    assert item["numerator"] == 3 and item["verified"] == 0
    assert result(b, "F18").state == "low"
    assert (
        next(r for r in d["sensitivity"] if r["label"] == "provider_classifications_removed")[
            "state"
        ]
        == "insufficient_without_provider"
    )


def test_unknown_ownership_remains_provisional(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now, known_groups=False)
    b = DecisionService(repository).analyze(opt)
    own = result(b, "decision").details["evidence"]["ownership"]
    assert len(own["unknown_relationship_channels"]) == 3 and not own["documented_groups"]
    row = next(
        r
        for r in result(b, "decision").details["sensitivity"]
        if r["label"] == "documented_groups_only"
    )
    assert row["comparable"] is False


def test_comment_captures_show_video_order_route_and_scope(repository, observation_factory, now):
    base, q, opt, _, ids = setup(repository, observation_factory, now)
    a = review(
        now,
        {
            "kind": "comment_theme",
            "video_id": ids[0],
            "theme": "question",
            "route": "commentThreads.list",
            "order": "time",
            "pages": 1,
            "sample_size": 1,
            "retrieved_at": now,
            "relationship": "top_level",
            "availability": "available",
            "source": "independent reviewed comment",
        },
        "comment",
    )
    service = QualitativeService(repository)
    service.annotate(a)
    qo = q.run.options.model_copy(
        update={"annotation_ids": (*q.run.options.annotation_ids, "comment")}
    )
    newer = service.analyze(base.run.cohort_id, qo, video_cohort_id=base.run.video_cohort_id)
    b = DecisionService(repository).analyze(
        opt.model_copy(update={"qualitative_run_ids": (newer.run.run_id,)})
    )
    comments = result(b, "decision").details["evidence"]["comments"]
    assert comments["videos"] == [ids[0]] and comments["reviews"][0]["sample_size"] == 1
    assert comments["reviews"][0]["order"] == "time" and "not summed" in comments["warning"]


@pytest.mark.parametrize(
    "missing", ["rights_legal", "platform_policy", "factual_editorial", "F16", "source_to_story"]
)
def test_missing_critical_risk_or_production_evidence_blocks_support(
    repository, observation_factory, now, missing
):
    from youtube_niche_mcp.decision.synthesis import assemble

    base, q, opt, mm, _ = setup(repository, observation_factory, now)
    mm.update({m.formula_id: m for m in q.metrics})
    mm.pop(missing)
    d = assemble(
        mm,
        opt.rubric,
        policy_state="policy_refresh_required" if missing == "platform_policy" else "fresh",
    )
    assert d["state"] not in {"supported", "supported_with_caveats"}


def test_provider_similarity_evidence_is_removed_from_qualitative_ablations(
    repository, observation_factory, now
):
    base, q, opt, _, ids = setup(repository, observation_factory, now)
    nr = NexLevRepository(repository)
    ingest(nr, "similarity", record(now, entity=ids[0], thumbnail_similarity="0.8"))
    eid = repository.connection.execute("SELECT evidence_id FROM provider_evidence").fetchone()[0]
    # Independent human review can record auxiliary T4 similarity; its permission still applies.
    a = review(
        now,
        {
            "kind": "packaging",
            "video_id": ids[0],
            "thumbnail_reviewed": True,
            "provider_similarity_ids": (eid,),
        },
        "similarity-review",
    )
    a = a.model_copy(update={"expires_at": now + timedelta(minutes=10)})
    service = QualitativeService(repository)
    service.annotate(a)
    qo = q.run.options.model_copy(
        update={"annotation_ids": (*q.run.options.annotation_ids, a.annotation_id)}
    )
    newer = service.analyze(base.run.cohort_id, qo, video_cohort_id=base.run.video_cohort_id)
    b = DecisionService(repository).analyze(
        opt.model_copy(update={"qualitative_run_ids": (newer.run.run_id,)})
    )
    row = next(
        r
        for r in result(b, "decision").details["sensitivity"]
        if r["label"] == "provider_similarity_removed"
    )
    assert row["state"] == "materially_changed"
    assert "differentiation" in row["changed_axes"]
    assert "similarity-review" in row["diagnostic"]["removed_annotation_ids"]


@pytest.mark.parametrize("basis", ["default_audio_language", "official_metadata"])
def test_audio_metadata_is_coverage_not_verified_speech(
    repository, observation_factory, now, basis
):
    from youtube_niche_mcp.decision.evidence import collect

    base, q, opt, _, ids = setup(repository, observation_factory, now, complete=False)
    for vid in ids:
        claim(repository, now, "spoken_language", vid, "en", basis=basis)
    frame = DecisionService(repository).repository.load(
        base.run.cohort_id, base.run.video_cohort_id, base.run.options
    )
    e = collect(repository, frame, base, (q,), opt)
    assert e["classifications"]["spoken_language"]["numerator"] == len(ids)
    assert e["classifications"]["spoken_language"]["verified"] == 0
