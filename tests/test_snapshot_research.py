"""View-history snapshots are recorded, never backfilled or fabricated."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from youtube_niche_mcp import snapshot_research as snapshot
from youtube_niche_mcp.config import Settings


@pytest.mark.anyio
async def test_capture_then_read_actual_observation(monkeypatch, tmp_path):
    path = tmp_path / "views.sqlite3"
    monkeypatch.setenv("YT_RESEARCH_SNAPSHOTS_DB", str(path))
    now = datetime.now(UTC)
    pub = (now - timedelta(days=7)).isoformat()

    async def fake_api(_settings, ids):
        return [
            {
                "id": video_id,
                "views": 4321,
                "published_at": pub,
                "title": "Example public documentary",
            }
            for video_id in ids
        ]

    monkeypatch.setattr(snapshot, "api_videos", fake_api)
    settings = Settings(youtube_api_key=SecretStr("test-key"))
    result = await snapshot.capture(settings, snapshot.CaptureRequest(video_ids=["a" * 11]))
    assert result.state == "available"
    assert result.metadata["captured"] == 1
    assert path.is_file()

    historical = await snapshot.history(settings, snapshot.HistoryRequest(video_id="a" * 11))
    milestones = historical.metadata["milestones"]
    assert milestones["day_7"]["state"] == "observed_near_milestone"
    assert milestones["day_7"]["views"] == 4321
    assert milestones["day_30"]["state"] == "not_recorded"
    assert milestones["day_90"]["state"] == "not_recorded"


@pytest.mark.anyio
async def test_no_data_means_no_invented_history(monkeypatch, tmp_path):
    monkeypatch.setenv("YT_RESEARCH_SNAPSHOTS_DB", str(tmp_path / "empty.sqlite3"))
    result = await snapshot.history(Settings(), snapshot.HistoryRequest(video_id="a" * 11))
    assert result.state == "insufficient_evidence"


@pytest.mark.anyio
async def test_bad_video_identifier_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("YT_RESEARCH_SNAPSHOTS_DB", str(tmp_path / "views.sqlite3"))
    result = await snapshot.capture(Settings(), snapshot.CaptureRequest(video_ids=["../unsafe"]))
    assert result.state == "invalid_input"
    assert not (tmp_path / "views.sqlite3").exists()
