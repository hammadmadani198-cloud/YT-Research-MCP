"""Named, sample-scoped reach shares and HHI; no evaluative cutoffs."""

from collections import defaultdict
from decimal import Decimal

from youtube_niche_mcp.analysis.numerics import ratio


def shares(mass):
    total = sum(mass.values())
    fractions = {k: ratio(v, total) for k, v in sorted(mass.items())}
    hhi = sum(s * s for s in fractions.values()) if total else None
    order = sorted(mass, key=lambda k: (-mass[k], k))
    return {
        "total": total,
        "mass": dict(mass),
        "shares": fractions,
        "HHI": hhi,
        "effective_count": ratio(1, hhi),
        "top1": ratio(mass[order[0]], total) if order else None,
        "top3": ratio(sum(mass[k] for k in order[:3]), total),
        "top_ids": order[:3],
    }


def concentration(frame, outcomes, options):
    videos = {v.video_id: v for v in frame.videos}
    video_mass, channel_mass, unit_mass, topic_mass = (
        {},
        defaultdict(int),
        defaultdict(int),
        defaultdict(Decimal),
    )
    classified_mass, unclassified_mass = 0, 0
    classified_count, mature_count = 0, 0
    for o in outcomes:
        if o.state != "available":
            continue
        v = videos[o.video_id]
        mature_count += 1
        video_mass[o.video_id] = o.value
        channel_mass[o.channel_id] += o.value
        unit_mass[v.membership.independence_unit] += o.value
        if v.topic_families and not v.topic_conflict:
            classified_count += 1
            classified_mass += o.value
            for topic in v.topic_families:
                topic_mass[topic] += Decimal(o.value) / len(v.topic_families)
        else:
            unclassified_mass += o.value
    channel = shares(channel_mass)
    removed = dict(channel_mass)
    if channel["top_ids"]:
        removed.pop(channel["top_ids"][0])
    coverage = ratio(classified_count, mature_count)
    topic = shares(topic_mass)
    if coverage is None or coverage < options.classification_minimum:
        topic["HHI"] = None
        topic["effective_count"] = None
        topic["state"] = "insufficient_classification_coverage"
    else:
        topic["state"] = "available" if classified_mass else "insufficient_sample"
    return {
        "videos": shares(video_mass),
        "channels": channel,
        "creator_units": shares(unit_mass),
        "topics": topic,
        "classified_mass": classified_mass,
        "unclassified_mass": unclassified_mass,
        "classification_coverage": coverage,
        "top_channel_removed": shares(removed),
        "topic_allocation": "equal fractional mass across frozen multi-label families",
        "scope": "matched-age observed reach in this researched frame only",
    }
