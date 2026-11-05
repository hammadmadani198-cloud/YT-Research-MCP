# YT Research — Royalty TV broadcast classification & Watch resilience
Date: 2026-11-05

## Verified input
Channel: Royalty TV (UCLaL_1BgxTz1528xgAbGhTA)
Video examined: London Bridge Is Down (2023) | Full Documentary (CCjvbAbWSgY).

Google YouTube Data API's liveStreamingDetails object can exist for a completed broadcast.
Its mere presence cannot independently establish whether a video is an unsuitable
livestream versus a scheduled documentary premiere. See
https://developers.google.com/youtube/data/reference/rest/v3/videos

On the same 100-upload sample:
- 55 had completed-broadcast metadata (liveBroadcastContent=none).
- 45 had no liveStreamingDetails.
- Before: eligible 41, scorable 39, 30-day scorable 0, 90-day scorable 0,
  overall >=2x ratio 11.
- After: eligible 96, scorable 96, 30-day scorable 6, 90-day scorable 19,
  overall >=2x ratio 28.
- Old London Bridge current-age-cohort ratio 37.44x; corrected ratio 30.73x.
- Corrected analysis still uses lifetime public views grouped by broad age buckets;
  it is NOT genuine same-age Day-7/30/90 historical views.

## Broadcast policy
- Default exclude_active_only: exclude active/upcoming live events while retaining
  completed broadcasts/premieres with a review flag.
- Optional flag_only: retain all items, including currently live/upcoming, flagged.
- Optional exclude_all_broadcast_metadata: emulate previous strict exclusion.
- Each API row includes broadcast_kind and broadcast_metadata_present.
- Completed_broadcast_or_premiere is deliberately ambiguous: cannot certify a
  documentary's production format from metadata alone.
- The 55 flagged items are not automatically considered high-quality documentaries.

## Watch improvements
- YT Research youtube_watch_video accepts processing_mode:
  auto, local_first, local_only (default auto preserves existing behavior).
- Inspection plans default to local_first, avoiding an up-front Gemini 503 delay
  when the local downloader is working.
- local_first tries local extraction first, then Gemini and existing opt-in
  model adapters only if local extraction fails; local_only never calls Gemini.
- Watch downloader has bounded attempts; if SSL unexpected EOF occurs, retry
  once with IPv4 while keeping TLS certificate verification enabled.
- Watch process media temp runs under WatchMCP/jobs/runtime_tmp on D:.
- Temporary downloaded video/audio inside a job's dedicated artifacts are removed
  after extraction. Timestamped frames and job JSON remain.
- Model-only reports do NOT count as verified extracted frames.

## Test results and limitations
- Royalty TV live API sample 100/100: before/after comparison verified.
- YT Research focused tests: 29 passed; Ruff checks passed.
- Watch strategy tests: 6 passed; download resilience tests: 2 passed;
  Gemini-first success and simulated fallback integration passed (16 frames).
- Real local_first request on N7JanqWb9W0 ended FAILED because local yt-dlp
  timed out and Gemini responded HTTP 503. No fabricated visual output.
- A previously successful live local Watch sample returned 26 timestamped frames,
  but this cannot guarantee every competitor video can be downloaded.
- Full four-stage live inspection on Royalty TV is NOT yet verified end-to-end.
- Automatic daily view snapshots/scheduler are NOT included in this fix.
- No NexLev calls and no other MCP-to-MCP dependency introduced.
- New YT Research tool count remains 14; schema for youtube_watch_video changed.
  The ChatGPT connector may need a refresh to display processing_mode.

## Source/rollback
YT Research source:
D:\LocalMCPs\YouTubeNicheFinderMCP
Watch source:
D:\LocalMCPs\WatchMCP

Pre-change files saved alongside Watch source as
*.before_fallback_reliability_20261105.bak
and alongside YT Research source as the corresponding backup relocated to
D:\LocalMCPs\YTResearchBackups\2026-11-05.

