"""One maturity/history/source policy for every formula; never perform HTTP."""

from datetime import timedelta

from youtube_niche_mcp.analysis.models import AnalysisOptions, Outcome, VideoInput

EXCLUDED = {"outside_cohort", "excluded_format"}


def resolve(video: VideoInput, options: AnalysisOptions, now) -> Outcome:
    pub = video.publication_at
    maturity = pub + options.age if pub else None
    body = dict(
        video_id=video.video_id,
        channel_id=video.channel_id,
        publication_at=pub,
        maturity_at=maturity,
    )

    def missing(state, reason):
        return Outcome(**body, state=state, reason=reason)

    state = video.membership.state.value
    if state == "excluded":
        return missing("excluded_format", video.membership.reason)
    if state == "source_conflict" or video.identity_conflict:
        return missing("source_conflict", "Frozen identity/publication conflict")
    if state not in {"included", "included_with_uncertainty"}:
        return missing("classification_unknown", "Frozen eligibility unresolved")
    if pub is None or pub > options.cutoff:
        return missing("insufficient_history", "Known publication chronology unavailable")
    if options.cutoff < maturity:
        return missing("pending_maturity", "Target outcome age not reached at cutoff")
    snapshots = [
        s
        for s in video.snapshots
        if s.observed_at <= options.cutoff
        and s.available_at <= options.cutoff
        and s.expires_at > now
    ]
    end = maturity + timedelta(seconds=options.tolerance_seconds)
    valid = [
        s
        for s in snapshots
        if maturity <= s.observed_at <= end
        and s.source_kind == "public_api"
        and s.source in {"youtube:videos.list", "youtube:videos.batchGetStats"}
        and s.precision == "exact"
        and s.evidence_state == "available"
        and s.outcome == "available"
        and s.value is not None
    ]
    if valid:
        valid.sort(key=lambda s: (s.observed_at, -s.available_at.timestamp(), s.observation_id))
        selected = valid[0]
        if len({s.value for s in valid if s.observed_at == selected.observed_at}) > 1:
            return missing("source_conflict", "Contemporaneous official counts disagree")
        return Outcome(
            **body,
            state="available",
            value=selected.value,
            observation_id=selected.observation_id,
            observed_at=selected.observed_at,
            available_at=selected.available_at,
            reason="Retained exact age-matched official count",
        )
    if video.policy_blocked:
        return missing(
            "policy_permission_required", "Required history expired or permission unavailable"
        )
    removed = [
        s
        for s in snapshots
        if s.outcome in {"unavailable", "deleted_or_private_unknown", "API_missing"}
    ]
    if removed:
        return missing("not_publicly_available", "Known video unavailable; absence is not failure")
    return missing("insufficient_history", "No retained official count at the declared age window")
