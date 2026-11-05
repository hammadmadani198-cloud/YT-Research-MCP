"""Paired entrant/upload exposure; stopped and zero-output entrants stay."""

from collections import defaultdict
from datetime import datetime, timedelta

from youtube_niche_mcp.analysis.bounds import bounds
from youtube_niche_mcp.analysis.numerics import quantile, ratio
from youtube_niche_mcp.analysis.outcomes import EXCLUDED


def exposure(frame, outcomes, options, *, grouped):
    rows, units = [], defaultdict(list)
    if frame.kind not in {"entrant", "small_channel"}:
        return {"state": "insufficient_sample", "reason": "Frozen channel/entrant frame required"}
    for m in frame.members:
        if m.state.value not in {"included", "included_with_uncertainty"}:
            continue
        unit = m.independence_unit if grouped else m.subject.entity_id
        units[unit].append(m)
    coverage = {c.channel_id: c for c in options.coverage}
    for unit, members in sorted(units.items()):
        scoped, completed = {}, True
        unresolved = any(o.channel_id is None and o.state not in EXCLUDED for o in outcomes)
        clocks, channels = [], []
        unpositioned = set()
        entry_values = [
            datetime.fromisoformat(m.entry_status["first_observed_niche_entry"])
            for m in members
            if m.entry_status.get("first_observed_niche_entry")
        ]
        unit_entry = min(entry_values) if entry_values else None
        for m in members:
            channel = m.subject.entity_id
            channels.append(channel)
            raw = m.entry_status.get("first_observed_niche_entry")
            if not raw:
                completed = False
                unresolved = True
                continue
            entry = unit_entry
            end = entry + timedelta(days=options.exposure_days)
            clocks.append((entry, end))
            review = coverage.get(channel)
            completed &= bool(
                options.cutoff >= end + options.age and review and review.through >= end
            )
            if any(
                o.channel_id == channel and o.publication_at is None and o.state not in EXCLUDED
                for o in outcomes
            ):
                unresolved = True
            unpositioned.update(
                o.video_id
                for o in outcomes
                if o.state not in EXCLUDED
                and (o.channel_id is None or (o.channel_id == channel and o.publication_at is None))
            )
            attempts = sorted(
                [
                    o
                    for o in outcomes
                    if o.channel_id == channel
                    and o.publication_at
                    and entry <= o.publication_at < end
                    and o.state not in EXCLUDED
                ],
                key=lambda o: (o.publication_at, o.video_id),
            )
            if any(o.state == "classification_unknown" for o in attempts):
                unresolved = True
            for o in attempts:
                scoped[o.video_id] = o
        # Group first K is over the combined chronological publications, not K per sister.
        selected = sorted(scoped.values(), key=lambda o: (o.publication_at, o.video_id))
        if options.first_k is not None:
            selected = selected[: options.first_k]
        known = [o for o in selected if o.state == "available"]
        hits = sum(o.value >= options.goal for o in known)
        pending = sum(o.state == "pending_maturity" for o in selected)
        unknown = len(selected) - len(known)
        status = (
            "hit" if hits else "miss" if completed and not unknown and not unresolved else "unknown"
        )
        rows.append(
            {
                "unit": unit,
                "channels": channels,
                "attempt_ids": [o.video_id for o in selected],
                "attempts": len(selected),
                "mature": len(known),
                "hits": hits,
                "pending": pending,
                "unknown": unknown,
                "unpositioned_records": sorted(unpositioned),
                "status": status,
                "window_complete": completed,
                "known_upload_fraction": ratio(hits, len(known)),
                "elapsed_days": [
                    min(
                        options.exposure_days,
                        max(0, (options.cutoff - entry).total_seconds() / 86400),
                    )
                    for entry, _ in clocks
                ],
                "entry_clocks": [entry.isoformat() for entry, _ in clocks],
            }
        )
    n = len(rows)
    h = sum(r["status"] == "hit" for r in rows)
    u = sum(r["status"] == "unknown" for r in rows)
    actual = sum(r["attempts"] for r in rows)
    hits = sum(r["hits"] for r in rows)
    unknown = sum(r["unknown"] for r in rows)
    mature = actual - unknown
    known_channel_rates = [
        r["known_upload_fraction"] for r in rows if r["known_upload_fraction"] is not None
    ]
    enumerated = options.finite_frame_reference is not None
    unpositioned_ids = sorted({vid for r in rows for vid in r["unpositioned_records"]})
    return {
        "state": "available" if n and not u else "partial_coverage" if n else "insufficient_sample",
        "unit": "frozen_creator_unit" if grouped else "raw_channel",
        "K": options.first_k,
        "T_days": options.exposure_days,
        "entrants": n,
        "successful": h,
        "unknown_entrants": u,
        "fraction": ratio(h, n) if not u else None,
        "known_only_fraction": ratio(h, n - u),
        "attempts": actual,
        "upload_hits": hits,
        "upload_unknown": unknown,
        "upload_fraction": ratio(hits, actual) if not unknown and not unpositioned_ids else None,
        "known_only_upload_fraction": ratio(hits, mature),
        "channel_bounds": bounds(n, h, u, enumerated),
        "upload_bounds": bounds(actual, hits, unknown, enumerated and not unpositioned_ids),
        "unpositioned_records": unpositioned_ids,
        "attempts_median": quantile([r["attempts"] for r in rows]),
        "zero_output": sum(r["attempts"] == 0 for r in rows),
        "low_output": sum(0 < r["attempts"] < (options.first_k or 5) for r in rows),
        "channel_balanced_known_upload_mean": ratio(
            sum(known_channel_rates), len(known_channel_rates)
        ),
        "rows": rows,
    }
