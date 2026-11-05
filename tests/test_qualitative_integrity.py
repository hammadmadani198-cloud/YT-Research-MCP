"""Real SQLite persistence, official-count safety, policy expiry and provider firewall."""

import json
import sqlite3
from datetime import timedelta
from decimal import Decimal

import pytest
from phase3_helpers import seed
from phase5_helpers import pilot, premise, production, review, source
from test_nexlev_evidence import ingest, record

from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.analysis.service import AnalysisService
from youtube_niche_mcp.cli import main
from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import migrate
from youtube_niche_mcp.db.schema import MIGRATIONS, Migration
from youtube_niche_mcp.db.status import integrity
from youtube_niche_mcp.domain.evidence import NumericEvidence
from youtube_niche_mcp.qualitative.models import Annotation, Material, QualitativeOptions
from youtube_niche_mcp.qualitative.service import QualitativeService, sample_manifest


def setup(repository, observation_factory, now):
    vd, _, ids, _ = seed(
        repository, observation_factory, now, [[1000]], topics=["a"], publication_days=40
    )
    return vd, ids, QualitativeOptions(cutoff=now, age_days=30, tolerance_seconds=0, goal=1000)


def result(bundle, fid):
    return next(m for m in bundle.metrics if m.formula_id == fid)


def test_persist_replay_and_separate_axes(repository, observation_factory, now):
    vd, _, opt = setup(repository, observation_factory, now)
    service = QualitativeService(repository)
    for a in (source(now), premise(now, "x"), production(now)):
        service.annotate(a)
    opt = opt.model_copy(
        update={
            "annotation_ids": ("source", "premise-x", "production"),
            "generated_candidate_ids": ("x",),
            "pilot": pilot(now),
        }
    )
    bundle = service.analyze(vd, opt)
    assert result(bundle, "F15").value == 1 and result(bundle, "F16").value == 12
    assert result(bundle, "F23").value == 400 and len(bundle.metrics) == 13
    assert service.analyze(vd, opt) == bundle and service.inspect(bundle.run.run_id) == bundle
    assert bundle.run.formula_version == "phase5-v1"
    assert not {"F17", "F18"} & {m.formula_id for m in bundle.metrics}


def test_revocation_invalidates_transitive_reviews_and_runs(repository, observation_factory, now):
    vd, _, opt = setup(repository, observation_factory, now)
    service = QualitativeService(repository)
    oid = repository.connection.execute(
        "SELECT observation_id FROM video_observations LIMIT 1"
    ).fetchone()[0]
    expiry = now + timedelta(days=5)
    a = source(now).model_copy(update={"input_ids": (oid,), "expires_at": expiry})
    service.annotate(a)
    service.annotate(premise(now, "x").model_copy(update={"expires_at": expiry}))
    opt = opt.model_copy(
        update={"annotation_ids": ("source", "premise-x"), "generated_candidate_ids": ("x",)}
    )
    bundle = service.analyze(vd, opt)
    repository.connection.execute("DELETE FROM source_records")
    repository.connection.execute("DELETE FROM retention_permissions")
    with pytest.raises(AnalysisUnavailable):
        service.inspect(bundle.run.run_id)
    with pytest.raises(AnalysisUnavailable):
        service.reviews.read_many(("premise-x",), now)


def test_annotation_cannot_outlive_source(repository, observation_factory, now):
    setup(repository, observation_factory, now)
    oid = repository.connection.execute(
        "SELECT observation_id FROM video_observations LIMIT 1"
    ).fetchone()[0]
    with pytest.raises(ValueError, match="outlive"):
        QualitativeService(repository).annotate(
            source(now).model_copy(
                update={"input_ids": (oid,), "expires_at": now + timedelta(days=1000)}
            )
        )


def test_review_immutability(repository, now):
    service = QualitativeService(repository)
    a = source(now)
    service.annotate(a)
    assert service.annotate(a) == a
    with pytest.raises(ValueError, match="Immutable"):
        service.annotate(a.model_copy(update={"rationale": "Changed review requires new ID"}))
    with pytest.raises(sqlite3.IntegrityError, match="Append-only"):
        repository.connection.execute("UPDATE qualitative_annotations SET input_hash='changed'")


def test_permission_verified_later_cannot_enter_past_review(repository, now):
    from youtube_niche_mcp.history.retention import RetentionRepository, StoragePermission

    pid = RetentionRepository(repository).record_permission(
        StoragePermission(
            source="nexlev.reviewed_text",
            approval_reference="Synthetic scoped contract review",
            verified_by="test administrator",
            verified_at=now,
            expires_at=now + timedelta(days=30),
            statistical_months=1,
        )
    )
    annotation = source(now - timedelta(days=1)).model_copy(update={"input_ids": (pid,)})
    with pytest.raises(ValueError, match="Future source"):
        QualitativeService(repository).annotate(annotation)


