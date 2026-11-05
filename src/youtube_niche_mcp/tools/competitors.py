"""Channel-scoped descriptors; niche-level reviews stay labeled separate context."""

import json

from youtube_niche_mcp.analysis.numerics import json_numbers
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.models import Subject
from youtube_niche_mcp.eligibility.rules import classify
from youtube_niche_mcp.tools.metadata import declared_country
from youtube_niche_mcp.tools.schemas import CompetitorRequest, PublicResult
from youtube_niche_mcp.tools.serialization import page, project
from youtube_niche_mcp.tools.views import provider_context


def analyze(engine, request, *, context=None):
    sid, at = request.channel_id, engine.history.clock()
    subject = Subject(entity_kind="channel", entity_id=sid)
    if request.research_id and context is None:
        context = engine.context(request.research_id)
    capture = engine.history.latest("channel", sid, at, source="youtube:channels.list")
    statistics = {
        "state": "unavailable",
        "subscriber_count": None,
        "view_count": None,
        "video_count": None,
    }
    metadata = {}
    provenance = {"channel_id": sid}
    if capture and capture["source"].startswith("youtube:"):
        metadata = json.loads(capture["metadata_json"])
        statistics = {
            "state": capture["outcome"],
            "subscriber_count": None
            if capture["subscriber_hidden"]
            else capture["subscriber_count"],
            "subscriber_hidden": capture["subscriber_hidden"],
            "view_count": capture["view_count"],
            "video_count": capture["video_count"],
            "observed_at": capture["observed_at"],
            "source": capture["source"],
            "evidence": project(json.loads(capture["evidence_json"])),
        }
        provenance["observation_id"] = capture["observation_id"]
    eligibility = {}
    for field, rule in (
        ("faceless", "faceless_v1"),
        ("spoken_language", "spoken_language_v1"),
        ("subscriber_count", "current_small_v1_50k"),
    ):
        claims = engine.eligibility.claims(subject, at, field)
        known = engine.eligibility.latest(subject, rule, at)
        d = known[1] if known else classify(subject, rule, claims, decided_at=at)
        eligibility[field] = {
            "state": d.state.value,
            "label": d.label,
            "evidence_ids": list(d.evidence_ids),
        }
    membership_rows = engine.c.execute(
        (
            "SELECT DISTINCT taxonomy_version FROM niche_memberships "
            "WHERE entity_kind='channel' AND entity_id=? LIMIT 21"
        ),
        (sid,),
    ).fetchall()
    memberships = [
        {
            "membership_id": mid,
            "node_id": m.node_id,
            "taxonomy_version": m.taxonomy_version,
            "state": m.state,
            "source": m.source,
        }
        for version in membership_rows[:20]
        for mid, m in engine.eligibility.memberships(subject, version[0], at)
    ]
    ownership = engine.eligibility.independence(sid, at)
    current_videos = engine.c.execute(
        "WITH ranked AS (SELECT o.video_id,o.metadata_json,o.observed_at,ROW_NUMBER() OVER "
        "(PARTITION BY o.video_id ORDER BY o.observed_at "
        "DESC,o.available_at DESC,o.observation_id) n "
        "FROM video_observations o JOIN source_records s USING(source_id) WHERE o.observed_at<=? "
        "AND o.available_at<=? AND s.expires_at>? AND s.source LIKE 'youtube:%') "
        "SELECT video_id,metadata_json,observed_at FROM ranked WHERE n=1 "
        "AND json_extract(metadata_json,'$.channel_id')=? ORDER BY video_id LIMIT 1001",
        (timestamp(at), timestamp(at), timestamp(at), sid),
    ).fetchall()
    uploads = [
        {
            "video_id": r[0],
            "publication_at": json.loads(r[1]).get("publication_at"),
            "observed_at": r[2],
        }
        for r in current_videos[:1000]
    ]
    data = {
        "channel_id": sid,
        "title": metadata.get("title"),
        "declared_country": declared_country(engine.history, sid),
        "current_public_statistics": statistics,
        "eligibility": eligibility,
        "niche_memberships": memberships[:40],
        "ownership": ownership,
        "ordinary_floor": {"state": "age_matched_research_unavailable", "value": None},
        "breakout_dependence": {"state": "channel_specific_metric_unavailable"},
        "followup_repeatability": {"state": "anchor_specific_history_unavailable"},
        "observed_uploads": {
            "count": len(uploads),
            "complete_catalog": False,
            "truncated": len(current_videos) > 1000,
            "chronology": sorted(uploads, key=lambda r: (r["publication_at"] or "", r["video_id"]))[
                :20
            ],
        },
        "upload_cadence": {
            "state": "complete_catalog_unavailable",
            "rate": None,
            "scope": "dated observed uploads only",
        },
        "topic_breadth": {"state": "unavailable"},
        "content_patterns": {"state": "unreviewed"},
        "packaging_patterns": {"state": "unreviewed"},
        "production_model": {"state": "channel_specific_review_unavailable"},
        "risk": {"state": "channel_specific_review_unavailable"},
        "history": {"state": "unavailable"},
        "provider_conflicts": [
            {
                "conflict_id": c["conflict_id"],
                "field": c["field"],
                "available_at": c["available_at"],
            }
            for c in engine.history.conflicts("channel", sid, at)
        ],
    }
    outcomes = []
    confidence = {"level": "unknown", "F18": None, "history_maturity": "unavailable"}
    if context:
        decision, base, metrics, frame = context
        scoped = [o for o in base.outcomes if o.channel_id == sid]
        member = next((m for m in frame.members if m.subject.entity_id == sid), None)
        data["in_researched_frame"] = member is not None
        if member:
            data["frozen_eligibility_state"] = member.state.value
        outcomes = [o.model_dump(mode="json", exclude={"reason"}) for o in scoped]
        floor = metrics.get("F5")
        floor_value = floor.details.get("channel_floors", {}).get(sid) if floor else None
        data["ordinary_floor"] = {
            "state": "available" if floor_value is not None else "insufficient_history",
            "value": json_numbers(floor_value),
            "unit": "views_q25",
            "age_days": base.run.options.age_days,
            "goal": base.run.options.goal,
            "analysis_run_id": base.run.run_id,
        }
        f7 = metrics.get("F7")
        anchor = f7.details.get("anchor_id") if f7 else None
        if anchor in {o.video_id for o in scoped}:
            data["followup_repeatability"] = project(f7.details)
        data["candidate_hits"] = [
            {"video_id": o.video_id, "absolute_reach": o.value, "state": "candidate_hit"}
            for o in scoped
            if o.state == "available" and o.value >= base.run.options.goal
        ][:20]
        data["breakout_dependence"] = {
            "state": "observed_frozen_frame_counts",
            "mature_videos": sum(o.state == "available" for o in scoped),
            "goal_hits": sum(
                o.state == "available" and o.value >= base.run.options.goal for o in scoped
            ),
            "pending": sum(o.state == "pending_maturity" for o in scoped),
            "unknown": sum(o.state not in {"available", "pending_maturity"} for o in scoped),
            "interpretation": "Descriptive counts, not a channel concentration formula or census.",
        }
        data["topic_breadth"] = {
            "topic_family_ids": sorted(
                {t for v in frame.videos if v.channel_id == sid for t in v.topic_families}
            ),
            "scope": "observed_frozen_memberships",
        }
        # Packaging reviews are video-scoped; all other production/risk reviews are boundary-scoped.
        from youtube_niche_mcp.qualitative.dimensions import packaging_patterns
        from youtube_niche_mcp.qualitative.repository import ReviewRepository

        aids = set()
        for rid in decision.run.options.qualitative_run_ids:
            q = engine.repository.read(rid)
            for metric in q.metrics:
                aids.update(metric.details.get("sample_manifest", {}).get("sample_ids", ()))
        annotations = ReviewRepository(engine.history).read_many(
            tuple(sorted(aids)), base.run.options.cutoff
        )
        packaging = [
            a
            for a in annotations
            if a.payload.kind == "packaging" and a.payload.video_id in {o.video_id for o in scoped}
        ]
        data["packaging_patterns"] = json_numbers(packaging_patterns(packaging))
        data["niche_context"] = {
            "research_id": decision.run.run_id,
            "recommendation_state": metrics["decision"].state,
            "F18": {
                k: v
                for k, v in metrics["F18"].details.items()
                if k
                in {
                    "confidence",
                    "specification_agreement",
                    "consistent_specifications",
                    "comparable_specifications",
                    "planned_specifications",
                    "assessment_scope",
                }
            },
            "production": {
                "state": metrics["F16"].state,
                "value": json_numbers(metrics["F16"].value),
                "unit": metrics["F16"].unit,
            }
            if "F16" in metrics
            else {"state": "unknown"},
            "risk_states": {
                f: metrics[f].state
                for f in ("rights_legal", "platform_policy", "factual_editorial")
                if f in metrics
            },
            "scope": (
                "niche-level context; not channel-specific cost, rights, confidence or success"
            ),
        }
        data["history"] = {
            "scope": "age_matched_scoped_outcomes",
            "analysis_run_id": base.run.run_id,
            "mature": sum(o.state == "available" for o in scoped),
            "pending": sum(o.state == "pending_maturity" for o in scoped),
            "unknown": sum(o.state not in {"available", "pending_maturity"} for o in scoped),
        }
        provenance["decision_run_id"] = decision.run.run_id
        provenance["analysis_run_id"] = base.run.run_id
    data["provider_context"] = provider_context(
        engine,
        {("channel", sid)},
        {"spoken_language", "faceless", "outlier_score", "geography"},
        at,
    )
    outcomes, cursor = page(outcomes, request, ["competitor", sid, request.research_id])
    return PublicResult(
        state="available"
        if capture
        or memberships
        or outcomes
        or any(v["state"] != "unknown" for v in eligibility.values())
        else "insufficient_evidence",
        summary="Channel-scoped public descriptors with separately labeled niche context.",
        research_id=request.research_id,
        reused_run=bool(context),
        data=data,
        evidence=outcomes,
        confidence=confidence,
        provenance=provenance,
        next_cursor=cursor,
        warnings=[
            "Unknown ownership is not independence. Current size is not size at publication.",
            (
                "Scoped public uploads do not establish complete history, "
                "private analytics, actual costs or asset rights."
            ),
        ],
    )


def compare(engine, request):
    context = engine.context(request.research_id) if request.research_id else None
    rows = []
    for sid in request.channel_ids:
        result = analyze(
            engine,
            CompetitorRequest(channel_id=sid, research_id=request.research_id),
            context=context,
        )
        rows.append(
            {
                "state": result.state,
                "confidence": result.confidence,
                **{k: v for k, v in result.data.items() if k != "niche_context"},
            }
        )
    return PublicResult(
        state="available",
        summary="Descriptive comparison of channel-scoped public evidence.",
        research_id=request.research_id,
        evidence=rows,
        data={
            "winner": None,
            "scope": (
                "same frozen measurement context when supplied; current sizes"
                " remain separately dated"
            ),
        },
        warnings=[
            (
                "No objectively better creator is declared; private analytics"
                " and ownership remain unknown where unsupported."
            )
        ],
    )
