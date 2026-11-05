"""General public YouTube research: first-party API, yt-dlp fallback, local Watch engine.

No niche eligibility, F1-F23 decisions, NexLev provider, or third-party MCP calls.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from mcp.types import ImageContent, TextContent, ToolAnnotations
from pydantic import BaseModel, Field

from youtube_niche_mcp.api.client import APIError, YouTubeClient
from youtube_niche_mcp.config import Settings


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=250)
    max_results: int = Field(default=10, ge=1, le=25)
    order: Literal["relevance", "date", "viewCount"] = "relevance"
    published_after: str | None = Field(default=None, max_length=30)
    published_before: str | None = Field(default=None, max_length=30)


class VideoRequest(BaseModel):
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")


class ChannelRequest(BaseModel):
    channel_id: str = Field(pattern=r"^UC[A-Za-z0-9_-]{22}$")
    max_results: int = Field(default=10, ge=1, le=25)


class WatchRequest(BaseModel):
    url: str = Field(max_length=2048)
    question: str = Field(default="Summarize visuals and speech with timestamps.", max_length=4000)
    start: str = Field(default="", max_length=16)
    end: str = Field(default="", max_length=16)
    processing_mode: Literal["auto", "local_first", "local_only"] = "auto"


class HealthRequest(BaseModel):
    pass


class JobRequest(BaseModel):
    job_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class FrameRequest(BaseModel):
    job_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    offset: int = Field(default=0, ge=0, le=500)
    limit: int = Field(default=4, ge=1, le=6)


class GeneralResult(BaseModel):
    state: str
    summary: str
    source: str = "none"
    items: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


def video_item(item: dict) -> dict:
    snippet, stats, details = (
        item.get("snippet") or {},
        item.get("statistics") or {},
        item.get("contentDetails") or {},
    )
    vid = item.get("id")
    if isinstance(vid, dict):
        vid = vid.get("videoId")
    duration = details.get("duration")
    try:
        views = int(stats["viewCount"]) if stats.get("viewCount") is not None else None
    except (ValueError, TypeError):
        views = None
    return {
        "id": vid,
        "title": snippet.get("title"),
        "channel": snippet.get("channelTitle"),
        "channel_id": snippet.get("channelId"),
        "published_at": snippet.get("publishedAt"),
        "views": views,
        "duration": duration,
        "url": f"https://www.youtube.com/watch?v={vid}" if vid else None,
    }


def dlp_item(item: dict) -> dict:
    vid = item.get("id")
    date = item.get("upload_date")
    if isinstance(date, str) and re.fullmatch(r"\d{8}", date):
        date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    return {
        "id": vid,
        "title": item.get("title"),
        "channel": item.get("channel") or item.get("uploader"),
        "channel_id": item.get("channel_id"),
        "published_at": date or item.get("release_date"),
        "views": item.get("view_count"),
        "duration": item.get("duration"),
        "url": item.get("webpage_url")
        or (f"https://www.youtube.com/watch?v={vid}" if vid else None),
    }


def _run_json(command: list[str], timeout: int = 35) -> dict:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError("yt_dlp_nonzero_exit")
    if not result.stdout.strip():
        raise RuntimeError("no usable metadata")
    return json.loads(result.stdout)


async def via_dlp(url: str, max_results: int = 10, *, single: bool = False) -> list[dict]:
    executable = shutil.which("yt-dlp")
    if not executable:
        raise RuntimeError("yt-dlp not installed")
    args = [
        executable,
        "--no-config",
        "--no-warnings",
        "--skip-download",
        "--dump-single-json",
        "--socket-timeout",
        "8",
        "--retries",
        "0",
        "--extractor-retries",
        "0",
    ]
    if single:
        args.append("--no-playlist")
    else:
        args += ["--flat-playlist", "--playlist-end", str(max_results)]
    args.append(url)
    raw = await asyncio.to_thread(_run_json, args)
    entries = [raw] if single else (raw.get("entries") or [])
    return [dlp_item(entry) for entry in entries if isinstance(entry, dict)][:max_results]


async def api_videos(settings: Settings, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    async with YouTubeClient(settings) as client:
        page = await client.request(
            "videos.list", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[:50])}
        )
    return [video_item(item) for item in page.body["items"]]


async def enrich_missing(records: list[dict]) -> tuple[list[dict], int]:
    """Supplement up to three missing public view counts without replacing API evidence."""
    candidates = [
        record
        for record in records
        if record.get("views") is None
        and isinstance(record.get("id"), str)
        and re.fullmatch(r"[A-Za-z0-9_-]{11}", record["id"])
    ][:3]

    async def resolve(record: dict) -> int | None:
        try:
            extra = await via_dlp(f"https://www.youtube.com/watch?v={record['id']}", single=True)
            return extra[0].get("views") if extra else None
        except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired):
            return None

    values = await asyncio.gather(*(resolve(record) for record in candidates))
    filled = 0
    for record, value in zip(candidates, values, strict=True):
        if value is not None:
            record["views"] = value
            record["views_source"] = "yt_dlp"
            filled += 1
    return records, filled


async def search(settings: Settings, req: SearchRequest) -> GeneralResult:
    notes: list[str] = []
    if settings.youtube_api_key:
        try:
            params = {
                "part": "snippet",
                "q": req.query,
                "maxResults": req.max_results,
                "type": "video",
                "order": req.order,
            }
            if req.published_after:
                params["publishedAfter"] = req.published_after
            if req.published_before:
                params["publishedBefore"] = req.published_before
            async with YouTubeClient(settings) as client:
                page = await client.request("search.list", params)
            ids = [item.get("id", {}).get("videoId") for item in page.body["items"]]
            ids = [v for v in ids if isinstance(v, str)]
            records = await api_videos(settings, ids)
            if records:
                missing = [r for r in records if r.get("views") is None]
                if missing:
                    records, filled = await enrich_missing(records)
                    notes.append(
                        f"{filled} missing view counts supplemented using yt-dlp; "
                        "remaining missing values are unknown."
                    )
                return GeneralResult(
                    state="available",
                    summary=f"{len(records)} public videos from YouTube Data API",
                    source="youtube_data_api",
                    items=records,
                    metadata={"query": req.query, "order": req.order},
                    warnings=notes,
                )
            notes.append("API returned no hydrated videos; trying yt-dlp.")
        except APIError as exc:
            notes.append(f"YouTube API {exc.outcome.value}; trying yt-dlp.")
        except (ValueError, RuntimeError, TimeoutError):
            notes.append("YouTube API response unavailable; trying yt-dlp.")
    else:
        notes.append("YouTube API key not configured; trying yt-dlp.")
    try:
        records = await via_dlp(f"ytsearch{req.max_results}:{req.query}", req.max_results)
        # yt-dlp search is not an API-equivalent date/order filter.
        if req.published_after or req.published_before or req.order != "relevance":
            notes.append(
                "yt-dlp fallback search cannot guarantee the requested date/order filters."
            )
        if records:
            return GeneralResult(
                state="partial" if notes else "available",
                summary=f"{len(records)} public search matches from yt-dlp",
                source="yt_dlp",
                items=records,
                metadata={"query": req.query},
                warnings=notes,
            )
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        notes.append(f"yt-dlp unavailable: {type(exc).__name__}.")
    return GeneralResult(state="unavailable", summary="No search data collected.", warnings=notes)


async def video(settings: Settings, req: VideoRequest) -> GeneralResult:
    notes = []
    items = []
    if settings.youtube_api_key:
        try:
            items = await api_videos(settings, [req.video_id])
            if items and items[0].get("views") is not None:
                return GeneralResult(
                    state="available",
                    summary="Video metadata retrieved",
                    source="youtube_data_api",
                    items=items,
                )
            notes.append("Missing public video or views data; trying yt-dlp.")
        except APIError as exc:
            notes.append(f"API {exc.outcome.value}; trying yt-dlp.")
    try:
        items = await via_dlp(f"https://www.youtube.com/watch?v={req.video_id}", single=True)
        if items:
            return GeneralResult(
                state="available" if items[0].get("views") is not None else "partial",
                summary="Video metadata retrieved using yt-dlp",
                source="yt_dlp",
                items=items,
                warnings=notes,
            )
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        notes.append(f"yt-dlp unavailable: {type(exc).__name__}.")
    if items:
        return GeneralResult(
            state="partial",
            summary="Partial video metadata from API",
            source="youtube_data_api",
            items=items,
            warnings=notes,
        )
    return GeneralResult(state="unavailable", summary="Video data unavailable", warnings=notes)


async def channel(settings: Settings, req: ChannelRequest) -> GeneralResult:
    notes = []
    if settings.youtube_api_key:
        try:
            async with YouTubeClient(settings) as client:
                page = await client.request(
                    "channels.list",
                    {"part": "contentDetails,snippet,statistics", "id": req.channel_id},
                )
                found = page.body["items"]
                uploads = (
                    (found[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"))
                    if found
                    else None
                )
                if uploads:
                    page = await client.request(
                        "playlistItems.list",
                        {
                            "part": "snippet,contentDetails",
                            "playlistId": uploads,
                            "maxResults": req.max_results,
                        },
                    )
                    ids = [x.get("contentDetails", {}).get("videoId") for x in page.body["items"]]
                    ids = [x for x in ids if x]
                else:
                    ids = []
            items = await api_videos(settings, ids)
            if items:
                return GeneralResult(
                    state="available",
                    summary="Recent channel uploads",
                    source="youtube_data_api",
                    items=items,
                    metadata={"channel_id": req.channel_id},
                )
            notes.append("No channel uploads from API; trying yt-dlp.")
        except APIError as exc:
            notes.append(f"API {exc.outcome.value}; trying yt-dlp.")
    try:
        items = await via_dlp(
            f"https://www.youtube.com/channel/{req.channel_id}/videos", req.max_results
        )
        if items:
            return GeneralResult(
                state="partial" if any(x.get("views") is None for x in items) else "available",
                summary="Channel uploads from yt-dlp",
                source="yt_dlp",
                items=items,
                warnings=notes,
            )
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        notes.append(f"yt-dlp unavailable: {type(exc).__name__}.")
    return GeneralResult(state="unavailable", summary="Channel data unavailable", warnings=notes)


WATCH_ROOT = Path(os.getenv("YT_RESEARCH_WATCH_ROOT", r"D:\LocalMCPs\WatchMCP"))


def _watch_helper(operation: str, args: list[str]) -> dict:
    py = WATCH_ROOT / ".venv" / "Scripts" / "python.exe"
    if not py.is_file():
        raise FileNotFoundError("Local Watch Python environment unavailable")
    script = (
        "import json,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "from job_manager import submit,lookup;"
        "print(json.dumps(submit(*sys.argv[3:]) if sys.argv[2]=='submit' "
        "else lookup(sys.argv[3])))"
    )
    raw = _run_json([str(py), "-c", script, str(WATCH_ROOT), operation, *args], timeout=25)
    return raw


def watch_health() -> GeneralResult:
    """Read local Watch availability without touching a third-party MCP endpoint."""
    py = WATCH_ROOT / ".venv" / "Scripts" / "python.exe"
    if not py.is_file():
        return GeneralResult(state="unavailable", summary="Watch Python missing")
    script = (
        "import json,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "from server import watch_health;"
        "print(watch_health())"
    )
    try:
        data = _run_json([str(py), "-c", script, str(WATCH_ROOT)], timeout=15)
        return GeneralResult(
            state=data.get("status", "unknown"),
            summary="Local Watch engine readiness",
            source="local_watch_engine",
            metadata=data,
        )
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        return GeneralResult(state="unavailable", summary="Watch health unavailable")


def _allowed_watch_url(url: str) -> bool:
    from urllib.parse import urlsplit

    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"www.youtube.com", "youtube.com", "youtu.be", "m.youtube.com"}
        and not parsed.username
        and not parsed.password
    )


async def watch(req: WatchRequest) -> GeneralResult:
    if not _allowed_watch_url(req.url):
        return GeneralResult(state="invalid_input", summary="HTTPS YouTube URL required")
    if any(s and not re.fullmatch(r"[0-9:.]{1,16}", s) for s in (req.start, req.end)):
        return GeneralResult(state="invalid_input", summary="Invalid timestamps")
    try:
        data = await asyncio.to_thread(
            _watch_helper,
            "submit",
            [req.url, req.question, req.start, req.end, req.processing_mode],
        )
        return GeneralResult(
            state="queued",
            summary="Local Watch video job queued",
            source="local_watch_engine",
            metadata=data,
        )
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return GeneralResult(
            state="unavailable",
            summary="Local Watch engine unavailable",
            warnings=[type(exc).__name__],
        )


async def watch_status(req: JobRequest) -> GeneralResult:
    try:
        data = await asyncio.to_thread(_watch_helper, "status", [req.job_id])
        # Watch's "completed" can mean transcript-only when video frames could not be fetched.
        transcript_only = (
            data.get("status") == "completed"
            and data.get("engine") == "local"
            and int(data.get("frames_available") or 0) == 0
        )
        warnings = []
        if transcript_only:
            warnings.append("No verified visual frames. Transcript-only analysis is incomplete.")
        data["visual_evidence_available"] = bool(data.get("frames_available"))
        data["ai_video_report_available"] = bool(
            data.get("engine") in {"gemini", "nvidia_direct", "openrouter"}
            and data.get("status") == "completed"
        )
        return GeneralResult(
            state="partial" if transcript_only else data.get("status", "unknown"),
            summary=(
                "Video report has no visual evidence; transcript-only"
                if transcript_only
                else "Local video-analysis job status"
            ),
            source="local_watch_engine",
            metadata=data,
            warnings=warnings,
        )
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return GeneralResult(
            state="unavailable",
            summary="Watch job status unavailable",
            warnings=[type(exc).__name__],
        )


def watch_frames(req: FrameRequest) -> list[TextContent | ImageContent]:
    """Return images from the local Watch engine without calling its MCP endpoint."""
    path = WATCH_ROOT / "jobs" / f"{req.job_id}.json"
    helper = WATCH_ROOT / "fallback_manager.py"
    if not path.is_file() or not helper.is_file():
        return [TextContent(type="text", text="Local Watch frames unavailable.")]
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("yt_research_watch_fallback", helper)
        if spec is None or spec.loader is None:
            raise RuntimeError("Watch fallback is not importable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.get_frame_contents(job, req.offset, req.limit)
    except (OSError, ValueError, RuntimeError, TypeError):
        return [TextContent(type="text", text="Unable to load local sampled frames.")]


def register(server, settings: Settings) -> None:
    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )

    @server.tool(
        name="youtube_search",
        description="Search public YouTube: Data API first, yt-dlp fallback. No niche verdicts.",
        structured_output=True,
        annotations=annotations,
    )
    async def do_search(request: SearchRequest) -> GeneralResult:
        return await search(settings, request)

    @server.tool(
        name="youtube_video_details",
        description="Get public video metadata using official API, fallback to yt-dlp.",
        structured_output=True,
        annotations=annotations,
    )
    async def do_video(request: VideoRequest) -> GeneralResult:
        return await video(settings, request)

    @server.tool(
        name="youtube_channel_uploads",
        description="Get recent uploads via official API, fallback yt-dlp.",
        structured_output=True,
        annotations=annotations,
    )
    async def do_channel(request: ChannelRequest) -> GeneralResult:
        return await channel(settings, request)

    @server.tool(
        name="youtube_watch_health",
        description="Check local Watch video analysis readiness without calling another MCP.",
        structured_output=True,
        annotations=annotations,
    )
    async def do_watch_health(request: HealthRequest) -> GeneralResult:
        return await asyncio.to_thread(watch_health)

    @server.tool(
        name="youtube_watch_video",
        description="Queue video analysis on local Watch engine, not another MCP.",
        structured_output=True,
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def do_watch(request: WatchRequest) -> GeneralResult:
        return await watch(request)

    @server.tool(
        name="youtube_watch_frames",
        description="Return local Watch sampled frames as timestamped images.",
        structured_output=False,
        annotations=annotations,
    )
    async def do_watch_frames(request: FrameRequest) -> list[TextContent | ImageContent]:
        return await asyncio.to_thread(watch_frames, request)

    @server.tool(
        name="youtube_watch_status",
        description="Read status and findings of local Watch video job.",
        structured_output=True,
        annotations=annotations,
    )
    async def do_watch_status(request: JobRequest) -> GeneralResult:
        return await watch_status(request)
