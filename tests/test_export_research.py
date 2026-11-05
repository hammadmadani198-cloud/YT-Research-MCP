"""Exported research evidence includes source links and explicit age caveat."""

import json
from pathlib import Path

import pytest

from youtube_niche_mcp import export_research as export
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.general_research import GeneralResult


@pytest.mark.anyio
async def test_json_csv_export_is_grounded(monkeypatch, tmp_path):
    monkeypatch.setenv("YT_RESEARCH_EXPORT_DIR", str(tmp_path))

    async def fake_scan(_settings, _request):
        row = {
            "id": "abcdefghijk",
            "url": "https://www.youtube.com/watch?v=abcdefghijk",
            "title": "Royal history",
            "views": 15000,
            "video_age_days": 20,
            "age_cohort": "0-30d",
            "peer_sample": 7,
            "coarse_age_cohort_ratio": 4.5,
            "historical_age_matched": False,
        }
        return GeneralResult(
            state="available",
            summary="Test evidence",
            source="youtube_data_api",
            items=[row],
            metadata={
                "windows": {"last_30_days": {"top": [row]}},
                "eligible_total": 12,
                "collection_source": "youtube_data_api",
            },
            warnings=["Historical same-age views are unavailable"],
        )

    monkeypatch.setattr(export, "scan", fake_scan)
    result = await export.export(
        Settings(), export.ExportRequest(channel_id="UC" + "x" * 22, max_uploads=100)
    )
    assert result.state == "available"
    json_path = Path(result.metadata["json_path"])
    csv_path = Path(result.metadata["csv_path"])
    assert json_path.is_file() and csv_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["items"][0]["historical_age_matched"] is False
    assert "abcdefghijk" in csv_path.read_text(encoding="utf-8-sig")
    assert result.metadata["exported_csv_rows"] == 1
