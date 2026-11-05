# YT Research — General Data and Video Research Profile (2026-11-04)

## User-approved scope
This profile removes the old niche-specific approval/eligibility/decision rules from the ACTIVE MCP surface.
The original F1-F23 niche engine and historical SQLite records remain intact for rollback. They are never invoked by this profile.
The live MCP server name is **YT Research**.

## Active tools
The seven tools below are the preserved foundation. Seven additional outlier,
inspection, snapshot and export tools were added in November 2026; see
`yt-research-outlier-inspection-v1-2026-11-05.md` for their contracts and caveats.

1. youtube_search — official YouTube Data API first; yt-dlp if API key absent, quota/error, or no hydrated results.
2. youtube_video_details — official metadata first; yt-dlp when unavailable or public view count is missing.
3. youtube_channel_uploads — official uploads-playlist API first; yt-dlp if empty/unavailable.
4. youtube_watch_health — check readiness of the local Watch engine.
5. youtube_watch_video — submit video analysis directly to local Watch code (Gemini and local media fallback).
6. youtube_watch_status — get local job progress/result.
7. youtube_watch_frames — return sampled local timestamped frames, not a whole-video review.

## What is disabled
No niche_entry, faceless-only eligibility, subscriber-count eligibility, F1-F23 auto-verdicts, niche comparisons,
niche watchlists, or proprietary niche classification are exposed. No NexLev requests or other third-party
MCP calls execute in this profile. Code is archived in the same repository for reversible rollback.

## Data integrity / caveats
Public metadata only; no competitor CTR, AVD or retention data.
When API results lack views, yt-dlp supplements up to three videos and annotates views_source.
Missing values are unknown, never zero. yt-dlp fallback does not guarantee official search date/order filters.
Raw yt-dlp searches may supply less metadata than official API. Provider errors do not imply zero demand.
The local Watch video engine may use model APIs configured in WatchMCP (e.g. Gemini/OpenRouter/NVIDIA), but YT Research makes no other MCP-to-MCP calls. Third-party model API use is separate from the no-third-party-MCP restriction.
No automatic scheduled history snapshots were added in this change.
When the local Watch engine succeeds with transcript only but no verified frames, YT Research now reports partial and visual_evidence_available=false. A real 20-second watch sample returned 26 frames plus transcript after local media extraction.

## How to launch
Environment variable: YT_RESEARCH_GENERAL=1.
Use scripts/run-yt-research.ps1 or the configured tunnel/run-mcp.ps1.
The active tunnel sets NEXLEV_API_KEY to null so the third-party key is not loaded.
Rollback: unset YT_RESEARCH_GENERAL and restart; old research-only setting remains independently reversible.
Remote ChatGPT app display label may require a separate plugin metadata rename; server name is YT Research.

## Validation
Standalone client tool list and yt-research://status resource validate the no-niche surface.
Mock tests cover no-key fallback, official quota fallback and supplemental public views.
A live small official API search succeeded; no private metrics were accessed.
yt-dlp was updated to stable 2026.10.26. Live no-key keyword search and single-video metadata retrieval both succeeded. API quota-failure fallback is covered by mocked tests, not a real exhausted-quota run.

