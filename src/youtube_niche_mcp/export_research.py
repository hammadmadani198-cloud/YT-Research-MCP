"""Evidence export for public channel outlier research."""

from __future__ import annotations

import asyncio
import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.general_research import GeneralResult
from youtube_niche_mcp.outlier_research import OutlierScanRequest, scan


class ExportRequest(BaseModel):
    channel_id: str = Field(pattern=r"^UC[A-Za-z0-9_-]{22}$")
    max_uploads: int = Field(default=100, ge=10, le=300)


def _save(settings: Settings, report: GeneralResult, channel_id: str) -> dict:
    root = Path(os.getenv("YT_RESEARCH_EXPORT_DIR", str(settings.db_path.parent / "yt_exports")))
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    prefix = root / f"{stamp}_{channel_id}"
    json_file = prefix.with_suffix(".json")
    csv_file = prefix.with_suffix(".csv")
    json_file.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    columns = [
        "window",
        "id",
        "url",
        "title",
        "published_at",
        "views",
        "video_age_days",
        "age_cohort",
        "duration_seconds",
        "peer_sample",
        "peer_median_current_views",
        "coarse_age_cohort_ratio",
        "outlier_band",
        "confidence",
        "historical_age_matched",
    ]

    count = 0
    with csv_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for window, data in report.metadata.get("windows", {}).items():
            for entry in data.get("top", []):
                writer.writerow({"window": window, **entry})
                count += 1
    return {
        "json_path": str(json_file),
        "csv_path": str(csv_file),
        "exported_csv_rows": count,
    }


async def export(settings: Settings, request: ExportRequest) -> GeneralResult:
    result = await scan(
        settings,
        OutlierScanRequest(
            channel_id=request.channel_id,
            max_uploads=request.max_uploads,
            max_items=50,
        ),
    )
    if not result.items:
        return result
    try:
        paths = await asyncio.to_thread(_save, settings, result, request.channel_id)

    except OSError:
        return GeneralResult(
            state="unavailable",
            summary="Unable to save research evidence",
            warnings=result.warnings,
        )
    return GeneralResult(
        state=result.state,
        summary="Outlier evidence exported to local JSON and CSV",
        source=result.source,
        metadata=paths,
        warnings=result.warnings,
    )


def register(server, settings: Settings) -> None:
    @server.tool(
        name="youtube_export_outliers",
        description="Save outlier evidence with video links and cohorts as JSON/CSV.",
        structured_output=True,
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def export_tool(request: ExportRequest) -> GeneralResult:
        return await export(settings, request)
