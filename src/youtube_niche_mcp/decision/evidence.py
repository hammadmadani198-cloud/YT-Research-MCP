"""Bulk retained evidence diagnostics. Coverage counts unique scoped subjects, not rows."""

import json
from collections import defaultdict

from youtube_niche_mcp.analysis.numerics import ratio
from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.models import Claim
from youtube_niche_mcp.qualitative.repository import ReviewRepository


def fraction(n, d, ids=()):
    return {"numerator": n, "denominator": d, "fraction": ratio(n, d), "subject_ids": sorted(ids)}


def collect(history, frame, base, bundles, options):
    now, cutoff, c = history.clock(), options.cutoff, history.connection
    videos = {v.video_id for v in frame.videos if v.membership.state.value != "excluded"}
    channels = {
        m.subject.entity_id
        for m in frame.members
        if m.subject.entity_kind == "channel" and m.state.value != "excluded"
    }
    if not channels:
        channels = {v.channel_id for v in frame.videos if v.video_id in videos and v.channel_id}
    subjects = videos | channels
    known = {o.video_id for o in base.outcomes if o.state == "available" and o.video_id in videos}
    observed_channels = {
        o.channel_id for o in base.outcomes if o.video_id in known and o.channel_id
    }
    topics = {
        v.video_id
        for v in frame.videos
        if v.video_id in videos and v.topic_families and not v.topic_conflict
    }
    dependencies = set()
    claims = defaultdict(list)
    for row in c.execute(
        (
            "SELECT * FROM classification_claims WHERE available_at<=? AND "
            "(expires_at IS NULL OR expires_at>?)"
        ),
        (timestamp(frame.video_freeze_at), timestamp(now)),
    ):
        if row["entity_id"] not in subjects:
            continue
        claim = Claim.model_validate_json(row["claim_json"])
        if claim.permission_state != "permitted" and row["evidence_id"] not in frame.input_ids:
            continue  # external unintegrated labels cannot supply a critical finding
        claims[(claim.subject.entity_id, claim.field)].append((row["evidence_id"], claim))
        dependencies.add(row["evidence_id"])
    classifications = {}
    for field in (
        "spoken_language",
        "faceless",
        "live_status",
        "niche_membership",
        "continuity",
        "creator_relation",
    ):
        population = channels if field in {"faceless", "continuity", "creator_relation"} else videos
        covered, verified, provider_only, conflicted = set(), set(), set(), set()
        provenance = []
        for sid in sorted(population):
            rows = claims.get((sid, field), [])
            if not rows:
                continue
            covered.add(sid)
            values = {json.dumps(cl.value, sort_keys=True) for _, cl in rows}
            if field == "niche_membership":
                by_node = defaultdict(set)
                for _, cl in rows:
                    if isinstance(cl.value, dict):
                        by_node[cl.value.get("node_id")].add(cl.value.get("state"))
                values = (
                    {"compatible_multi_label"}
                    if by_node and all(len(v) == 1 for v in by_node.values())
                    else values
                )
            if len(values) > 1:
                conflicted.add(sid)
            strong = any(
                cl.data_origin != "provider_data"
                and (
                    field != "spoken_language" or cl.basis in {"transcript_review", "human_review"}
                )
                and (
                    cl.basis
                    in {
                        "official_metadata",
                        "default_audio_language",
                        "public_disclosure",
                        "shared_company",
                        "explicit_network",
                        "transcript_review",
                    }
                    or (
                        cl.basis == "human_review"
                        and (field == "niche_membership" or cl.complete_review)
                    )
                )
                for _, cl in rows
            )
            if strong and len(values) == 1:
                verified.add(sid)
            if all(
                cl.data_origin == "provider_data" or cl.basis == "provider_label" for _, cl in rows
            ):
                provider_only.add(sid)
            provenance.extend(
                {
                    "entity_id": sid,
                    "evidence_id": eid,
                    "basis": cl.basis,
                    "origin": cl.data_origin,
                    "source": cl.source,
                    "version": cl.source_version,
                    "value": cl.value,
                    "complete_review": cl.complete_review,
                    "reviewed_video_ids": list(cl.reviewed_video_ids),
                }
                for eid, cl in rows
            )
        classifications[field] = {
            **fraction(len(covered), len(population), covered),
            "verified": len(verified),
            "verified_ids": sorted(verified),
            "provider_only_ids": sorted(provider_only),
            "conflicted_ids": sorted(conflicted),
            "provenance": provenance,
        }
    classifications["topic_family"] = {
        **fraction(len(topics), len(videos), topics),
        "verified": sum(
            bool(claims.get((vid, "niche_membership")))
            and any(
                cl.data_origin == "independent_annotation" and cl.basis == "human_review"
                for _, cl in claims[(vid, "niche_membership")]
            )
            for vid in topics
        ),
        "provider_only_ids": [
            vid
            for vid in topics
            if claims.get((vid, "niche_membership"))
            and all(
                cl.data_origin == "provider_data" or cl.basis == "provider_label"
                for _, cl in claims[(vid, "niche_membership")]
            )
        ],
        "conflicted_ids": [v.video_id for v in frame.videos if v.topic_conflict],
    }
    conflicts = []
    ignored_conflicts = []
    for row in c.execute(
        (
            "SELECT c.*,l.source_kind AS left_kind,r.source_kind AS "
            "right_kind FROM source_conflicts c JOIN source_records l ON "
            "l.source_id=c.left_source_id JOIN source_records r ON "
            "r.source_id=c.right_source_id WHERE c.available_at<=? AND "
            "l.expires_at>? AND r.expires_at>?"
        ),
        (timestamp(cutoff), timestamp(now), timestamp(now)),
    ):
        if row["entity_id"] not in subjects:
            continue
        if any(
            word in row["field"].lower()
            for word in ("revenue", "rpm", "monetiz", "proprietary", "outlier_score")
        ):
            ignored_conflicts.append(row["conflict_id"])
            continue
        conflicts.append(dict(row))
        dependencies.add(row["conflict_id"])
    for field, value in classifications.items():
        conflicts.extend(
            {"field": field, "entity_id": sid, "state": "classification_source_conflict"}
            for sid in value["conflicted_ids"]
        )
    review_ids = {
        i
        for b in bundles
        if b.run.formula_version == "phase5-v1"
        for m in b.metrics
        for i in m.details.get("annotation_confidences", {})
    }
    annotations = ReviewRepository(history).read_many(tuple(sorted(review_ids)), cutoff)
    policy_annotations = []
    unavailable_policy = []
    for aid in options.policy_snapshot_ids:
        try:
            rows = ReviewRepository(history).read_many((aid,), cutoff)
        except AnalysisUnavailable:
            unavailable_policy.append(aid)
            continue
        if not rows or rows[0].payload.kind != "policy":
            raise ValueError("Policy snapshot ID must reference a policy annotation")
        if rows[0].boundary != frame.boundary:
            raise ValueError("Policy review boundary mismatch")
        policy_annotations.extend(rows)
        dependencies.add(aid)
    policies = {
        a.annotation_id: a
        for a in (*annotations, *policy_annotations)
        if a.payload.kind == "policy"
    }
    receipts = [p for p in options.policy_clocks if p.expires_at > now]
    policy_rows = [
        {
            "snapshot_id": a.annotation_id,
            "retrieved_at": a.payload.retrieved_at.isoformat(),
            "refresh_by": a.payload.refresh_by.isoformat(),
            "age_seconds": (cutoff - a.payload.retrieved_at).total_seconds(),
            "state": "fresh" if a.payload.refresh_by > cutoff else "policy_refresh_required",
            "substantive_evidence": True,
        }
        for a in policies.values()
    ]
    policy_rows.extend(
        {
            "snapshot_id": p.snapshot_id,
            "retrieved_at": p.retrieved_at.isoformat(),
            "refresh_by": p.refresh_by.isoformat(),
            "state": "fresh_clock_only" if p.refresh_by > cutoff else "policy_refresh_required",
            "substantive_evidence": False,
            "provenance_reference": p.provenance_reference,
        }
        for p in receipts
    )
    policy_state = (
        "fresh"
        if policies
        and not unavailable_policy
        and all(r["state"] in {"fresh", "fresh_clock_only"} for r in policy_rows)
        else "policy_refresh_required"
    )
    kind_population = defaultdict(set)
    kind_sample = defaultdict(set)
    source_types = defaultdict(set)
    review_materials = defaultdict(list)
    comments = []
    for a in annotations:
        kind_population[a.payload.kind].update(a.sample.population_ids)
        kind_sample[a.payload.kind].update(a.sample.sample_ids)
        source_types[a.payload.kind].add(a.source_type)
        review_materials[a.payload.kind].append(
            {
                "annotation_id": a.annotation_id,
                "source_type": a.source_type,
                "sample_manifest": a.sample.model_dump(mode="json"),
                "reviewed_material_types": sorted({m.kind for m in a.materials}),
                "reviewed_material_ids": [m.material_id for m in a.materials],
                "sample_ids": list(a.sample.sample_ids),
                "population_ids": list(a.sample.population_ids),
                "material": a.payload.model_dump(mode="json"),
                "input_ids": list(a.input_ids),
            }
        )
        if a.payload.kind == "comment_theme":
            comments.append({"annotation_id": a.annotation_id, **a.payload.model_dump(mode="json")})
    qualitative = {
        k: {
            **fraction(len(kind_sample[k]), len(p), kind_sample[k]),
            "source_types": sorted(source_types[k]),
            "materials": review_materials[k],
            "scoped_video_coverage": fraction(
                len(kind_sample[k] & videos), len(videos), kind_sample[k] & videos
            ),
            "warning": (
                "Declared review populations and sampled assets/cases "
                "are not full channel or video coverage"
            ),
        }
        for k, p in kind_population.items()
    }
    groups = {
        m.independence_unit for m in frame.members if m.independence_state == "documented_group"
    }
    unknown_owners = {
        m.subject.entity_id
        for m in frame.members
        if m.subject.entity_kind == "channel" and m.independence_state == "unknown"
    }
    for v in frame.videos:
        if v.membership.independence_state == "documented_group":
            groups.add(v.membership.independence_unit)
        elif v.channel_id:
            unknown_owners.add(v.channel_id)
    routes = defaultdict(set)
    route_metadata = {}
    occurrence_count = 0
    route_runs = defaultdict(set)
    # Channel discovery recruits scoped uploads; video discovery recruits that video.
    for m in (*frame.members, *(v.membership for v in frame.videos)):
        for route in m.discovery_occurrences:
            occurrence_count += 1
            name = route.get("route", "unknown")
            routes[name].add(m.subject.entity_id)
            route_metadata[name] = {
                k: route.get(k) for k in ("provider", "sort_order", "mode", "collection_version")
            }
            dependencies.add(route["run_id"])
            route_runs[name].add(route["run_id"])
    route_rows = {}
    for name, ids in routes.items():
        others = (
            set().union(*(s for n, s in routes.items() if n != name)) if len(routes) > 1 else set()
        )
        route_rows[name] = {
            "entities": sorted(ids),
            "unique_entities": sorted(ids - others),
            "overlap_entities": sorted(ids & others),
            "metadata": route_metadata[name],
            "collections": [
                {
                    "run_id": rid,
                    "run": dict(
                        c.execute("SELECT * FROM discovery_runs WHERE run_id=?", (rid,)).fetchone()
                    ),
                    "pages": [
                        dict(p)
                        for p in c.execute(
                            (
                                "SELECT page_number,available_at,outcome,reason,"
                                "next_token IS NOT NULL AS more_pages_indicated "
                                "FROM discovery_pages WHERE run_id=? ORDER BY page_number"
                            ),
                            (rid,),
                        )
                    ],
                }
                for rid in sorted(route_runs[name])
            ],
        }
    return {
        "coverage": {
            "channels": fraction(
                len(observed_channels & channels), len(channels), observed_channels & channels
            ),
            "videos": fraction(len(known), len(videos), known),
            "topic_classification": fraction(len(topics), len(videos), topics),
            "qualitative": qualitative,
        },
        "classifications": classifications,
        "conflicts": conflicts,
        "ignored_financial_conflict_ids": ignored_conflicts,
        "policy": {
            "state": policy_state,
            "snapshots": policy_rows,
            "unavailable_ids": unavailable_policy,
            "expired_receipt_ids": [
                p.snapshot_id for p in options.policy_clocks if p.expires_at <= now
            ],
        },
        "ownership": {
            "documented_groups": sorted(groups),
            "provisional_canonical_channels": sorted(channels),
            "unknown_relationship_channels": sorted(unknown_owners),
        },
        "routes": {
            "routes": route_rows,
            "occurrences": occurrence_count,
            "unique_entities": len(set().union(*routes.values())) if routes else 0,
            "omissions": ["No stored route provenance"] if not routes else [],
            "limitations": [
                (
                    "Retrieved scope only; pagination/index caps do not establish "
                    "YouTube representativeness"
                )
            ],
        },
        "comments": {
            "reviews": comments,
            "videos": sorted({a["video_id"] for a in comments}),
            "sample_counts_by_capture": [
                {
                    k: a[k]
                    for k in ("video_id", "source", "route", "order", "retrieved_at", "sample_size")
                }
                for a in comments
            ],
            "warning": (
                "Overlapping themes/captures are not summed as independent "
                "comments or audience sentiment"
            ),
        },
        "annotations": tuple(
            {a.annotation_id: a for a in (*annotations, *policy_annotations)}.values()
        ),
        "dependencies": dependencies,
    }
