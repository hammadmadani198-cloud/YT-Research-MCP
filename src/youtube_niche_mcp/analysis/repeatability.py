"""Explicit/first-known anchors and actual chronological follow-up positions."""

from youtube_niche_mcp.analysis.numerics import quantile, ratio
from youtube_niche_mcp.analysis.outcomes import EXCLUDED


def repeatability(frame, outcomes, options):
    by_id = {o.video_id: o for o in outcomes}
    anchor = by_id.get(options.anchor_id)
    mode = "explicit"
    if options.anchor_id:
        if anchor is None or anchor.state != "available" or anchor.value < options.goal:
            return {
                "state": "insufficient_history",
                "reason": "Explicit anchor requires observed qualifying hit",
            }
    elif options.anchor_channel_id:
        mode = "first_known_goal_hit"
        if frame.video_freeze_at > options.anchor_cutoff:
            return {"state": "insufficient_history", "reason": "Anchor frame unknown at landmark"}
        candidates = [
            o
            for o in outcomes
            if o.channel_id == options.anchor_channel_id
            and o.state == "available"
            and o.value >= options.goal
            and o.available_at <= options.anchor_cutoff
        ]
        anchor = min(candidates, key=lambda o: (o.publication_at, o.video_id), default=None)
    if anchor is None:
        return {"state": "insufficient_sample", "reason": "No declared, verified anchor"}
    after = sorted(
        [
            o
            for o in outcomes
            if o.channel_id == anchor.channel_id
            and o.publication_at
            and (o.publication_at, o.video_id) > (anchor.publication_at, anchor.video_id)
        ],
        key=lambda o: (o.publication_at, o.video_id),
    )
    eligible = [o for o in after if o.state not in EXCLUDED]
    unpositioned = [
        o.video_id
        for o in outcomes
        if o.state not in EXCLUDED
        and o.publication_at is None
        and o.channel_id in {anchor.channel_id, None}
    ]
    windows = {}
    for k in (5, 10):
        selected = eligible[:k]
        mature = [o for o in selected if o.state == "available"]
        h = sum(o.value >= options.goal for o in mature)
        positions = [
            {"position": i + 1, "video_id": o.video_id, "state": o.state, "value": o.value}
            for i, o in enumerate(selected)
        ]
        positions.extend(
            {"position": i + 1, "video_id": None, "state": "not_yet_occurred", "value": None}
            for i in range(len(selected), k)
        )
        windows[str(k)] = {
            "actual_followups": len(selected),
            "mature": len(mature),
            "hits": h,
            "pending": sum(o.state == "pending_maturity" for o in selected),
            "unknown": len(selected) - len(mature),
            "absent": k - len(selected),
            "R_k": ratio(h, k) if len(mature) == k and not unpositioned else None,
            "known_only_fraction": ratio(h, len(mature)),
            "median_mature": quantile([o.value for o in mature]),
            "positions": positions,
        }
    return {
        "state": "available"
        if windows["10"]["mature"] == 10 and not unpositioned
        else "partial_coverage",
        "anchor_id": anchor.video_id,
        "anchor_observation_id": anchor.observation_id,
        "anchor_mode": mode,
        "unpositioned_unknown_chronology": unpositioned,
        "anchor_landmark": options.anchor_cutoff.isoformat() if options.anchor_cutoff else None,
        "windows": windows,
        "excluded_followups": [o.video_id for o in after if o.state in EXCLUDED],
        "context": "No observed follow-up is not permanent creator failure",
    }