def test_expiry_blocks_inspection_and_explicit_purge(repository, observation_factory, now):
    vd, _, opt = setup(repository, observation_factory, now)
    service = QualitativeService(repository)
    service.annotate(source(now))
    bundle = service.analyze(vd, opt.model_copy(update={"annotation_ids": ("source",)}))
    repository.clock = lambda: now + timedelta(days=11)
    with pytest.raises(AnalysisUnavailable):
        service.inspect(bundle.run.run_id)
    deleted = repository.purge_expired()
    assert deleted["qualitative_annotations"] == 1 and deleted["analysis_runs"] == 1


def test_future_annotation_cannot_backfill_old_cutoff(repository, observation_factory, now):
    vd, _, opt = setup(repository, observation_factory, now)
    service = QualitativeService(repository)
    service.annotate(source(now))
    with pytest.raises(ValueError, match="Future"):
        service.analyze(
            vd,
            opt.model_copy(
                update={"cutoff": now - timedelta(days=1), "annotation_ids": ("source",)}
            ),
        )


def test_boundary_mismatch(repository, observation_factory, now):
    vd, _, opt = setup(repository, observation_factory, now)
    a = source(now)
    a = a.model_copy(update={"boundary": a.boundary.model_copy(update={"boundary_id": "other"})})
    service = QualitativeService(repository)
    service.annotate(a)
    with pytest.raises(ValueError, match="boundary"):
        service.analyze(vd, opt.model_copy(update={"annotation_ids": (a.annotation_id,)}))


def test_taxonomy_unknown_or_wrong_level_rejected(repository, observation_factory, now):
    setup(repository, observation_factory, now)
    service = QualitativeService(repository)
    service.annotate(source(now))
    for nodes in [("unknown",), ("niche",)]:
        with pytest.raises(ValueError, match="taxonomy"):
            service.annotate(premise(now, "x", family_node_ids=nodes))


def test_prior_analytics_read_only(repository, observation_factory, now):
    vd, _, _, oldopt = seed(repository, observation_factory, now, [[1000]])
    prior = AnalysisService(repository).analyze(vd, oldopt)
    opt = QualitativeOptions(
        cutoff=now,
        age_days=30,
        tolerance_seconds=0,
        goal=1000,
        analysis_run_ids=(prior.run.run_id,),
    )
    new = QualitativeService(repository).analyze(vd, opt)
    assert new.run.options.analysis_run_ids == (prior.run.run_id,)
    assert AnalysisService(repository).inspect(prior.run.run_id) == prior
    assert result(new, "content_gaps").state == "unknown"


@pytest.mark.parametrize(
    "field,value",
    [
        ("rpm", 7),
        ("monthly_revenue", 500),
        ("monetized", True),
        ("quality", 9),
        ("outlier_score", 10),
        ("vph", 100),
    ],
)
def test_provider_financial_quality_firewall(repository, now, field, value):
    repo = NexLevRepository(repository)
    ingest(repo, "blocked", record(now, **{field: value}))
    eid = repository.connection.execute("SELECT evidence_id FROM provider_evidence").fetchone()[0]
    a = review(
        now,
        dict(
            kind="relation",
            left_candidate_id="a",
            right_candidate_id="b",
            relation="near_duplicate",
            provider_evidence_ids=(eid,),
        ),
        "relation",
        source_type="provider",
        input_ids=(eid,),
        expires_at=now + timedelta(hours=1),
    )
    with pytest.raises(ValueError, match="forbidden"):
        QualitativeService(repository).annotate(a)


def test_provider_similarity_auxiliary_not_canonical(repository, now):
    ingest(NexLevRepository(repository), "similar", record(now, semantic_similarity=0.99))
    eid = repository.connection.execute("SELECT evidence_id FROM provider_evidence").fetchone()[0]
    a = review(
        now,
        dict(
            kind="relation",
            left_candidate_id="a",
            right_candidate_id="b",
            relation="near_duplicate",
            provider_evidence_ids=(eid,),
        ),
        source_type="provider",
        input_ids=(eid,),
        expires_at=now + timedelta(hours=1),
    )
    QualitativeService(repository).annotate(a)
    from youtube_niche_mcp.qualitative.dimensions import idea_feasibility

    r = idea_feasibility([source(now), premise(now, "a"), premise(now, "b"), a], ["a", "b"])
    assert r["validated_distinct_count"] == 2 and r["provider_model_relation_ids_auxiliary"] == [
        a.annotation_id
    ]


