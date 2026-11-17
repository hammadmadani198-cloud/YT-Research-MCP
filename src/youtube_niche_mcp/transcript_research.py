"""Timestamped public captions; independent of the Watch video engine."""

from __future__ import annotations

import asyncio
import html
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, Field

from youtube_niche_mcp.general_research import GeneralResult

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
LANGUAGE = re.compile(r"^[a-zA-Z]{2,3}(?:[-_][a-zA-Z0-9]{2,8}){0,2}$")
TIMESTAMP = re.compile(r"(?:(\d{2}):)?(\d{2}):(\d{2})[.,](\d{3})")


class CaptionProviderError(RuntimeError):
    """Only a fixed non-sensitive reason code leaves the provider boundary."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _error_code(error: Exception) -> str:
    if isinstance(error, CaptionProviderError):
        return error.reason
    name = type(error).__name__
    if name == "IpBlocked":
        return "ip_blocked"
    if name in {"RequestBlocked", "FailedToCreateConsentCookie"}:
        return "request_blocked"
    if name in {"NoTranscriptFound", "TranslationLanguageNotAvailable"}:
        return "language_unavailable"
    if name == "TranscriptsDisabled":
        return "captions_disabled"
    if name in {"VideoUnavailable", "VideoUnplayable"}:
        return "video_unavailable"
    if name in {"AgeRestricted", "PoTokenRequired"}:
        return "authentication_required"
    if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)):
        return "timeout"
    if isinstance(error, (ImportError, ModuleNotFoundError)):
        return "dependency_missing"
    if isinstance(error, (ConnectionError, OSError)):
        return "network_error"
    # Inspect only locally: never return raw provider error messages or URLs.
    message = str(error).lower()
    if re.search(r"\b429\b|too many requests", message):
        return "rate_limited"
    if re.search(r"\b403\b|forbidden", message):
        return "access_denied"
    if "sign in" in message or "login required" in message:
        return "authentication_required"
    return "provider_error"


def _ytdlp_code(stderr: str, stdout: str, returncode: int) -> str:
    diagnostics = (stderr + "\n" + stdout).lower()
    if re.search(r"\b429\b|too many requests", diagnostics):
        return "rate_limited"
    if re.search(r"\b403\b|forbidden", diagnostics):
        return "access_denied"
    if "sign in" in diagnostics or "login required" in diagnostics:
        return "authentication_required"
    if "unsupported url" in diagnostics or "video unavailable" in diagnostics:
        return "video_unavailable"
    if "no subtitles" in diagnostics or "subtitles are not available" in diagnostics:
        return "captions_unavailable"
    if "timed out" in diagnostics or "timeout" in diagnostics:
        return "timeout"
    return "provider_error" if returncode else "captions_unavailable"


class TranscriptRequest(BaseModel):
    video_id: str = Field(
        default="", max_length=2048, description="11-character ID or HTTPS YouTube URL"
    )
    languages: list[str] = Field(default_factory=lambda: ["en"], min_length=1, max_length=4)
    offset: int = Field(default=0, ge=0, le=100000)
    limit: int = Field(default=150, ge=1, le=300)
    output_format: Literal["json", "text", "srt"] = "json"


def _resolve_id(value: str) -> str | None:
    if VIDEO_ID.fullmatch(value):
        return value
    parts = urlsplit(value)
    if parts.scheme != "https" or parts.username or parts.password or parts.port:
        return None
    if parts.hostname in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        candidate = (
            parse_qs(parts.query).get("v", [""])[0]
            if parts.path == "/watch"
            else parts.path.removeprefix("/shorts/").removeprefix("/live/")
        )
    elif parts.hostname == "youtu.be":
        candidate = parts.path.lstrip("/")
    else:
        return None
    return candidate if VIDEO_ID.fullmatch(candidate) else None


def _valid_languages(languages: list[str]) -> bool:
    return all(isinstance(s, str) and LANGUAGE.fullmatch(s) for s in languages)


def _primary(video_id: str, languages: list[str]) -> tuple[list[dict], str, str]:
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    result = api.fetch(video_id, languages=languages)
    rows = [
        {
            "start": round(float(row.start), 3),
            "duration": round(float(row.duration), 3),
            "text": row.text.strip(),
        }
        for row in result
        if row.text and row.text.strip()
    ]
    return rows, result.language_code, ("automatic" if result.is_generated else "manual")


def _seconds(value: str) -> float:
    match = TIMESTAMP.fullmatch(value.strip())
    if not match:
        raise ValueError("invalid timestamp")
    hours, minutes, seconds, millis = match.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def _parse_vtt(content: str) -> list[dict]:
    # YouTube VTT may contain overlapping rolling captions; deduplicate exact cue text.
    result = []
    for block in re.split(r"\r?\n\s*\r?\n", content.lstrip("\ufeff")):
        lines = [line.strip() for line in block.splitlines()]
        cue = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if cue is None:
            continue
        start_s, end_s = (v.strip().split(" ", 1)[0] for v in lines[cue].split("-->", 1))
        try:
            start, end = _seconds(start_s), _seconds(end_s)
        except ValueError:
            continue
        body = " ".join(lines[cue + 1 :])
        body = re.sub(r"<[^>]*>", "", body)
        body = html.unescape(body).strip()
        if not body:
            continue
        if result and result[-1]["text"] == body:
            continue
        result.append({"start": start, "duration": round(max(0, end - start), 3), "text": body})
    return result


def _fallback(video_id: str, languages: list[str]) -> tuple[list[dict], str, str]:
    root = Path(__file__).resolve().parents[2] / "data"
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="yt-captions-", dir=root) as directory:
        command = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-config",
            "--no-playlist",
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            ",".join(languages),
            "--sub-format",
            "vtt",
            "--no-warnings",
            "--no-progress",
            "--no-cache-dir",
            "--socket-timeout",
            "8",
            "--retries",
            "0",
            "--extractor-retries",
            "0",
            "--output",
            str(Path(directory) / "%(id)s.%(ext)s"),
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=55,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        files = sorted(Path(directory).glob("*.vtt"))
        if proc.returncode != 0 or not files:
            raise CaptionProviderError(_ytdlp_code(proc.stderr, proc.stdout, proc.returncode))
        chosen = files[0]
        rows = _parse_vtt(chosen.read_text(encoding="utf-8-sig", errors="replace"))
        if not rows:
            raise CaptionProviderError("captions_unreadable")
        lang = chosen.stem.removeprefix(video_id + ".")
        return rows, lang, "unknown"


def _go_available() -> bool:
    """Third-party local executable is opt-in; it is never bundled or redistributed."""
    return bool(os.environ.get("YT_RESEARCH_GO_TRANSCRIPT_BIN", "").strip())


def _go_fallback(video_id: str, languages: list[str]) -> tuple[list[dict], str, str]:
    binary = Path(os.environ.get("YT_RESEARCH_GO_TRANSCRIPT_BIN", "").strip())
    if not binary.is_absolute() or not binary.is_file():
        raise CaptionProviderError("dependency_missing")
    if not VIDEO_ID.fullmatch(video_id):
        raise CaptionProviderError("invalid_input")

    # A single Go request; no concurrent calls, cookies, remote scripts, or video downloads.
    command = [
        str(binary),
        f"https://www.youtube.com/watch?v={video_id}",
        "--lang",
        languages[0],
        "--json",
    ]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=50,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise CaptionProviderError("timeout") from exc
    if len(proc.stdout) > 8_000_000:
        raise CaptionProviderError("provider_error")
    if proc.returncode != 0:
        raise CaptionProviderError(_ytdlp_code(proc.stderr, proc.stdout, proc.returncode))
    try:
        items = json.loads(proc.stdout)
    except (ValueError, TypeError) as exc:
        raise CaptionProviderError("provider_error") from exc
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        raise CaptionProviderError("provider_error")
    item = items[0]
    if item.get("videoId") != video_id:
        raise CaptionProviderError("provider_error")
    if item.get("error"):
        raise CaptionProviderError(_ytdlp_code(str(item["error"]), "", 1))
    language = item.get("language")
    if not isinstance(language, str) or not any(
        language.lower() == x.lower() or language.lower().startswith(x.lower() + "-")
        for x in languages
    ):
        raise CaptionProviderError("language_unavailable")
    segments = item.get("segments")
    if not isinstance(segments, list) or len(segments) > 30000:
        raise CaptionProviderError("provider_error")
    rows = []
    for item in segments:
        if not isinstance(item, dict):
            raise CaptionProviderError("provider_error")
        try:
            start = float(item["start"])
            duration = float(item["dur"])
            content = item["text"]
        except (KeyError, ValueError, TypeError) as exc:
            raise CaptionProviderError("provider_error") from exc
        if (
            not math.isfinite(start)
            or not math.isfinite(duration)
            or start < 0
            or duration < 0
            or duration > 3600
            or not isinstance(content, str)
            or len(content) > 5000
        ):
            raise CaptionProviderError("provider_error")
        if content.strip():
            rows.append(
                {"start": round(start, 3), "duration": round(duration, 3), "text": content.strip()}
            )
    if not rows:
        raise CaptionProviderError("captions_unavailable")
    return rows, language, "unknown"


def _clock(seconds: float) -> str:
    n = round(max(0, seconds) * 1000)
    h, rem = divmod(n, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def get_transcript(req: TranscriptRequest) -> GeneralResult:
    video_id = _resolve_id(req.video_id)
    if video_id is None or not _valid_languages(req.languages):
        return GeneralResult(
            state="invalid_input", summary="Invalid YouTube ID/URL or language codes"
        )
    warnings = []
    provider_diagnostics: list[dict[str, str]] = []
    try:
        rows, language, caption_type = await asyncio.wait_for(
            asyncio.to_thread(_primary, video_id, req.languages), timeout=25
        )
        provider = "youtube_transcript_api"
        if not rows:
            raise ValueError("empty captions")
    except Exception as exc:
        primary_reason = _error_code(exc)
        provider_diagnostics.append(
            {"provider": "youtube_transcript_api", "reason": primary_reason}
        )
        warnings.append(f"Primary caption provider failed ({primary_reason}); tried yt-dlp.")
        try:
            rows, language, caption_type = await asyncio.wait_for(
                asyncio.to_thread(_fallback, video_id, req.languages), timeout=65
            )
            provider = "yt_dlp"
        except Exception as exc:
            fallback_reason = _error_code(exc)
            provider_diagnostics.append({"provider": "yt_dlp", "reason": fallback_reason})
            if _go_available():
                warnings.append("yt-dlp unavailable; attempted local Go InnerTube fallback.")
                try:
                    rows, language, caption_type = await asyncio.wait_for(
                        asyncio.to_thread(_go_fallback, video_id, req.languages),
                        timeout=55,
                    )
                    provider = "go_innertube"
                except Exception as go_exc:
                    provider_diagnostics.append(
                        {"provider": "go_innertube", "reason": _error_code(go_exc)}
                    )
                    return GeneralResult(
                        state="unavailable",
                        summary="Captions unavailable from all three providers",
                        metadata={
                            "video_id": video_id,
                            "provider_diagnostics": provider_diagnostics,
                        },
                        warnings=["No verified transcript; no speech or video content inferred."],
                    )
            else:
                return GeneralResult(
                    state="unavailable",
                    summary="Captions unavailable from both configured providers",
                    metadata={
                        "video_id": video_id,
                        "provider_diagnostics": provider_diagnostics,
                    },
                    warnings=["Go InnerTube fallback not configured; no transcript inferred."],
                )
    if not rows:
        return GeneralResult(
            state="unavailable", summary="Caption track contained no readable cues"
        )
    page = rows[req.offset : req.offset + req.limit]
    if req.output_format == "text":
        content = "\n".join(f"[{_clock(r['start']).replace(',', '.')}] {r['text']}" for r in page)
    elif req.output_format == "srt":
        content = "\n\n".join(
            f"{req.offset + i + 1}\n{_clock(r['start'])} --> "
            f"{_clock(r['start'] + r['duration'])}\n{r['text']}"
            for i, r in enumerate(page)
        )
    else:
        content = ""
    next_offset = req.offset + len(page) if req.offset + len(page) < len(rows) else None
    return GeneralResult(
        state="ok",
        summary=f"Retrieved {len(page)} of {len(rows)} caption cues",
        source=provider,
        items=page if req.output_format == "json" else [],
        metadata={
            "video_id": video_id,
            "language": language,
            "caption_type": caption_type,
            "provider_diagnostics": provider_diagnostics,
            "go_fallback_configured": _go_available(),
            "total_segments": len(rows),
            "offset": req.offset,
            "next_offset": next_offset,
            "output_format": req.output_format,
            "content": content,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
        },
        warnings=warnings,
    )


def register(server) -> None:
    from mcp.types import ToolAnnotations

    @server.tool(
        name="youtube_get_transcript",
        description="Get public captions by ID or YouTube URL. Transcript API first, "
        "yt-dlp subtitle-only fallback, then optional local Go InnerTube fallback. "
        "Supports pagination, JSON, text and SRT. Watch Videos stays separate.",
        structured_output=True,
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
    )
    async def do_transcript(request: TranscriptRequest) -> GeneralResult:
        return await get_transcript(request)
