# YT Research — Production Acceptance Check (2026-11-04)

## Scope and current decision
Core data/video-research functionality: **technical smoke tests PASSED**.
Full unrestricted production sign-off: **CONDITIONAL / HOLD** until external ChatGPT app label/tool-list refresh and long-run operational tests.
Do not call the complete future research roadmap finished: historical scheduler, deep topic/outlier methodology, monitoring, and extended load testing are not included.

## Verified local and live observations
- Active server identity: YT Research; exactly seven general tools exposed, no legacy niche/F1–F23 decision tools.
- YouTube Data API search, videos.list, channels.list and playlistItems.list each returned HTTP 200 and valid video metadata in a live sequence.
- yt-dlp version updated from 2026.07.04 to 2026.10.26 stable.
- Live yt-dlp no-API-key keyword search: 2 video matches and view counts returned.
- Live yt-dlp single-video metadata: public view count returned.
- Quota-exhausted API fallback: **simulated/mocked**, not an actual exhausted quota account.
- Local Watch engine health: ready; Gemini-first path previously hit 503; local fallback succeeded.
- Real Watch 20-second visual test: 26 sampled frames and transcript. First two timestamped image payloads retrieved.
- Transcript-only previous job: corrected to partial; visual_evidence_available=false.
- Focused tests: 13 passed, Ruff check passed on affected files; full historical 859+ test suite not rerun here.

## Security, permission and limits
- The active profile disables NexLev provider use and exposes no MCP-to-MCP third-party dependencies.
- Local Watch still uses third-party model APIs if configured; this is separate from third-party MCP integration.
- No credentials printed; external requests originate only on user-authorized local runner.
- Public YouTube data retrieval cannot recover competitors' private analytics.
- Search coverage is a sample, not exhaustive. yt-dlp fallback may not preserve official date/order search semantics.
- No scheduler/snapshot service and no competitor historical VPH reconstruction.
- Existing Git-ignored tunnel files set YT_RESEARCH_GENERAL=1 and NEXLEV_API_KEY unset.
- Remote ChatGPT app display label/tool inventory is controlled by installed app metadata and may be stale; **not verified renamed**.

## Deployment / recovery
Active source path: D:\LocalMCPs\YouTubeNicheFinderMCP.
Launch mode: YT_RESEARCH_GENERAL=1. Legacy engine retained in source as reversible rollback only.
Do not claim production-level resilience without monitoring, quotas/alerting, dependency checks and complete regression suite.

