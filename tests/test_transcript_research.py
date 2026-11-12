"""Independent caption retrieval: validation, pagination, and fallback."""

import pytest

from youtube_niche_mcp import transcript_research as t


def test_video_url_allowlist():
    assert t._resolve_id("https://www.youtube.com/watch?v=abcdefghijk&t=12") == "abcdefghijk"
    assert t._resolve_id("https://youtu.be/abcdefghijk") == "abcdefghijk"
    assert t._resolve_id("https://www.youtube.com/shorts/abcdefghijk") == "abcdefghijk"
    assert t._resolve_id("abcdefghijk") == "abcdefghijk"
    assert t._resolve_id("http://youtu.be/abcdefghijk") is None
    assert t._resolve_id("https://youtube.com.evil.test/watch?v=abcdefghijk") is None


def test_vtt_parser_and_srt_clock():
    text = (
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nHello &amp; welcome\n\n"
        "00:00:02.500 --> 00:00:03.000\n<i>Second</i> line\n"
    )
    rows = t._parse_vtt(text)
    assert [r["text"] for r in rows] == ["Hello & welcome", "Second line"]
    assert rows[0]["duration"] == 1.5
    assert t._clock(62.25) == "00:01:02,250"


@pytest.mark.anyio
async def test_primary_success_and_pagination(monkeypatch):
    calls = []

    def primary(video_id, langs):
        calls.append(video_id)
        return (
            [
                {"start": 0.0, "duration": 1.0, "text": "One"},
                {"start": 1.0, "duration": 2.0, "text": "Two"},
            ],
            "en",
            "manual",
        )

    monkeypatch.setattr(t, "_primary", primary)
    result = await t.get_transcript(
        t.TranscriptRequest(video_id="https://youtu.be/abcdefghijk", limit=1)
    )
    assert result.state == "ok"
    assert calls == ["abcdefghijk"]
    assert result.metadata["next_offset"] == 1
    assert result.items[0]["text"] == "One"


@pytest.mark.anyio
async def test_fallback_and_srt(monkeypatch):
    def broken(*args):
        raise RuntimeError("blocked")

    monkeypatch.setattr(t, "_primary", broken)
    monkeypatch.setattr(
        t,
        "_fallback",
        lambda *args: ([{"start": 1.0, "duration": 2.0, "text": "Hello"}], "en", "automatic"),
    )
    result = await t.get_transcript(
        t.TranscriptRequest(video_id="abcdefghijk", output_format="srt")
    )
    assert result.source == "yt_dlp"
    assert "00:00:01,000 --> 00:00:03,000" in result.metadata["content"]
    assert result.items == []


@pytest.mark.anyio
async def test_both_providers_fail_without_fabrication(monkeypatch):
    monkeypatch.setattr(t, "_primary", lambda *args: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(t, "_fallback", lambda *args: (_ for _ in ()).throw(RuntimeError()))
    result = await t.get_transcript(t.TranscriptRequest(video_id="abcdefghijk"))
    assert result.state == "unavailable"
    assert not result.items


@pytest.mark.anyio
async def test_rejects_untrusted_url(monkeypatch):
    monkeypatch.setattr(t, "_primary", lambda *args: pytest.fail("Should never call primary"))
    result = await t.get_transcript(
        t.TranscriptRequest(video_id="https://bad.example/watch?v=abcdefghijk")
    )
    assert result.state == "invalid_input"


def test_sanitized_provider_reason_codes():
    assert t._ytdlp_code("HTTP Error 429: Too Many Requests", "", 1) == "rate_limited"
    assert t._ytdlp_code("HTTP Error 403: Forbidden", "", 1) == "access_denied"
    assert t._ytdlp_code("sign in to confirm", "", 1) == "authentication_required"
    assert t._ytdlp_code("", "no subtitles", 0) == "captions_unavailable"
    assert t._error_code(TimeoutError()) == "timeout"
    assert t._error_code(t.CaptionProviderError("rate_limited")) == "rate_limited"
    assert t._error_code(RuntimeError("token=secret-value")) == "provider_error"


@pytest.mark.anyio
async def test_both_failures_report_codes_not_sensitive_text(monkeypatch):
    def blocked(*args):
        raise RuntimeError("Too Many Requests 429; secret=must-never-leak")

    def other(*args):
        raise t.CaptionProviderError("captions_unavailable")

    monkeypatch.setattr(t, "_primary", blocked)
    monkeypatch.setattr(t, "_fallback", other)
    result = await t.get_transcript(t.TranscriptRequest(video_id="abcdefghijk"))
    assert result.state == "unavailable"
    assert result.metadata["provider_diagnostics"] == [
        {"provider": "youtube_transcript_api", "reason": "rate_limited"},
        {"provider": "yt_dlp", "reason": "captions_unavailable"},
    ]
    assert "must-never-leak" not in result.model_dump_json()


@pytest.mark.anyio
async def test_fallback_success_retains_primary_failure_code(monkeypatch):
    def primary(*args):
        raise TimeoutError("sensitive provider message")

    monkeypatch.setattr(t, "_primary", primary)
    monkeypatch.setattr(
        t,
        "_fallback",
        lambda *args: ([{"start": 1.0, "duration": 1.0, "text": "Example"}], "en", "unknown"),
    )
    result = await t.get_transcript(t.TranscriptRequest(video_id="abcdefghijk"))
    assert result.state == "ok" and result.source == "yt_dlp"
    assert result.metadata["provider_diagnostics"] == [
        {"provider": "youtube_transcript_api", "reason": "timeout"}
    ]
