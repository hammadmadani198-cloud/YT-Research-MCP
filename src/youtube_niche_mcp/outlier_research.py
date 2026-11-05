"""Public channel baseline/outlier research with explicit cohort limitations.

Data API first; yt-dlp fallback. No NexLev, niche gates or automated GREEN verdicts.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from statistics import median
from typing import Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from youtube_niche_mcp.api.client import APIError, YouTubeClient
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.general_research import GeneralResult, via_dlp, video_item


class DeepUploadsRequest(BaseModel):
    channel_id: str = Field(pattern=r"^UC[A-Za-z0-9_-]{22}$")
    max_uploads: int = Field(default=100, ge=1, le=300)


class OutlierScanRequest(DeepUploadsRequest):
    min_duration_seconds: int = Field(default=480, ge=60, le=7200)
    min_peer_sample: int = Field(default=5, ge=3, le=25)
    max_items: int = Field(default=20, ge=1, le=50)
    include_title_terms: list[str] = Field(default_factory=list, max_length=12)
    exclude_title_terms: list[str] = Field(default_factory=list, max_length=12)
    broadcast_policy: Literal[
        "exclude_active_only", "exclude_all_broadcast_metadata", "flag_only"
    ] = "exclude_active_only"


def classify_broadcast(raw: dict) -> str:
    """Distinguish active broadcasts from completed premieres and archives."""
    snippet = raw.get("snippet") or {}
    status = snippet.get("liveBroadcastContent")
    details = raw.get("liveStreamingDetails") or {}
    if status == "live":
        return "currently_live"
    if status == "upcoming":
        return "upcoming"
    if details:
        if details.get("actualEndTime"):
            return "completed_broadcast_or_premiere"
        return "broadcast_metadata_ambiguous"
    return "ordinary_upload"


def duration_seconds(value: object) -> int | None:
    """Parse API ISO8601 duration or integer seconds from yt-dlp."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value if value >= 0 else None
    if not isinstance(value, str):
        return None
    m = re.fullmatch(
        r"P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?",
        value,
    )
    if m and any(v is not None for v in m.groups()):
        w, d, h, minutes, s = [int(x or 0) for x in m.groups()]
        return w * 604800 + d * 86400 + h * 3600 + minutes * 60 + s
    return None


