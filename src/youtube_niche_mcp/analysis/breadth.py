"""Frozen validated topic-family coverage and documented independent units."""

from collections import defaultdict

from youtube_niche_mcp.analysis.numerics import ratio


def breadth(frame, outcomes, options):
    videos = {v.video_id: v for v in frame.videos}
    observed = [o for o in outcomes if o.state == "available"]
    classified = [
        o
        for o in observed
        if videos[o.video_id].topic_families and not videos[o.video_id].topic_conflict
    ]
    families = defaultdict(lambda: {"channels": set(), "units": set(), "unknown": set()})
    for o in classified:
        if o.value < options.goal:
            continue
        v = videos[o.video_id]
        for topic in v.topic_families:
            f = families[topic]
            f["channels"].add(o.channel_id)
            if v.membership.independence_state == "documented_group":
                f["units"].add(v.membership.independence_unit)
            else:
                f["unknown"].add(o.channel_id)
    coverage = ratio(len(classified), len(observed))
    rows = {
        topic: {
            "channels": sorted(f["channels"]),
            "independent_units": sorted(f["units"]),
            "unknown_ownership": sorted(f["unknown"]),
            "qualifies": len(f["units"]) >= options.breadth_k,
        }
        for topic, f in sorted(families.items())
    }
    adequate = coverage is not None and coverage >= options.classification_minimum
    return {
        "state": "available" if adequate else "insufficient_classification_coverage",
        "value": sum(f["qualifies"] for f in rows.values()) if adequate else None,
        "k": options.breadth_k,
        "classification_coverage": coverage,
        "classified": len(classified),
        "unclassified": len(observed) - len(classified),
        "conflicted": sum(videos[o.video_id].topic_conflict for o in observed),
        "families": rows,
        "qualifying_independent_units": sorted(
            {u for f in rows.values() for u in f["independent_units"]}
        ),
        "qualification": (
            "Unknown ownership contributes provisional channels, not confirmed independence"
        ),
    }
