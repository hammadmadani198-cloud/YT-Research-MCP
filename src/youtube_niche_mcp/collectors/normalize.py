"""Normalize only public facts; absent and hidden counts remain structured unknowns."""

from datetime import UTC, datetime

from youtube_niche_mcp.api.client import EntityResult
from youtube_niche_mcp.api.contracts import CONTRACT_VERSION
from youtube_niche_mcp.domain.evidence import NumericEvidence
from youtube_niche_mcp.domain.foundation import Metadata, Observation, Outcome
from youtube_niche_mcp.domain.provenance import Provenance
from youtube_niche_mcp.domain.states import EvidenceState, Precision, SourceKind


def parse_time(value):
    if value is None:
        return None
    at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if at.tzinfo is None:
        raise ValueError("Source timestamp has no timezone")
    return at


def regime(at: datetime) -> str:
    return (
        "public-playback-starts-2026-08-24-cumulative-mixed"
        if at >= datetime(2026, 8, 24, tzinfo=UTC)
        else "public-pre-2026-08-24-format-dependent"
    )


def normalize(result: EntityResult, kind: str, capture_id: str) -> Observation:
    page = result.page
    provenance = Provenance(
        source=f"youtube:{page.endpoint}",
        source_kind=SourceKind.PUBLIC_API,
        source_version=CONTRACT_VERSION,
        precision=Precision.EXACT if result.outcome == Outcome.AVAILABLE else Precision.UNKNOWN,
        observed_at=page.observed_at,
        available_at=page.available_at,
    )
    base = dict(
        capture_id=capture_id,
        entity_kind=kind,
        entity_id=result.entity_id,
        request_at=page.request_at,
        provenance=provenance,
        metric_definition=regime(page.observed_at),
        outcome_detail=page.reason,
        http_status=page.http_status,
    )
    if result.outcome != Outcome.AVAILABLE or result.item is None:
        if base["outcome_detail"] == "ok":
            base["outcome_detail"] = result.outcome.value
        return Observation(**base, outcome=result.outcome)
    try:
        item = result.item
        snippet, stats, details = (
            item.get("snippet", {}),
            item.get("statistics", {}),
            item.get("contentDetails", {}),
        )
        hidden = stats.get("hiddenSubscriberCount")
        live = item.get("liveStreamingDetails", {})
        if hidden is not None and not isinstance(hidden, bool):
            raise ValueError("Malformed visibility flag")
        metadata = Metadata(
            title=snippet.get("title"),
            channel_id=snippet.get("channelId"),
            account_created_at=parse_time(snippet.get("publishedAt"))
            if kind == "channel"
            else None,
            publication_at=parse_time(snippet.get("publishedAt")) if kind == "video" else None,
            publication_semantics=(
                "API publishedAt; public/private/unlisted/members exceptions apply"
                if kind == "video" and snippet.get("publishedAt")
                else None
            ),
            upload_at=parse_time(snippet.get("publishTime")),
            duration=details.get("duration"),
            subscriber_hidden=hidden,
            uploads_playlist_id=details.get("relatedPlaylists", {}).get("uploads"),
            default_audio_language=snippet.get("defaultAudioLanguage"),
            default_language=snippet.get("defaultLanguage"),
            live_broadcast_content=snippet.get("liveBroadcastContent"),
            live_details_checked="liveStreamingDetails" in page.requested_parts,
            actual_start_at=parse_time(live.get("actualStartTime")),
            actual_end_at=parse_time(live.get("actualEndTime")),
            scheduled_start_at=parse_time(live.get("scheduledStartTime")),
        )
        fields = (
            {
                "view_count": "viewCount",
                "subscriber_count": "subscriberCount",
                "video_count": "videoCount",
            }
            if kind == "channel"
            else {
                "view_count": "viewCount",
                "like_count": "likeCount",
                "comment_count": "commentCount",
            }
        )
        metrics = {}
        for field, api_field in fields.items():
            value = stats.get(api_field)
            if field == "subscriber_count" and hidden:
                value = None
            if value is None:
                evidence = NumericEvidence(
                    state=EvidenceState.NOT_PUBLICLY_AVAILABLE,
                    value=None,
                    reason="hidden_or_absent_public_field",
                    provenance=provenance.model_copy(update={"precision": Precision.UNKNOWN}),
                )
            else:
                if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
                    raise ValueError("Malformed public count")
                count = int(value)
                approximate = field == "subscriber_count"
                metric_provenance = (
                    provenance.model_copy(update={"precision": Precision.ROUNDED})
                    if approximate
                    else provenance
                )
                evidence = NumericEvidence(
                    state=EvidenceState.APPROXIMATE if approximate else EvidenceState.AVAILABLE,
                    value=count,
                    reason="rounded_down_three_significant_figures"
                    if approximate
                    else "public_api_count",
                    provenance=metric_provenance,
                )
            metrics[field] = evidence
        # Capture precision describes its least precise present metric.
        if kind == "channel" and metrics["subscriber_count"].value is not None:
            provenance = provenance.model_copy(update={"precision": Precision.ROUNDED})
            base["provenance"] = provenance
        return Observation(**base, metadata=metadata, metrics=metrics)
    except (ValueError, TypeError, AttributeError):
        base["outcome_detail"] = "malformed_public_record"
        return Observation(**base, outcome=Outcome.PARTIAL_RESPONSE)
