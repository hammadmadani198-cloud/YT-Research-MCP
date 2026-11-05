"""T2 auxiliary diagnostics from validated daily analytics; never canonical inputs."""

import json
from decimal import Decimal

from youtube_niche_mcp.analysis.numerics import ratio
from youtube_niche_mcp.collectors.nexlev.models import ProviderRecord
from youtube_niche_mcp.domain.foundation import timestamp


def diagnostics(connection, subjects, cutoff, now, window):
    output, ids, expiries = [], set(), []
    for row in connection.execute(
        "SELECT e.*,s.expires_at AS source_expiry,r.expires_at AS run_expiry "
        "FROM provider_evidence e JOIN source_records s USING(source_id) "
        "JOIN provider_runs r USING(run_id) WHERE e.route='nexlev.daily_analytics' "
        "AND e.observed_at<=? AND e.available_at<=? ORDER BY e.evidence_id",
        (timestamp(cutoff), timestamp(cutoff)),
    ):
        if row["entity_id"] not in subjects:
            continue
        expiry = min(row["expires_at"], row["source_expiry"], row["run_expiry"])
        if expiry <= timestamp(now):
            continue
        record = ProviderRecord.model_validate_json(row["record_json"])
        points = sorted(
            (
                p
                for p in record.history
                if window.start <= p.date <= window.end
                and p.date <= cutoff
                and (not p.data_fetched_at or p.data_fetched_at <= cutoff)
            ),
            key=lambda p: p.date,
        )
        flags = set(json.loads(row["anomalies_json"]))
        if any(p.videos == 0 for p in points):
            flags.add("zero_video_count")
        for quantity, unit in (
            ("views", "views/hour"),
            ("subscribers", "subscribers/hour"),
            ("videos", "uploads/hour"),
        ):
            intervals = []
            for a, b in zip(points, points[1:], strict=False):
                left, right = getattr(a, quantity), getattr(b, quantity)
                elapsed = Decimal(str((b.date - a.date).total_seconds()))
                if elapsed <= 0:
                    flags.add("timestamp_conflict")
                    continue
                if left is None or right is None:
                    flags.add("missing_value")
                    continue
                if left < 0 or right < 0:
                    flags.add("impossible_count")
                    continue
                delta = right - left
                if delta < 0:
                    flags.add("negative_delta")
                intervals.append(
                    {
                        "timestamps": [a.date.isoformat(), b.date.isoformat()],
                        "values": [left, right],
                        "delta": delta,
                        "elapsed_seconds": elapsed,
                        "rate": ratio(delta * 3600, elapsed),
                    }
                )
            if any(
                a["delta"] < 0 < b["delta"] for a, b in zip(intervals, intervals[1:], strict=False)
            ):
                flags.add("rebound")
            output.append(
                {
                    "history_class": "PROVIDER_HISTORY",
                    "trust_class": "T2",
                    "entity_id": row["entity_id"],
                    "evidence_id": row["evidence_id"],
                    "retrieved_at": record.available_at.isoformat(),
                    "quantity": quantity,
                    "unit": unit,
                    "intervals": intervals,
                    "flags": sorted(flags),
                    "state": "source_conflict"
                    if "timestamp_conflict" in flags
                    else "available"
                    if intervals
                    else "insufficient_history",
                }
            )
        ids.update((row["evidence_id"], row["source_id"], row["run_id"]))
        expiries.append(expiry)
    return output, ids, expiries
