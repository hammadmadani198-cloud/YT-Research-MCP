"""Channel Q25 first, then across-channel median, plus observed failure floor."""

from collections import defaultdict
from decimal import Decimal

from youtube_niche_mcp.analysis.numerics import quantile, ratio


def floor(outcomes, options):
    channels = defaultdict(list)
    values = []
    for o in outcomes:
        if o.state == "available":
            values.append(o.value)
            channels[o.channel_id].append(o.value)
    floors = {c: quantile(v, Decimal(".25")) for c, v in sorted(channels.items())}
    return quantile(list(floors.values())), {
        "channel_floors": floors,
        "contributing_channels": len(floors),
        "channel_floor_q25": quantile(list(floors.values()), Decimal(".25")),
        "video_weighted_median": quantile(values),
        "video_weighted_q25": quantile(values, Decimal(".25")),
        "low_threshold": options.low_threshold,
        "low_count": sum(v < options.low_threshold for v in values),
        "low_fraction": ratio(sum(v < options.low_threshold for v in values), len(values)),
        "observed_zero_count": values.count(0),
        "weak_channels": [c for c, v in floors.items() if v < options.low_threshold],
        "channels_below_five_mature": [c for c, v in channels.items() if len(v) < 5],
    }
