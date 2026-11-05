"""Synthetic attributed reviews; no empirical niche or platform claims."""

from datetime import timedelta
from decimal import Decimal

from youtube_niche_mcp.eligibility.models import Boundary
from youtube_niche_mcp.qualitative.models import (
    Annotation,
    Material,
    PilotProfile,
    PilotRelease,
    SampleManifest,
    Task,
)


def review(now, payload, aid="review", **changes):
    material_id = f"material-{aid}"
    body = dict(
        annotation_id=aid,
        boundary=Boundary(
            boundary_id="boundary-v1",
            taxonomy_version="topics-v1",
            node_ids=("niche",),
            classifier_version="topic-v1",
        ),
        source_type="human",
        reviewer="synthetic human",
        system_version="fixture-v1",
        rubric_version="phase5-v1",
        materials=(Material(material_id=material_id, kind="independent"),),
        sample=SampleManifest(
            population_ids=(material_id,),
            sample_ids=(material_id,),
            method="declared_review",
            seed="fixture",
            budget=100,
            cutoff=now,
            reason="Synthetic reviewed fixture",
        ),
        input_ids=(),
        available_at=now,
        decided_at=now,
        expires_at=now + timedelta(days=10),
        confidence="medium",
        rationale="Synthetic bounded review; no real platform claim",
        limitations=("Synthetic fixture only; sample scope",),
        payload=payload,
    )
    body.update(changes)
    return Annotation(**body)


def source(now, aid="source", **changes):
    body = dict(
        kind="source",
        source_reference="https://example.invalid/report",
        category="official_report",
        source_family=aid,
        checked=True,
        accessible=True,
        credible=True,
        primary=True,
        checked_at=now,
    )
    body.update(changes)
    return review(now, body, aid)


def premise(now, cid, **changes):
    body = dict(
        kind="premise",
        candidate_id=cid,
        subject=f"Entity {cid}",
        viewer_promise=f"Understand {cid}",
        mechanism="causal technical history",
        long_form_treatment=f"Documents and diagrams for {cid}",
        source_annotation_ids=("source",),
        production_path="Original diagrams with sourced narration",
        family_node_ids=("a",),
    )
    body.update(changes)
    return review(now, body, f"premise-{cid}")


def task(hours=12, cash=60, category="research", **changes):
    body = dict(
        category=category,
        hours=Decimal(hours),
        cash=Decimal(cash),
        required_skills=(),
        evidence_ids=(),
        reason="Declared synthetic task estimate",
        confidence="medium",
    )
    body.update(changes)
    return Task(**body)


def production(now, hours=12, cash=60, **changes):
    body = dict(
        kind="production",
        case_id="pilot",
        currency="USD",
        method="estimate",
        tasks=(task(hours, cash),),
        complete_task_inventory=True,
    )
    body.update(changes)
    return review(now, body, "production")


def pilot(now, count=5, **changes):
    body = dict(
        profile_id="creator-pilot",
        declared_at=now,
        expires_at=now + timedelta(days=90),
        currency="USD",
        setup_at=now,
        setup_cash=100,
        setup_hours=10,
        releases=tuple(
            PilotRelease(
                release_id=f"release-{i}",
                publication_at=now + timedelta(days=i * 7),
                tasks=(task(8, 60),),
            )
            for i in range(count)
        ),
        overhead_at=now,
        cash_limit=300,
        hour_limit=60,
        outcome_age_days=30,
        runway_until=now + timedelta(days=60),
    )
    body.update(changes)
    return PilotProfile(**body)
