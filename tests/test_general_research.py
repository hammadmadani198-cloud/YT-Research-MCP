"""General YT Research profile does not execute legacy niche selection rules."""

import json

import pytest
from mcp import Client
from pydantic import SecretStr

from youtube_niche_mcp import general_research as g
from youtube_niche_mcp.api.client import APIError
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.domain.foundation import Outcome
from youtube_niche_mcp.server import create_server


@pytest.mark.anyio
async def test_general_profile_has_no_niche_or_watchlist_tools(monkeypatch):
    monkeypatch.setenv("YT_RESEARCH_GENERAL", "1")
    async with Client(create_server(Settings())) as client:
        tools = {tool.name for tool in (await client.list_tools()).tools}
        assert tools == {
            "youtube_search",
            "youtube_video_details",
            "youtube_channel_uploads",
            "youtube_watch_video",
            "youtube_watch_health",
            "youtube_watch_status",
            "youtube_watch_frames",
            "youtube_channel_deep_uploads",
            "youtube_channel_outliers",
            "youtube_inspection_plan",
            "youtube_inspection_review",
            "youtube_view_snapshot",
            "youtube_view_history",
            "youtube_export_outliers",
        }
        status = await client.read_resource("yt-research://status")
        data = json.loads(status.contents[0].text)
        assert data["name"] == "YT Research"
        assert data["nexlev"] == "disabled"
        assert data["niche_decision_rules"] == "disabled"


@pytest.mark.anyio
async def test_no_api_key_uses_ytdlp(monkeypatch):
    async def fake_dlp(url, max_results=10, *, single=False):
        assert url.startswith("ytsearch")
        return [{"id": "abcdefghijk", "title": "Test result", "views": 42}]

    monkeypatch.setattr(g, "via_dlp", fake_dlp)
    result = await g.search(Settings(), g.SearchRequest(query="royal history"))
    assert result.source == "yt_dlp"
    assert result.items[0]["views"] == 42


@pytest.mark.anyio
async def test_api_quota_falls_back(monkeypatch):
    class ExhaustedClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def request(self, *args, **kwargs):
            raise APIError("search.list", Outcome.QUOTA_LIMITED, "quotaExceeded")

    async def fake_dlp(url, max_results=10, *, single=False):
        return [{"id": "abcdefghijk", "title": "Fallback video"}]

    monkeypatch.setattr(g, "YouTubeClient", ExhaustedClient)
    monkeypatch.setattr(g, "via_dlp", fake_dlp)
    settings = Settings(youtube_api_key=SecretStr("test-key"))
    result = await g.search(settings, g.SearchRequest(query="royal history"))
    assert result.source == "yt_dlp"
    assert "quota" in " ".join(result.warnings).lower()


@pytest.mark.anyio
async def test_partial_api_metadata_is_supplemented(monkeypatch):
    async def fake_dlp(url, max_results=10, *, single=False):
        return [{"id": "abcdefghijk", "views": 9000}]

    monkeypatch.setattr(g, "via_dlp", fake_dlp)
    records = [{"id": "abcdefghijk", "views": None, "title": "A"}]
    found, count = await g.enrich_missing(records)
    assert count == 1 and found[0]["views"] == 9000
    assert found[0]["views_source"] == "yt_dlp"


@pytest.mark.anyio
async def test_watch_transcript_only_is_not_reported_as_visual_success(monkeypatch):
    monkeypatch.setattr(
        g,
        "_watch_helper",
        lambda _operation, _args: {
            "job_id": "a" * 32,
            "status": "completed",
            "engine": "local",
            "frames_available": 0,
            "transcript_available": True,
            "result": "Transcript without video frames.",
        },
    )
    result = await g.watch_status(g.JobRequest(job_id="a" * 32))
    assert result.state == "partial"
    assert result.metadata["visual_evidence_available"] is False
    assert "visual" in " ".join(result.warnings).lower()


