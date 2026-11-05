"""Leave-one-out prior references, frozen at an explicit landmark."""

from collections import defaultdict

from youtube_niche_mcp.analysis.numerics import blend, log_baseline


def baseline(frame, outcomes, options):
    if options.baseline_cutoff and frame.video_freeze_at > options.baseline_cutoff:
        return None, None, {"reason": "Reference membership was not frozen at baseline landmark"}
    candidate = next((v for v in frame.videos if v.video_id == options.candidate_id), None)
    if candidate is None or candidate.publication_at is None:
        return None, None, {"reason": "Candidate not in frozen comparable frame"}
    references = [
        o
        for o in outcomes
        if o.video_id != candidate.video_id
        and o.state == "available"
        and o.publication_at < candidate.publication_at
        and o.available_at <= options.baseline_cutoff
    ]
    own = [o for o in references if o.channel_id == candidate.channel_id]
    peers = [o for o in references if o.channel_id != candidate.channel_id and o.channel_id]
    channels = defaultdict(list)
    for o in peers:
        channels[o.channel_id].append(o.value)
    details = {
        "own_ids": [o.video_id for o in own],
        "peer_ids": [o.video_id for o in peers],
        "own_count": len(own),
        "peer_videos": len(peers),
        "peer_channels": len(channels),
        "landmark": options.baseline_cutoff.isoformat(),
        "absolute_views_separate": True,
    }
    peer_members = [v.membership for v in frame.videos if v.channel_id in channels]
    details["peer_independent_units"] = sorted(
        {m.independence_unit for m in peer_members if m.independence_state == "documented_group"}
    )
    details["peer_unresolved_ownership"] = len(
        {
            v.channel_id
            for v in frame.videos
            if v.channel_id in channels and v.membership.independence_state == "unknown"
        }
    )
    own_log = log_baseline([o.value for o in own])
    pooled = None
    if len(peers) >= options.peer_video_minimum and len(channels) >= options.peer_channel_minimum:
        from youtube_niche_mcp.analysis.numerics import quantile

        peer_log = quantile([log_baseline(values) for values in channels.values()])
        b, pooled, weight = blend(own_log, peer_log, len(own), options.pooling_k)
        details.update(
            {
                "pooled_log": b,
                "peer_log": peer_log,
                "own_log": own_log,
                "lambda": weight,
                "peer_video_weighted_log": log_baseline([o.value for o in peers]),
            }
        )
    if len(own) >= options.own_minimum:
        own_value = own_log.exp() - 1
        details["f1_baseline_mode"] = "own_log_median"
        return own_value, pooled, details
    details["f1_baseline_mode"] = "F2_cold_start"
    return pooled, pooled, details
