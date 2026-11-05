# YT Research — Production acceptance checkpoint (5 November 2026)

## Verified
- OpenAI tunnel control-plane metadata name renamed from "Niche Mcp Tunnel" to "YT Research"; original tunnel ID and workspace associations preserved.
- Remote tunnel healthz and readyz both HTTP 200; control-plane poll healthy before and after production launcher reload. tunnel-client doctor returned RESULT ok.
- Full stdio MCP handshake listed exactly 7 tools and yt-research://status reported name YT Research, NexLev disabled, API then yt-dlp.
- Live official YouTube search, videos.list, channels.list and playlistItems.list succeeded.
- Live yt-dlp no-key search and single-video public view counts succeeded with yt-dlp stable 2026.10.26.
- Local Watch successful 20-second test: 26 timestamped sampled frames and transcript.
- Mocked API-quota failure triggers yt-dlp fallback; simulated tests cannot prove every future outage scenario.
- Focused general-mode suite: 13/13 passed before the full legacy run.
- Operational launch script now redirects TEMP/TMP/TMPDIR to D:\LocalMCPs\YouTubeNicheFinderMCP\data\runtime-tmp.

## Legacy regression methodology
- Old legacy F1-F23 tests are tested with old mode enabled; 7-tool general profile is tested separately.
- Full tests require D: temp path because C: was completely full at first attempt.
- Two old CLI tests used synthetic October 2 clock in fixtures but the CLI inherited the actual November clock and legitimately rejected expired retention. Test-only clock injection fixes this; production expiry checks are unchanged.
- Collected full legacy suite: 870 cases. Executed in segments because the suite is CPU-intensive and synthetic fixture expiry was time-dependent.
- First segment: 250 passed, one expired October CLI fixture exposed.
- Next segment: 494 passed, another expired October CLI review fixture exposed.
- Last legacy segment: 150 passed before another correct expired-data permission state in stdio fixture.
- Corrected the two CLI test clocks only; adjusted the third expected stdio state to include permission_required when historical evidence expired.
- Final edge/verification batch: 35 passed. Follow-up focused batch (legacy projection, expiry fixtures and general MCP): 14 passed.
- All known failing test cases have been rerun successfully; there was no single uninterrupted 870/870 green run, so do not present it as one.

## Remaining conditions / limitations
- ChatGPT visible connected-app label and its cached public tool inventory cannot be read from this tool session; browser-side reconnection may be needed. Control-plane rename is independently verified.
- Windows C: free space under 0.2 GB is a serious operational risk for Watch video temp files and Windows components; user action needed to free disk space.
- No automatic scheduler/history snapshots; no full stability load/security audit; no guaranteed YouTube coverage when API/yt-dlp both fail.
- Config's local Watch can call model APIs (e.g. Gemini), but YT Research itself makes no MCP-to-MCP third-party calls.
- Full production sign-off remains conditional until all operational blockers are resolved.