@pytest.mark.anyio
async def test_watch_visual_result_is_not_downgraded(monkeypatch):
    monkeypatch.setattr(
        g,
        "_watch_helper",
        lambda _operation, _args: {
            "job_id": "b" * 32,
            "status": "completed",
            "engine": "local",
            "frames_available": 5,
            "transcript_available": True,
        },
    )
    result = await g.watch_status(g.JobRequest(job_id="b" * 32))
    assert result.state == "completed"
    assert result.metadata["visual_evidence_available"] is True


def test_nonzero_ytdlp_exit_cannot_be_reported_as_success(monkeypatch):
    class FakeProcess:
        returncode = 1
        stdout = '{"entries": [{"id": "abcdefghijk"}]}'
        stderr = "403 Forbidden"

    monkeypatch.setattr(g.subprocess, "run", lambda *args, **kwargs: FakeProcess())
    with pytest.raises(RuntimeError, match="yt_dlp_nonzero_exit"):
        g._run_json(["fake-ytdlp"])


@pytest.mark.anyio
async def test_live_mcp_search_response_without_key(monkeypatch):
    async def fake_dlp(url, max_results=10, *, single=False):
        return [{"id": "abcdefghijk", "title": "Public title", "views": 100}]

    monkeypatch.setattr(g, "via_dlp", fake_dlp)
    monkeypatch.setenv("YT_RESEARCH_GENERAL", "1")
    async with Client(create_server(Settings())) as client:
        reply = await client.call_tool(
            "youtube_search", {"request": {"query": "Queen Victoria", "max_results": 3}}
        )
        assert not reply.is_error
        assert reply.structured_content["source"] == "yt_dlp"


@pytest.mark.anyio
async def test_watch_url_rejects_non_youtube_hosts():
    result = await g.watch(g.WatchRequest(url="https://youtube.com.evil.test/video"))
    assert result.state == "invalid_input"


@pytest.mark.anyio
async def test_watch_local_first_mode_is_forwarded_to_local_engine(monkeypatch):
    captured = {}

    def fake_helper(operation, args):
        captured["operation"] = operation
        captured["args"] = args
        return {"job_id": "a" * 32, "status": "queued"}

    monkeypatch.setattr(g, "_watch_helper", fake_helper)
    result = await g.watch(
        g.WatchRequest(
            url="https://www.youtube.com/watch?v=N7JanqWb9W0",
            start="00:00:00",
            end="00:00:20",
            processing_mode="local_first",
        )
    )
    assert result.state == "queued"
    assert captured["operation"] == "submit"
    assert captured["args"][-1] == "local_first"


@pytest.mark.anyio
async def test_model_only_report_does_not_claim_verified_frames(monkeypatch):
    monkeypatch.setattr(
        g,
        "_watch_helper",
        lambda *_: {
            "job_id": "b" * 32,
            "status": "completed",
            "engine": "gemini",
            "frames_available": 0,
            "result": "Video interpreted by remote model",
        },
    )
    result = await g.watch_status(g.JobRequest(job_id="b" * 32))
    assert result.metadata["visual_evidence_available"] is False
    assert result.metadata["ai_video_report_available"] is True


@pytest.mark.anyio
async def test_mcp_watch_tool_exposes_processing_mode(monkeypatch):
    captured = {}

    def fake_helper(operation, args):
        captured["args"] = args
        return {"job_id": "d" * 32, "status": "queued"}

    monkeypatch.setattr(g, "_watch_helper", fake_helper)
    monkeypatch.setenv("YT_RESEARCH_GENERAL", "1")
    async with Client(create_server(Settings())) as client:
        result = await client.call_tool(
            "youtube_watch_video",
            {
                "request": {
                    "url": "https://www.youtube.com/watch?v=N7JanqWb9W0",
                    "start": "00:00:00",
                    "end": "00:00:20",
                    "processing_mode": "local_first",
                }
            },
        )
    assert not result.is_error
    assert captured["args"][-1] == "local_first"
