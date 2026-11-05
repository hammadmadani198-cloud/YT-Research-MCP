"""Persist actual observed public video views for future historical age-matched research."""

from __future__ import annotations

import asyncio
import os
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from youtube_niche_mcp.api.client import APIError
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.general_research import GeneralResult, api_videos, via_dlp
from youtube_niche_mcp.outlier_research import published


class CaptureRequest(BaseModel):
    video_ids: list[str] = Field(min_length=1, max_length=50)


class HistoryRequest(BaseModel):
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    tolerance_days: float = Field(default=1.0, ge=0.1, le=7.0)


def location(settings: Settings) -> Path:
    return Path(
        os.getenv(
            "YT_RESEARCH_SNAPSHOTS_DB",
            str(settings.db_path.parent / "yt_research_snapshots.sqlite3"),
        )
    )


def _store(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS video_view_snapshots (
                video_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                views INTEGER NOT NULL CHECK (views >= 0),
                published_at TEXT,
                source TEXT NOT NULL,
                PRIMARY KEY (video_id, observed_at)
            )"""
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS ix_snapshot_video ON "
            "video_view_snapshots(video_id, observed_at)"
        )
        for entry in entries:
            db.execute(
                "INSERT OR IGNORE INTO video_view_snapshots "
                "(video_id, observed_at, views, published_at, source) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    entry["id"],
                    entry["observed_at"],
                    entry["views"],
                    entry.get("published_at"),
                    entry["source"],
                ),
            )
        db.commit()


def _read(path: Path, video_id: str) -> list[dict]:
    if not path.is_file():
        return []
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        try:
            rows = db.execute(
                "SELECT observed_at, views, published_at, source "
                "FROM video_view_snapshots WHERE video_id=? "
                "ORDER BY observed_at DESC LIMIT 2000",
                (video_id,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [
        {"observed_at": a, "views": b, "published_at": c, "source": d} for a, b, c, d in rows[::-1]
    ]


async def capture(settings: Settings, req: CaptureRequest) -> GeneralResult:
    ids = list(dict.fromkeys(req.video_ids))
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{11}", item) for item in ids):
        return GeneralResult(state="invalid_input", summary="Invalid YouTube video ID")
    records: dict[str, dict] = {}
    notes: list[str] = []
    if settings.youtube_api_key:
        try:
            for row in await api_videos(settings, ids):
                if isinstance(row.get("views"), int) and row["views"] >= 0:
                    row["source"] = "youtube_data_api"
                    records[row["id"]] = row
        except (APIError, ValueError, RuntimeError, TimeoutError) as exc:
            notes.append(f"API unavailable: {type(exc).__name__}; trying yt-dlp.")
    else:
        notes.append("No YouTube API key; attempting bounded yt-dlp fallback.")
    missing = [id_ for id_ in ids if id_ not in records]
    if missing:
        # Keep fallback bounded: 10 direct videos, at most three concurrent processes.
        semaphore = asyncio.Semaphore(3)

        async def resolve(video_id: str):
            async with semaphore:
                try:
                    out = await via_dlp(f"https://www.youtube.com/watch?v={video_id}", single=True)
                    return out[0] if out and out[0].get("views") is not None else None
                except (OSError, RuntimeError, ValueError, TimeoutError):
                    return None

        samples = await asyncio.gather(*(resolve(id_) for id_ in missing[:10]))
        for raw in samples:
            if raw and isinstance(raw.get("views"), int) and raw["views"] >= 0:
                raw["source"] = "yt_dlp"
                records[raw["id"]] = raw
        if len(missing) > 10:
            notes.append("yt-dlp fallback capped at 10 video requests.")
    moment = datetime.now(UTC).isoformat()
    entries = [
        {
            "id": item["id"],
            "views": item["views"],
            "published_at": item.get("published_at"),
            "source": item["source"],
            "observed_at": moment,
        }
        for item in records.values()
    ]
    if not entries:
        return GeneralResult(
            state="unavailable", summary="No public view snapshots captured", warnings=notes
        )
    path = location(settings)
    try:
        await asyncio.to_thread(_store, path, entries)
    except (OSError, sqlite3.Error):
        return GeneralResult(
            state="unavailable",
            summary="Snapshot database write failed",
            warnings=notes,
        )
    return GeneralResult(
        state="partial" if len(entries) < len(ids) else "available",
        summary=f"{len(entries)} actual public view snapshots captured",
        source="youtube_data_api_and_or_yt_dlp",
        items=entries,
        metadata={"db_path": str(path), "captured": len(entries), "requested": len(ids)},
        warnings=notes
        + [
            "A snapshot records current views only; past Day-7/30/90 views cannot be reconstructed."
        ],
    )


async def history(settings: Settings, req: HistoryRequest) -> GeneralResult:
    path = location(settings)
    try:
        entries = await asyncio.to_thread(_read, path, req.video_id)
    except (OSError, sqlite3.Error):
        entries = []
    if not entries:
        return GeneralResult(
            state="insufficient_evidence",
            summary="No stored observations for video",
        )
    milestones = {}
    for target in (7, 30, 90):
        candidates = []
        for x in entries:
            obs, pub = published(x["observed_at"]), published(x.get("published_at"))
            if obs and pub and obs >= pub:
                age = (obs - pub).total_seconds() / 86400
                if abs(age - target) <= req.tolerance_days:
                    candidates.append((abs(age - target), age, x))
        best = min(candidates, key=lambda v: v[0]) if candidates else None
        milestones[f"day_{target}"] = (
            {
                "state": "observed_near_milestone",
                "views": best[2]["views"],
                "actual_video_age_days": round(best[1], 3),
                "observed_at": best[2]["observed_at"],
                "source": best[2]["source"],
            }
            if best
            else {"state": "not_recorded"}
        )
    return GeneralResult(
        state="available",
        summary=f"{len(entries)} genuine stored view observations",
        source="local_snapshot_database",
        items=entries[-100:],
        metadata={
            "video_id": req.video_id,
            "total_observations": len(entries),
            "milestones": milestones,
            "tolerance_days": req.tolerance_days,
            "db_path": str(path),
        },
        warnings=[
            "Age milestone estimates use actual stored timestamps and stated tolerance. "
            "No backfilled historical views."
        ],
    )


def register(server, settings: Settings) -> None:
    @server.tool(
        name="youtube_view_snapshot",
        description="Store views for up to 50 videos, using API first and yt-dlp fallback.",
        structured_output=True,
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def snapshot(request: CaptureRequest) -> GeneralResult:
        return await capture(settings, request)

    @server.tool(
        name="youtube_view_history",
        description="Read saved observations and actual near-Day-7/30/90 view checkpoints.",
        structured_output=True,
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
    )
    async def view_history(request: HistoryRequest) -> GeneralResult:
        return await history(settings, request)
