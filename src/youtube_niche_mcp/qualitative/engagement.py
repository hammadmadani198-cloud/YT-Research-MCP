"""F14 same-capture, age-comparable public interactions per 1,000 views."""

import json
from collections import defaultdict

from youtube_niche_mcp.analysis.numerics import quantile, ratio
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.qualitative.dimensions import typed


def engagement_description(history, outcomes, annotations, options):
    wanted = {o.observation_id for o in outcomes if o.observation_id}
    captures = {}
    now = timestamp(history.clock())
    for row in history.connection.execute(
        "SELECT o.*,s.expires_at FROM video_observations o JOIN source_records s USING(source_id) "
        "WHERE s.expires_at>?",
        (now,),
    ):
        if row["observation_id"] in wanted:
            captures[row["observation_id"]] = json.loads(row["evidence_json"])
    for row in history.connection.execute(
        "SELECT h.* FROM statistical_history h JOIN retention_permissions p USING(permission_id) "
        "WHERE h.expires_at>? AND p.expires_at>?",
        (now, now),
    ):
        if row["observation_id"] in wanted:
            captures[row["observation_id"]] = json.loads(row["statistics_json"]).get("metrics", {})
    rows, channel = [], defaultdict(lambda: defaultdict(list))
    themes = typed(annotations, "comment_theme")
    for outcome in outcomes:
        metrics = captures.get(outcome.observation_id, {})
        row = {
            "video_id": outcome.video_id,
            "channel_id": outcome.channel_id,
            "state": outcome.state,
            "denominator_views": outcome.value,
            "observation_id": outcome.observation_id,
            "observed_at": outcome.observed_at.isoformat() if outcome.observed_at else None,
            "age_days": options.age_days,
            "tolerance_seconds": options.tolerance_seconds,
            "source": None,
            "comment_availability": "unknown",
        }
        availability = {
            a.payload.availability for a in themes if a.payload.video_id == outcome.video_id
        }
        row["comment_availability"] = (
            next(iter(availability))
            if len(availability) == 1
            else "source_conflict"
            if availability
            else "unknown"
        )
        for field, label in (("like_count", "likes"), ("comment_count", "comments")):
            evidence = metrics.get(field, {})
            provenance = evidence.get("provenance", {})
            value = evidence.get("value")
            valid = (
                outcome.state == "available"
                and type(value) is int
                and value >= 0
                and evidence.get("state") == "available"
                and provenance.get("source_kind") == "public_api"
                and provenance.get("source")
                in {"youtube:videos.list", "youtube:videos.batchGetStats"}
                and provenance.get("precision") == "exact"
                and provenance.get("source")
                == metrics.get("view_count", {}).get("provenance", {}).get("source")
                and provenance.get("source_version")
                == metrics.get("view_count", {}).get("provenance", {}).get("source_version")
                and provenance.get("observed_at") is not None
                and provenance.get("available_at") is not None
                and timestamp_from_json(provenance["available_at"]) <= timestamp(options.cutoff)
                and timestamp_from_json(provenance["observed_at"]) == timestamp(outcome.observed_at)
            )
            if label == "comments" and row["comment_availability"] in {
                "disabled",
                "deleted",
                "source_conflict",
            }:
                valid = False
            numerator = value if valid else None
            descriptor = ratio(1000 * numerator, outcome.value) if numerator is not None else None
            row[f"{label}_numerator"] = numerator
            row[f"{label}_per_1000_views"] = descriptor
            row[f"{label}_state"] = (
                "available"
                if descriptor is not None
                else "zero_denominator"
                if valid and outcome.value == 0
                else "unknown"
            )
            if valid:
                row["source"] = provenance["source"]
            if descriptor is not None:
                channel[outcome.channel_id][label].append(descriptor)
        rows.append(row)
    comparable = sum(
        r["likes_per_1000_views"] is not None or r["comments_per_1000_views"] is not None
        for r in rows
    )
    return {
        "state": "partial_coverage"
        if comparable and comparable < len(rows)
        else "available"
        if comparable
        else "unknown",
        "videos": rows,
        "comparable_video_count": comparable,
        "preferred_20_met": comparable >= 20,
        "channel_medians": {
            cid: {
                label: {"median_per_1000_views": quantile(values), "count": len(values)}
                for label, values in groups.items()
            }
            for cid, groups in channel.items()
        },
        "comment_themes": [
            {
                "annotation_id": a.annotation_id,
                "source_type": a.source_type,
                **a.payload.model_dump(mode="json"),
            }
            for a in themes
        ],
        "limitations": [
            "Same-age public interaction descriptors are not retention or satisfaction",
            "Comment themes describe the retrieved sample, "
            "not representative sentiment or demand percentages",
        ],
    }


def timestamp_from_json(value):
    from datetime import datetime

    return timestamp(datetime.fromisoformat(value.replace("Z", "+00:00")))
