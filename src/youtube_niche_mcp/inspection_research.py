"""Evidence-first multi-segment video inspection using the local Watch engine."""

from __future__ import annotations

import asyncio
from typing import Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.general_research import (
    GeneralResult,
    JobRequest,
    VideoRequest,
    video,
    watch_status,
)
from youtube_niche_mcp.outlier_research import duration_seconds

STAGE_NAMES = ("opening", "early_middle", "late_middle", "ending")
QUESTION = {
    "opening": (
        "Inspect the selected opening frames and transcript. Identify the hook, "
        "actual visual types (still photographs vs moving footage), and initial title promise. "
        "Use timestamps. State what cannot be verified."
    ),
    "early_middle": (
        "Inspect sampled frames and transcript for specific story developments, "
        "narration density, visual relevance and repetition. Cite observed timestamps."
    ),
    "late_middle": (
        "Inspect sampled frames and transcript for evidence of meaningful progression, "
        "new information, and visual diversity. Do not infer unseen scenes."
    ),
    "ending": (
        "Check sampled ending frames and transcript for a payoff to the title promise, "
        "story resolution, visuals and whether key facts are actually evidenced. Cite timestamps."
    ),
}


class PlanRequest(BaseModel):
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    duration_seconds: int | None = Field(default=None, ge=60, le=43200)
    sample_seconds: int = Field(default=60, ge=15, le=180)
    processing_mode: Literal["auto", "local_first", "local_only"] = "local_first"


class CompletedStage(BaseModel):
    stage: Literal["opening", "early_middle", "late_middle", "ending"]
    job_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class ReviewRequest(BaseModel):
    stages: list[CompletedStage] = Field(min_length=1, max_length=4)
    excerpt_chars: int = Field(default=2500, ge=200, le=7500)


def clock(sec: int) -> str:
    return f"{sec // 3600:02d}:{(sec // 60) % 60:02d}:{sec % 60:02d}"


def plan_segments(video_id: str, length: int, sample: int, mode: str = "local_first") -> list[dict]:
    """Create grounded non-overlapping sample windows when duration permits."""
    duration = max(1, length)
    width = min(sample, max(15, duration // 5))
    centers = (0, int(duration * 0.24), int(duration * 0.64), duration - width)
    result = []
    last_end = -1
    for stage, estimated in zip(STAGE_NAMES, centers, strict=True):
        start = min(max(estimated, last_end + 1), max(0, duration - width))
        end = min(duration, start + width)
        last_end = end
        result.append(
            {
                "stage": stage,
                "start": clock(start),
                "end": clock(end),
                "start_seconds": start,
                "end_seconds": end,
                "status": "planned_not_inspected",
                "watch_request": {
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "question": QUESTION[stage],
                    "start": clock(start),
                    "end": clock(end),
                    "processing_mode": mode,
                },
            }
        )
    return result


async def plan(settings: Settings, req: PlanRequest) -> GeneralResult:
    duration = req.duration_seconds
    notes = []
    title = None
    if duration is None:
        details = await video(settings, VideoRequest(video_id=req.video_id))
        if details.items:
            raw = details.items[0]
            duration = duration_seconds(raw.get("duration"))
            title = raw.get("title")
        if duration is None:
            return GeneralResult(
                state="unavailable",
                summary="Video duration unknown; provide duration_seconds or retrieve metadata.",
                source=details.source,
                warnings=details.warnings,
            )
        notes.extend(details.warnings)
    return GeneralResult(
        state="available",
        summary="Four sample inspection windows planned; no footage inspected yet.",
        source="public_video_metadata_or_supplied_duration",
        items=plan_segments(req.video_id, duration, req.sample_seconds, req.processing_mode),
        metadata={
            "video_id": req.video_id,
            "title": title,
            "duration_seconds": duration,
            "sample_seconds": req.sample_seconds,
            "processing_mode": req.processing_mode,
            "execution": (
                "Call youtube_watch_video with each watch_request, poll youtube_watch_status, "
                "retrieve youtube_watch_frames when available, then call youtube_inspection_review."
            ),
        },
        warnings=notes
        + [
            "Sampling cannot prove full-video visual quality or full narrative payoff.",
            "A transcript-only segment does not verify visual content.",
        ],
    )


async def review(req: ReviewRequest) -> GeneralResult:
    if len({stage.stage for stage in req.stages}) != len(req.stages):
        return GeneralResult(state="invalid_input", summary="Duplicate inspection stage")
    responses = await asyncio.gather(
        *(watch_status(JobRequest(job_id=s.job_id)) for s in req.stages)
    )
    items = []
    issues = []
    for stage, response in zip(req.stages, responses, strict=True):
        m = response.metadata
        nframes = int(m.get("frames_available") or 0)
        transcript = bool(m.get("transcript_available"))
        if response.state in {"running", "queued"}:
            quality = "pending"
        elif nframes > 0:
            quality = "sampled_frames_verified"
        elif response.state == "completed":
            quality = "model_report_only"
        elif transcript:
            quality = "transcript_only"
        else:
            quality = "unavailable"
        if quality in {"model_report_only", "transcript_only", "unavailable", "pending"}:
            issues.append(f"{stage.stage}: {quality}")
        items.append(
            {
                "stage": stage.stage,
                "job_id": stage.job_id,
                "status": response.state,
                "engine": m.get("engine"),
                "evidence_label": quality,
                "sampled_frames": nframes,
                "transcript_available": transcript,
                "result_excerpt": str(m.get("result") or "")[: req.excerpt_chars],
                "warnings": response.warnings,
            }
        )
    return GeneralResult(
        state="partial" if issues or len(items) < 4 else "available",
        summary=f"{len(items)} stage(s) inspected; labels distinguish verified frames from claims",
        source="local_watch_engine",
        items=items,
        metadata={
            "stage_count": len(items),
            "requested_stages": len(req.stages),
            "complete_four_stage_coverage": len(items) == 4 and not issues,
        },
        warnings=issues
        + ["Timestamped samples do not establish full-video editing quality or factual accuracy."],
    )


def register(server, settings: Settings) -> None:
    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )

    @server.tool(
        name="youtube_inspection_plan",
        description="Generate four evidence-focused video inspection windows with Watch requests.",
        structured_output=True,
        annotations=annotations,
    )
    async def inspection_plan(request: PlanRequest) -> GeneralResult:
        return await plan(settings, request)

    @server.tool(
        name="youtube_inspection_review",
        description="Merge completed Watch jobs into timestamp/evidence-labelled stage reports.",
        structured_output=True,
        annotations=annotations,
    )
    async def inspection_review(request: ReviewRequest) -> GeneralResult:
        return await review(request)
