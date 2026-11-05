"""Metadata evidence adapter; it does not turn metadata into verified audio/visual review."""

from youtube_niche_mcp.domain.foundation import Outcome
from youtube_niche_mcp.eligibility.models import Claim, Subject
from youtube_niche_mcp.eligibility.rules import duration_seconds


def metadata_claims(observation):
    if observation.outcome != Outcome.AVAILABLE:
        return ()
    p, m = observation.provenance, observation.metadata
    subject = Subject(entity_kind=observation.entity_kind, entity_id=observation.entity_id)
    result = []

    def add(field, value, basis, reason):
        if p.source_kind.value != "public_api" and basis in {
            "official_metadata",
            "default_audio_language",
        }:
            basis = "provider_label"
        result.append(
            Claim(
                subject=subject,
                field=field,
                value=value,
                basis=basis,
                source=p.source,
                source_version=p.source_version,
                observed_at=p.observed_at,
                available_at=p.available_at,
                reason=reason,
                data_origin="provider_data" if p.source_kind.value == "provider" else "api_data",
            )
        )

    seconds = duration_seconds(m.duration)
    if seconds is not None:
        add(
            "duration_seconds",
            seconds,
            "official_metadata",
            "Captured ISO duration; independent of Shorts status",
        )
    if m.default_audio_language:
        add(
            "spoken_language",
            m.default_audio_language,
            "default_audio_language",
            "Declared default audio track, not audited full speech",
        )
    if m.default_language:
        add(
            "spoken_language",
            m.default_language,
            "default_language",
            "Text metadata language; cannot verify spoken content",
        )
    if m.actual_end_at:
        add(
            "live_status",
            "archived_live",
            "official_metadata",
            "Completed broadcast has actual end time",
        )
    elif m.actual_start_at:
        add(
            "live_status",
            "currently_live",
            "official_metadata",
            "Broadcast started without observed end time",
        )
    elif m.scheduled_start_at:
        add(
            "live_status",
            "scheduled_live",
            "official_metadata",
            "Scheduled broadcast has no actual start",
        )
    if m.live_broadcast_content in {"live", "upcoming"}:
        add(
            "live_status",
            "currently_live" if m.live_broadcast_content == "live" else "scheduled_live",
            "official_metadata",
            "Explicit snippet liveBroadcastContent",
        )
    elif (
        m.live_details_checked
        and not any((m.actual_start_at, m.actual_end_at, m.scheduled_start_at))
        and m.live_broadcast_content == "none"
    ):
        add(
            "live_status",
            "ordinary_vod",
            "official_metadata",
            "Explicit none and requested live details absent",
        )
    if observation.entity_kind == "channel":
        evidence = observation.metrics.get("subscriber_count")
        count = evidence.value if evidence else None
        payload = {"count": count, "hidden": m.subscriber_hidden}
        if count is not None:
            step = (
                10 ** max(0, len(str(count)) - 3)
                if evidence.provenance.precision.value == "rounded"
                else 1
            )
            payload["upper_bound"] = count + step - 1
        add(
            "subscriber_count",
            payload,
            "official_metadata",
            "Current observed public subscriber interval; historical size separate",
        )
    return tuple(result)
