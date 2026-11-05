# YT Research — Watch Video Future Fix Lock

- **Date:** 2026-11-05
- **Status:** DEFERRED / HOLD — do not block current channel discovery, outlier, or topic research.
- **Decision:** Skip Watch Videos troubleshooting and complete four-stage live footage inspection for now. Revisit only when user explicitly reopens this task.
- **Scope:** Local WatchMCP engine connected through YT Research; existing 14 research tools are retained.

## Confirmed blockers

1. Gemini video analysis sometimes returns HTTP 503 (service high demand).
2. Local yt-dlp media extraction times out contacting www.youtube.com:443 (HTTPS read timeout; earlier SSL unexpected EOF).
3. Latest Royalty TV inspection job `1583b01269594b819bcb481273211867` (video `OsppHo8VOVw`) finished **failed**; no verified extracted frames or completed footage analysis.
4. `local_first`, `local_only`, bounded retries, and D: temporary-media handling were implemented and offline-tested; they do not prove that all live video downloads are reliable.

## Reopen checklist (future only)

- Diagnose Windows-to-YouTube HTTPS, DNS, proxy, SSL and media extraction without disabling TLS verification.
- Check yt-dlp compatibility and controlled retry behavior; avoid indefinite hangs.
- Check Gemini model availability/quotas and approved backup routes; avoid falsely declaring missing visual evidence.
- Run a real Royalty TV video through opening, early-middle, late-middle and ending segments.
- Verify timestamped image frames, transcript/provenance and completed review; mark PASS only with actual evidence.
- Record final acceptance tests and update this status when user authorizes reopening.

## Work that can continue now

YT Research can continue competitor/channel discovery, 30/90-day and broad-age-cohort outlier analysis, public metadata collection, view snapshots and JSON/CSV exports. Do not label coarse age-cohort ratios as historical same-age views. Do not claim competitor visual-quality findings based on uninspected footage.