@pytest.mark.parametrize("kind", ["comment", "transcript", "thumbnail", "title"])
def test_model_text_media_requires_permission(now, kind):
    with pytest.raises(ValueError, match="permission"):
        review(
            now,
            dict(kind="packaging", video_id="x"),
            source_type="model",
            model_version="model-v1",
            prompt_version="prompt-v1",
            materials=(
                Material(
                    material_id="material-review", kind=kind, expires_at=now + timedelta(days=10)
                ),
            ),
        )


@pytest.mark.parametrize("field", ["transcript_metadata", "comment_metadata"])
def test_restricted_provider_text_cannot_be_relabelled_independent(repository, now, field):
    ingest(
        NexLevRepository(repository),
        "restricted",
        record(
            now,
            **{
                field: {"available": True, "retention_state": "contract_review_required"},
            },
        ),
    )
    eid = repository.connection.execute("SELECT evidence_id FROM provider_evidence").fetchone()[0]
    annotation = review(
        now,
        dict(
            kind="faceless",
            checked_paths=("voiceover",),
            central_host_required=False,
            field_footage_required=False,
            expert_interview_required=False,
        ),
        source_type="provider",
        input_ids=(eid,),
        expires_at=now + timedelta(minutes=30),
    )
    with pytest.raises(ValueError, match="contract review"):
        QualitativeService(repository).annotate(annotation)


def test_model_review_needs_model_and_prompt(now):
    with pytest.raises(ValueError, match="model and prompt"):
        review(now, dict(kind="packaging", video_id="x"), source_type="model")


@pytest.mark.parametrize(
    "private",
    [
        "ctr",
        "retention",
        "rpm",
        "revenue",
        "sentiment_percentage",
        "safe_clip_seconds",
        "raw_transcript",
        "raw_comment",
        "allegation",
    ],
)
def test_unapproved_fields_rejected(now, private):
    a = source(now).model_dump(mode="json")
    a["payload"][private] = 90
    with pytest.raises(ValueError):
        Annotation.model_validate(a)


def test_policy_version_changes_create_new_review_and_run(repository, observation_factory, now):
    vd, _, opt = setup(repository, observation_factory, now)
    service = QualitativeService(repository)
    p = dict(
        kind="policy",
        policy_url="https://support.google.com/youtube/answer/1311392?hl=en",
        policy_version="fixture-1",
        retrieved_at=now,
        refresh_by=now + timedelta(days=10),
        applicable_scope="Synthetic production method review",
        review_flags=("mass_produced",),
    )
    service.annotate(review(now, p, "policy-1"))
    first = service.analyze(vd, opt.model_copy(update={"annotation_ids": ("policy-1",)}))
    p["policy_version"] = "fixture-2"
    p["review_flags"] = ("reused_content",)
    service.annotate(review(now, p, "policy-2"))
    second = service.analyze(vd, opt.model_copy(update={"annotation_ids": ("policy-2",)}))
    assert first.run.run_id != second.run.run_id
    assert result(first, "rights_legal").state == "unknown"
    repository.clock = lambda: now + timedelta(days=11)
    with pytest.raises(AnalysisUnavailable):
        service.inspect(first.run.run_id)


def test_policy_cannot_outlive_refresh(now):
    with pytest.raises(ValueError, match="refresh"):
        review(
            now,
            dict(
                kind="policy",
                policy_url="https://support.google.com/youtube/answer/1311392?hl=en",
                policy_version="fixture",
                retrieved_at=now,
                refresh_by=now + timedelta(days=1),
                applicable_scope="Fixture",
                review_flags=(),
            ),
        )


@pytest.mark.parametrize("count,budget", [(1, 1), (20, 5), (500, 100)])
def test_bounded_deterministic_sampling(now, count, budget):
    ids = [str(i) for i in range(count)]
    a = sample_manifest(ids, budget, "seed", now)
    b = sample_manifest(list(reversed(ids)), budget, "seed", now)
    assert a == b and len(a.sample_ids) == min(count, budget)
    assert set(a.sample_ids) <= set(ids)


def test_sample_result_retains_manifest(repository, observation_factory, now):
    vd, _, opt = setup(repository, observation_factory, now)
    service = QualitativeService(repository)
    for i in range(5):
        service.annotate(source(now, str(i)))
    bundle = service.analyze(
        vd,
        opt.model_copy(
            update={"annotation_ids": tuple(str(i) for i in range(5)), "review_budget": 2}
        ),
    )
    m = result(bundle, "source_to_story")
    assert m.details["finding"]["coverage"]["sample_size"] == 2 and m.excluded == 3
    assert len(m.details["sample_manifest"]["population_ids"]) == 5


@pytest.mark.parametrize("version", range(6))
def test_clean_and_all_prior_migrations_to_v6(tmp_path, version):
    with connect(tmp_path / "upgrade.sqlite3") as c:
        if version:
            migrate(c, MIGRATIONS[:version])
        assert (
            migrate(c, MIGRATIONS[:6]) == list(range(version + 1, 7))
            and migrate(c, MIGRATIONS[:6]) == []
        )
        assert len(c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()) == 35
        assert integrity(c)["ok"]