def published(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    except ValueError:
        return None


def age_group(days: float) -> str:
    if days <= 30:
        return "0-30d"
    if days <= 90:
        return "31-90d"
    if days <= 365:
        return "91-365d"
    return "366d+"


async def collect(settings: Settings, req: DeepUploadsRequest) -> GeneralResult:
    """Collect paginated recent channel uploads; preserve source and missingness."""
    notes: list[str] = []
    if settings.youtube_api_key:
        try:
            async with YouTubeClient(settings) as client:
                channel = await client.request(
                    "channels.list",
                    {"part": "contentDetails", "id": req.channel_id},
                )
                ids = channel.body.get("items") or []
                upload_id = (
                    ids[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
                    if ids
                    else None
                )
                if not upload_id:
                    notes.append("Channel uploads playlist missing; trying yt-dlp.")
                else:
                    wanted: list[str] = []
                    token = None
                    seen_tokens = set()
                    has_more = True
                    page_count = 0
                    page_cap = (req.max_uploads + 49) // 50 + 2
                    while len(wanted) < req.max_uploads:
                        page_count += 1
                        if page_count > page_cap:
                            notes.append("Page cap reached; upload coverage incomplete.")
                            break
                        options = {
                            "part": "contentDetails",
                            "playlistId": upload_id,
                            "maxResults": min(50, req.max_uploads - len(wanted)),
                        }
                        if token:
                            options["pageToken"] = token
                        page = await client.request("playlistItems.list", options)
                        for entry in page.body.get("items", []):
                            video_id = (entry.get("contentDetails") or {}).get("videoId")
                            if isinstance(video_id, str) and video_id not in wanted:
                                wanted.append(video_id)
                        following = page.body.get("nextPageToken")
                        if not following:
                            has_more = False
                            break
                        if following in seen_tokens:
                            notes.append("Repeated page token; upload coverage incomplete.")
                            break
                        seen_tokens.add(following)
                        token = following
                    found = {}
                    for start in range(0, len(wanted), 50):
                        try:
                            page = await client.request(
                                "videos.list",
                                {
                                    "part": (
                                        "snippet,statistics,contentDetails,liveStreamingDetails"
                                    ),
                                    "id": ",".join(wanted[start : start + 50]),
                                },
                            )
                        except APIError as exc:
                            notes.append(f"Metadata batch incomplete: {exc.outcome.value}.")
                            break
                        for raw in page.body.get("items", []):
                            row = video_item(raw)
                            kind = classify_broadcast(raw)
                            row["broadcast_kind"] = kind
                            row["broadcast_metadata_present"] = bool(
                                raw.get("liveStreamingDetails")
                            )
                            row["is_live_archive"] = kind in {"currently_live", "upcoming"}
                            row["duration_seconds"] = duration_seconds(row.get("duration"))
                            row["metadata_source"] = "youtube_data_api"
                            found[row["id"]] = row
                    rows = [found[id_] for id_ in wanted if id_ in found]
                    if rows:
                        unavailable = len(wanted) - len(rows)
                        if unavailable:
                            notes.append(f"{unavailable} uploads lack accessible public metadata.")
                        return GeneralResult(
                            state="partial"
                            if unavailable or "incomplete" in " ".join(notes)
                            else "available",
                            summary=f"{len(rows)} accessible uploads retrieved",
                            source="youtube_data_api",
                            items=rows,
                            metadata={
                                "channel_id": req.channel_id,
                                "requested": req.max_uploads,
                                "retrieved": len(rows),
                                "more_uploads_available": has_more,
                                "collected_at": datetime.now(UTC).isoformat(),
                            },
                            warnings=notes,
                        )
                    notes.append("No accessible API video metadata; trying yt-dlp.")
        except APIError as exc:
            notes.append(f"YouTube API {exc.outcome.value}; trying yt-dlp.")
        except (ValueError, RuntimeError, TimeoutError):
            notes.append("YouTube API data incomplete; trying yt-dlp.")
    else:
        notes.append("YouTube API key absent; trying yt-dlp.")
    try:
        rows = await via_dlp(
            f"https://www.youtube.com/channel/{req.channel_id}/videos", req.max_uploads
        )
        for row in rows:
            row["duration_seconds"] = duration_seconds(row.get("duration"))
            row["is_live_archive"] = None
            row["broadcast_kind"] = "unverified_yt_dlp_metadata"
            row["broadcast_metadata_present"] = None
            row["metadata_source"] = "yt_dlp"
        if rows:
            notes.append(
                "yt-dlp flat-playlist metadata may lack views, full dates or livestream flags."
            )
            return GeneralResult(
                state="partial",
                summary=f"{len(rows)} accessible uploads via yt-dlp (incomplete metadata)",
                source="yt_dlp",
                items=rows,
                metadata={
                    "channel_id": req.channel_id,
                    "requested": req.max_uploads,
                    "retrieved": len(rows),
                    "collected_at": datetime.now(UTC).isoformat(),
                },
                warnings=notes,
            )
    except (RuntimeError, OSError, ValueError, TimeoutError) as exc:
        notes.append(f"yt-dlp fallback failed: {type(exc).__name__}.")
    return GeneralResult(
        state="unavailable", summary="No channel upload evidence available", warnings=notes
    )


def compute_outliers(
    videos: list[dict], req: OutlierScanRequest, *, now: datetime | None = None
) -> GeneralResult:
    """Observed-view peer cohorts, not historical same-age view curves."""
    now = now or datetime.now(UTC)
    excluded = {
        "short_or_under_min_duration": 0,
        "unknown_duration": 0,
        "livestream": 0,
        "broadcast_archives_by_policy": 0,
        "unknown_views_or_date": 0,
        "exact_title_duplicate": 0,
        "outside_selected_title_family": 0,
    }
    eligible: list[dict] = []
    ambiguous_broadcasts_retained = 0
    titles = set()
    for raw in videos:
        duration = duration_seconds(raw.get("duration_seconds", raw.get("duration")))
        if duration is None:
            excluded["unknown_duration"] += 1
            continue
        if duration < req.min_duration_seconds:
            excluded["short_or_under_min_duration"] += 1
            continue
        kind = raw.get("broadcast_kind")
        active = kind in {"currently_live", "upcoming"} or raw.get("is_live_archive") is True
        if active and req.broadcast_policy != "flag_only":
            excluded["livestream"] += 1
            continue
        marked_broadcast = raw.get("broadcast_metadata_present") is True
        if req.broadcast_policy == "exclude_all_broadcast_metadata" and marked_broadcast:
            excluded["broadcast_archives_by_policy"] += 1
            continue
        date = published(raw.get("published_at"))
        views = raw.get("views")
        if date is None or type(views) is not int or views < 0 or date > now:
            excluded["unknown_views_or_date"] += 1
            continue
        title = str(raw.get("title") or "").strip().casefold()
        includes = [x.strip().casefold() for x in req.include_title_terms if x.strip()]
        excludes = [x.strip().casefold() for x in req.exclude_title_terms if x.strip()]
        if (includes and not any(x in title for x in includes)) or any(
            x in title for x in excludes
        ):
            excluded["outside_selected_title_family"] += 1
            continue
        if title and title in titles:
            excluded["exact_title_duplicate"] += 1
            continue
        if title:
            titles.add(title)
        record = dict(raw)
        if kind in {"completed_broadcast_or_premiere", "broadcast_metadata_ambiguous"}:
            ambiguous_broadcasts_retained += 1
        record["video_age_days"] = round((now - date).total_seconds() / 86400, 2)
        record["age_cohort"] = age_group(record["video_age_days"])
        record["duration_seconds"] = duration
        eligible.append(record)
    if not eligible:
        return GeneralResult(
            state="insufficient_evidence",
            summary="No comparable long-form records",
            metadata={"retrieved": len(videos), "excluded": excluded},
            warnings=["Never infer no demand from missing data."],
        )
    all_median = median(x["views"] for x in eligible)
    by_bucket = {}
    for item in eligible:
        by_bucket.setdefault(item["age_cohort"], []).append(item)
    rows = []
    for item in eligible:
        # Leave-one-out prevents a breakout from raising its own baseline.
        peers = [x["views"] for x in by_bucket[item["age_cohort"]] if x["id"] != item["id"]]
        peer_median = median(peers) if len(peers) >= req.min_peer_sample else None
        ratio = (
            round(item["views"] / peer_median, 2)
            if peer_median is not None and peer_median > 0
            else None
        )
        row = {
            "id": item["id"],
            "url": item.get("url"),
            "title": item.get("title"),
            "views": item["views"],
            "published_at": item.get("published_at"),
            "duration_seconds": item["duration_seconds"],
            "video_age_days": item["video_age_days"],
            "age_cohort": item["age_cohort"],
            "peer_sample": len(peers),
            "peer_median_current_views": peer_median,
            "coarse_age_cohort_ratio": ratio,
            "overall_median_current_views": all_median,
            "overall_ratio_diagnostic_only": (
                round(item["views"] / all_median, 2) if all_median else None
            ),
            "outlier_band": (
                "10x+"
                if ratio is not None and ratio >= 10
                else "5x+"
                if ratio is not None and ratio >= 5
                else "2x+"
                if ratio is not None and ratio >= 2
                else "below_2x"
                if ratio is not None
                else "unknown"
            ),
            "confidence": (
                "moderate"
                if ratio is not None and len(peers) >= 10
                else "limited"
                if ratio is not None
                else "insufficient"
            ),
            "historical_age_matched": False,
            "views_source": item.get("views_source") or item.get("metadata_source"),
            "broadcast_kind": item.get("broadcast_kind") or "unknown",
            "broadcast_metadata_present": item.get("broadcast_metadata_present"),
        }
        rows.append(row)

    def rank(row):
        v = row["coarse_age_cohort_ratio"]
        return (v is not None, v if v is not None else -1, row["views"])

    windows = {}
    for label, day_limit in (("last_30_days", 30), ("last_90_days", 90), ("all_sampled", None)):
        selected = [x for x in rows if day_limit is None or x["video_age_days"] <= day_limit]
        ranked = sorted(selected, key=rank, reverse=True)
        windows[label] = {
            "eligible_count": len(selected),
            "scorable_count": sum(x["coarse_age_cohort_ratio"] is not None for x in selected),
            "outliers_2x": sum(
                x["coarse_age_cohort_ratio"] is not None and x["coarse_age_cohort_ratio"] >= 2
                for x in selected
            ),
            "top": ranked[: req.max_items],
        }
    warnings = [
        "Age cohorts compare current lifetime views of similarly aged uploads; "
        "they are NOT historical Day-7/30/90 matched view counts.",
        "No final market demand or quality verdict can follow from outlier ratios alone.",
        "Title-term families are optional approximations, not verified format classification.",
        "Archived broadcast metadata may indicate a premiere or livestream. "
        "Presence alone does not justify excluding a documentary.",
    ]
    if len(eligible) < 15:
        warnings.append("Small long-form cohort: treat overall baseline as provisional.")
    return GeneralResult(
        state="partial" if len(eligible) < 15 else "available",
        summary=f"{len(eligible)} eligible long-form videos, current-view cohort ratios",
        source="observed_public_video_metrics",
        items=windows["all_sampled"]["top"],
        metadata={
            "windows": windows,
            "overall_median_current_views": all_median,
            "eligible_total": len(eligible),
            "scorable_total": sum(x["coarse_age_cohort_ratio"] is not None for x in rows),
            "raw_count": len(videos),
            "excluded": excluded,
            "broadcast_ambiguous_retained": ambiguous_broadcasts_retained,
            "broadcast_policy": req.broadcast_policy,
            "method": "leave_one_out_median_by_current_video_age_cohort",
            "title_family_terms": {
                "include": req.include_title_terms,
                "exclude": req.exclude_title_terms,
            },
            "historical_age_matched": False,
            "as_of": now.isoformat(),
        },
        warnings=warnings,
    )


async def scan(settings: Settings, req: OutlierScanRequest) -> GeneralResult:
    collected = await collect(
        settings, DeepUploadsRequest(channel_id=req.channel_id, max_uploads=req.max_uploads)
    )
    if not collected.items:
        return collected
    report = compute_outliers(collected.items, req)
    report.metadata["collection"] = collected.metadata
    report.metadata["channel_id"] = req.channel_id
    report.metadata["collection_source"] = collected.source
    report.warnings.extend(collected.warnings)
    if collected.state == "partial":
        report.state = "partial"
    return report


def register(server, settings: Settings) -> None:
    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )

    @server.tool(
        name="youtube_channel_deep_uploads",
        description="Retrieve up to 300 channel uploads using API pagination and yt-dlp fallback.",
        structured_output=True,
        annotations=annotations,
    )
    async def deep(request: DeepUploadsRequest) -> GeneralResult:
        return await collect(settings, request)

    @server.tool(
        name="youtube_channel_outliers",
        description=(
            "Find long-form current-view outliers in age-cohort baselines and 30/90-day windows. "
            "Not genuine historical same-age views; no automatic market verdicts."
        ),
        structured_output=True,
        annotations=annotations,
    )
    async def outliers(request: OutlierScanRequest) -> GeneralResult:
        return await scan(settings, request)
