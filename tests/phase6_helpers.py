"""Synthetic retained decision inputs. Every public outcome uses the real Phase 3 resolver."""

import json
from datetime import timedelta
from decimal import Decimal

from phase3_helpers import frozen, metrics, seed
from phase4_helpers import discovery
from phase5_helpers import premise, production, review, source

from youtube_niche_mcp.analysis.service import AnalysisService
from youtube_niche_mcp.decision.models import (
    DecisionOptions,
    DecisionRubric,
    MetricRule,
    SensitivityPlan,
)
from youtube_niche_mcp.eligibility.models import Claim, CohortDefinition, CohortMember, Subject
from youtube_niche_mcp.eligibility.repository import EligibilityRepository
from youtube_niche_mcp.qualitative.models import QualitativeOptions
from youtube_niche_mcp.qualitative.service import QualitativeService


def clone_cohort(
    repository, cid, new_id, *, selected=None, boundary=None, changes=None, routes=False
):
    c = repository.connection
    definition = CohortDefinition.model_validate_json(
        c.execute(
            "SELECT definition_json FROM cohort_definitions WHERE cohort_id=?", (cid,)
        ).fetchone()[0]
    )
    definition = definition.model_copy(
        update={
            "cohort_id": new_id,
            **({"boundary": boundary} if boundary else {}),
            **(changes or {}),
        }
    )
    members = [
        CohortMember.model_validate_json(r[0])
        for r in c.execute(
            "SELECT member_json FROM cohort_memberships WHERE cohort_id=? ORDER BY entity_id",
            (cid,),
        )
    ]
    if selected is not None:
        members = [m for m in members if m.subject.entity_id in selected]
    if routes:
        from youtube_niche_mcp.eligibility.cohorts import CohortBuilder

        repo = CohortBuilder(EligibilityRepository(repository))
        members = [
            m.model_copy(
                update={"discovery_occurrences": repo.routes(m.subject, definition.known_at)}
            )
            for m in members
        ]
    frozen(c, definition, members)
    return new_id


def setup(
    repository,
    factory,
    now,
    *,
    values=None,
    complete=True,
    rights="low",
    hours=12,
    policy_flags=(),
    review_budget=100,
    known_groups=True,
    with_routes=True,
    official_span=None,
):
    values = values or [[12000] * 6, [15000] * 6, [16000] * 6]
    vd, cd, ids, ao = seed(
        repository, factory, now, values, topics=["a"] * len(values), known_groups=known_groups
    )
    freeze = now - timedelta(days=2)
    if with_routes:
        discovery(
            repository,
            "official",
            freeze,
            ids[:official_span],
            route="official_search",
            provider="youtube",
        )
        discovery(repository, "semantic", freeze, ids[:6], route="semantic", provider="nexlev")
        discovery(repository, "weak", freeze, ids[6:], route="suggested", provider="nexlev")
        vd = clone_cohort(repository, vd, "routed-videos", routes=True)
    e = EligibilityRepository(repository)
    if complete:
        channels = {
            json.loads(r[0])["subject"]["entity_id"]
            for r in repository.connection.execute(
                "SELECT member_json FROM cohort_memberships WHERE cohort_id=?", (cd,)
            )
        }
        for field, population, value, basis in (
            ("faceless", channels, True, "human_review"),
            ("continuity", channels, "continuous", "human_review"),
            ("spoken_language", set(ids), "en", "transcript_review"),
            ("live_status", set(ids), "ordinary_vod", "official_metadata"),
        ):
            for sid in sorted(population):
                e.append_claim(
                    Claim(
                        subject=Subject(
                            entity_kind="channel" if sid in channels else "video", entity_id=sid
                        ),
                        field=field,
                        value=value,
                        basis=basis,
                        source="synthetic independent review",
                        source_version="fixture-v1",
                        observed_at=freeze,
                        available_at=freeze,
                        reason="Synthetic complete scoped review",
                        complete_review=True,
                        data_origin="independent_annotation",
                        permission_state="permitted",
                    )
                )
    ao = ao.model_copy(update={"anchor_id": ids[0]})
    base = AnalysisService(repository).analyze(cd, ao, video_cohort_id=vd)
    qservice = QualitativeService(repository)
    annotations = [
        source(now),
        production(now, hours=hours, method="timed_pilot"),
        review(
            now,
            {
                "kind": "rights",
                "asset_id": "original diagrams",
                "asset_type": "original",
                "dependency": rights,
                "clearance": "verified",
                "license_reference": "creator owns diagrams",
            },
            "rights",
        ),
        review(
            now,
            {
                "kind": "policy",
                "policy_url": "https://support.google.com/youtube/answer/1311392?hl=en",
                "policy_version": "synthetic-v1",
                "retrieved_at": now,
                "refresh_by": now + timedelta(days=10),
                "applicable_scope": "synthetic scoped method",
                "review_flags": policy_flags,
            },
            "policy",
        ),
        review(
            now,
            {
                "kind": "factual",
                "domain": "documented_technical_history",
                "verification_burden": "low",
                "identifiable_entity": False,
                "allegation_verification_needed": False,
                "disputed_claims": False,
                "volatile": False,
                "correction_burden": "low",
                "source_annotation_ids": ["source"],
            },
            "factual",
        ),
    ]
    annotations.extend(premise(now, str(i)) for i in range(30))
    for a in annotations:
        qservice.annotate(a)
    qo = QualitativeOptions(
        cutoff=now,
        age_days=30,
        tolerance_seconds=0,
        goal=ao.goal,
        annotation_ids=tuple(a.annotation_id for a in annotations),
        generated_candidate_ids=tuple(str(i) for i in range(30)),
        review_budget=review_budget,
        analysis_run_ids=(base.run.run_id,),
    )
    q = qservice.analyze(cd, qo, video_cohort_id=vd)
    rules = tuple(
        MetricRule(
            formula_id=f,
            direction=d,
            threshold=Decimal(t),
            reference="Explicit synthetic research-goal rubric; not universal",
        )
        for f, d, t in (
            ("F3", "at_least", "0.5"),
            ("F5", "at_least", "10000"),
            ("F7", "at_least", "0.5"),
            ("F19", "at_least", "0.5"),
            ("F8", "at_least", "1"),
            ("F15", "at_least", "0.5"),
            ("F16", "at_most", "20"),
        )
    )
    opt = DecisionOptions(
        cutoff=now,
        age_days=30,
        tolerance_seconds=0,
        goal=ao.goal,
        base_run_id=base.run.run_id,
        qualitative_run_ids=(q.run.run_id,),
        rubric=DecisionRubric(version="synthetic-v1", rules=rules),
        sensitivity=SensitivityPlan(declared_at=now, mode="deep", max_runs=48),
    )
    return base, q, opt, metrics(base), ids


def result(bundle, fid):
    return next(m for m in bundle.metrics if m.formula_id == fid)


def options_json(options):
    return json.dumps(options.model_dump(mode="json"), indent=2)


def complete_history(metrics_by_id):
    """Pure synthesis fixture, deliberately not stored or represented as real measured history."""
    template = metrics_by_id["F3"]
    return {
        **metrics_by_id,
        **{
            fid: template.model_copy(
                update={"formula_id": fid, "formula_version": "phase4-v1", "state": "available"}
            )
            for fid in ("F10", "F11", "F12", "F13", "F20", "F21")
        },
    }