def test_v6_failure_rolls_back_preserves_frozen_v5(tmp_path):
    with connect(tmp_path / "rollback.sqlite3") as c:
        migrate(c, MIGRATIONS[:5])
        broken = Migration(6, "broken", (*MIGRATIONS[5].statements, "INVALID SQL"))
        with pytest.raises(sqlite3.OperationalError):
            migrate(c, (*MIGRATIONS[:5], broken))
        assert not c.execute(
            "SELECT name FROM sqlite_master WHERE name='qualitative_annotations'"
        ).fetchone()
        assert migrate(c, MIGRATIONS[:6]) == [6] and integrity(c)["ok"]


def test_cli_qualitative_and_annotation(
    repository, observation_factory, now, tmp_path, capsys, monkeypatch
):
    # Synthetic reviews use an October clock; CLI must use the same clock in this test.
    from youtube_niche_mcp.history import repository as history_module

    original_class = history_module.HistoryRepository

    class FixtureClockRepository(original_class):
        def __init__(self, connection, *args, **kwargs):
            kwargs.setdefault("clock", lambda: now)
            super().__init__(connection, *args, **kwargs)

    monkeypatch.setattr(history_module, "HistoryRepository", FixtureClockRepository)
    vd, _, opt = setup(repository, observation_factory, now)
    repository.connection.commit()
    db = repository.connection.execute("PRAGMA database_list").fetchone()[2]
    ap = tmp_path / "annotation.json"
    ap.write_text(source(now).model_dump_json(), encoding="utf-8")
    assert main(["--db", db, "analysis", "annotate", "--input", str(ap)]) == 0
    assert json.loads(capsys.readouterr().out)["annotation_id"] == "source"
    fp = tmp_path / "options.json"
    fp.write_text(
        opt.model_copy(update={"annotation_ids": ("source",)}).model_dump_json(), encoding="utf-8"
    )
    assert main(["--db", db, "analysis", "qualitative", "--cohort", vd, "--options", str(fp)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] and len(payload["metrics"]) == 13


@pytest.mark.parametrize(
    "likes,comments,views", [(10, 5, 1000), (None, 5, 1000), (10, None, 1000), (0, 0, 0)]
)
def test_F14_same_capture_counts(repository, observation_factory, now, likes, comments, views):
    def counts_factory(value, **kwargs):
        obs = observation_factory(value, **kwargs)
        if value == views:
            metrics = dict(obs.metrics)
            for name, count in (("like_count", likes), ("comment_count", comments)):
                if count is not None:
                    metrics[name] = NumericEvidence(
                        state="available",
                        value=count,
                        reason="Synthetic public count",
                        provenance=obs.provenance,
                    )
            obs = obs.model_copy(update={"metrics": metrics})
        return obs

    vd, _, _, _ = seed(repository, counts_factory, now, [[views]], publication_days=40)
    opt = QualitativeOptions(cutoff=now, age_days=30, tolerance_seconds=0, goal=1000)
    m = result(QualitativeService(repository).analyze(vd, opt), "F14")
    row = m.details["videos"][0]
    assert row["denominator_views"] == views and row["likes_numerator"] == likes
    assert row["likes_per_1000_views"] == (
        str(Decimal(likes)) if likes is not None and views else None
    )
    assert row["comments_per_1000_views"] == (
        str(Decimal(comments)) if comments is not None and views else None
    )


def test_F14_age_mismatch_never_backfills_current(repository, observation_factory, now):
    vd, _, opt = setup(repository, observation_factory, now)
    m = result(
        QualitativeService(repository).analyze(vd, opt.model_copy(update={"age_days": 3})), "F14"
    )
    assert m.details["videos"][0]["denominator_views"] is None and m.state == "unknown"


@pytest.mark.parametrize("availability", ["available", "disabled", "deleted", "unknown"])
def test_F14_comment_theme_provenance_and_disabled(
    repository, observation_factory, now, availability
):
    vd, ids, opt = setup(repository, observation_factory, now)
    a = review(
        now,
        dict(
            kind="comment_theme",
            video_id=ids[0],
            theme="question",
            route="public manual review",
            order="top",
            pages=1,
            sample_size=20,
            retrieved_at=now,
            relationship="mixed",
            availability=availability,
            source="Synthetic comment sample",
        ),
        "comments",
    )
    service = QualitativeService(repository)
    service.annotate(a)
    m = result(service.analyze(vd, opt.model_copy(update={"annotation_ids": ("comments",)})), "F14")
    assert m.details["videos"][0]["comment_availability"] == availability
    assert m.details["comment_themes"][0]["sample_size"] == 20
