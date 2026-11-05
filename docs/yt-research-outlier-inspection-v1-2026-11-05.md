# YT Research — Outlier + Video Inspection Expansion (2026-11-05)

## Core intent
Upgrade the approved seven-tool general-purpose MCP without re-enabling NexLev,
legacy niche-selection restrictions, F1–F23 automatic decisions, or any other MCP provider.
The new 14-tool profile has seven additive tools and preserves the original seven.

## Added tools
- youtube_channel_deep_uploads — paginate up to 300 available channel uploads (Data API first; yt-dlp fallback)
- youtube_channel_outliers — comparable long-form baselines, 2x/5x/10x flags, 30/90-day windows
- youtube_inspection_plan — evidence-first opening, early-middle, late-middle and ending windows
- youtube_inspection_review — aggregate Watch job status, transcript/frames and evidence labels
- youtube_view_snapshot — store real observed public views (manual capture, not a scheduler)
- youtube_view_history — read true stored observations and near-Day-7/30/90 checkpoints
- youtube_export_outliers — save 30/90/overall evidence as local JSON and CSV


## Outlier algorithm
- Default 8+ minutes, excluding identifiable livestream archives, very short videos,
  repeated exact titles and missing dates/views. User can adjust duration.
- Optional include_title_terms / exclude_title_terms narrow the relevant topic family.
  These are user-selected string filters, NOT verified semantic format classifications.
- Overall median is a diagnostic; ranked ratios use leave-one-out median of videos
  in the same broad current-video-age bucket: 0–30, 31–90, 91–365, 366+ days.
- At least 5 peer uploads are required for a scorable ratio (configurable).
- Top 30/90-day outlier counts do not claim exhaustive market demand.
- IMPORTANT: Current view counts in broad age buckets are NOT genuine same-age
  historical Day-7/30/90 performance. Exact checkpoints only exist if saved in time.
- No GREEN niche verdict follows automatically from these metrics.


## Video quality inspection
- youtube_inspection_plan provides four timestamped requests for the preexisting
  youtube_watch_video tool. Jobs can be polled through youtube_watch_status.
- youtube_watch_frames retrieves sampled frames when local extraction is available.
- youtube_inspection_review labels outcomes as sampled_frames_verified,
  model_report_only, transcript_only, pending, or unavailable.
- Sampling does not guarantee full-video narrative, factual accuracy, image licensing
  or complete audience fit. AI assessments must cite evidence and timestamps.
- Local Watch may use Gemini or other configured model APIs, but no MCP-to-MCP
  dependency is introduced.

## Snapshot and export limitations
- youtube_view_snapshot stores observed public view counts in a separate SQLite file.
- youtube_view_history shows actual observations near Day 7/30/90 within tolerance,
  or not_recorded. No historical reconstruction from present views.
- Automatic daily scheduling is NOT installed in this release.
- Export files are stored under data/yt_exports (or YT_RESEARCH_EXPORT_DIR).
- Both raw data provenance and warnings accompany generated reports.

## Quality gate
- Existing seven tools preserved; new profile exposes 14 total.
- Offline deterministic tests and live paginated API metadata checks are required.
- Do not assume remote ChatGPT app tool-cache refresh until independently observed.
- This expansion is separately releasable/rollbackable from the approved seven-tool base.

