"""One history sufficiency gate for all Phase 4 formulas; no inference/backfill."""

from collections import Counter

OFFICIAL = {"youtube:videos.list", "youtube:videos.batchGetStats"}


def availability(states, *, missing="insufficient_history", provider_only=False):
    counts = Counter(states)
    known = counts["available"] + counts["partial_coverage"]
    if counts["source_conflict"]:
        return "source_conflict"
    if known:
        return (
            "partial_coverage" if known < len(states) or counts["partial_coverage"] else "available"
        )
    if counts["policy_permission_required"]:
        return "policy_permission_required"
    if counts["pending_maturity"]:
        return "pending_maturity"
    return "provider_history_only" if provider_only else missing


def series(video, cutoff, now, window=None, *, provider=False):
    if video.identity_conflict or video.membership.state.value == "source_conflict":
        return (), "source_conflict"
    if video.membership.state.value not in {"included", "included_with_uncertainty"}:
        return (), "insufficient_history"
    if video.publication_at is None or video.publication_at > cutoff:
        return (), "insufficient_history"
    eligible = []
    for s in video.snapshots:
        correct_source = (
            s.source_kind == "provider" and s.source == "provider:nexlev.history"
            if provider
            else s.source_kind == "public_api" and s.source in OFFICIAL
        )
        if (
            correct_source
            and s.observed_at <= cutoff
            and s.available_at <= cutoff
            and s.observed_at >= video.publication_at
            and s.expires_at > now
            and s.precision == "exact"
            and s.evidence_state == "available"
            and s.outcome == "available"
            and s.value is not None
            and (window is None or window.start <= s.observed_at <= window.end)
        ):
            eligible.append(s)
    by_time = {}
    for s in sorted(eligible, key=lambda s: (s.observed_at, s.available_at, s.observation_id)):
        previous = by_time.get(s.observed_at)
        if previous and (previous.value, previous.metric_definition) != (
            s.value,
            s.metric_definition,
        ):
            return (), "source_conflict"
        by_time.setdefault(s.observed_at, s)
    points = tuple(by_time.values())
    if len({s.metric_definition for s in points}) > 1:
        return (), "source_conflict"
    state = (
        "available"
        if len(points) >= 2
        else ("policy_permission_required" if video.policy_blocked else "insufficient_history")
    )
    return points, state
