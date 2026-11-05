# YT Research — YouTube Research MCP

A Python MCP server for evidence-grounded public YouTube research.
**14 active research tools**, using YouTube Data API first and yt-dlp fallback.

## Capabilities
- Search public videos and retrieve public video/channel metadata.
- Paginate up to 300 uploads; identify provisional 2x/5x/10x
  current-view age-cohort outliers and recent 30/90-day publishing windows.
- Plan four video-inspection stages and review evidence-labelled Watch jobs.
- Save public view snapshots for future actual historical view checkpoints.
- Export evidence as local JSON/CSV. Local data is not shared.

## Install (Python 3.12+)
Create a virtualenv and install dependencies:
  py -3.12 -m venv .venv
  .venv/Scripts/python.exe -m pip install -e ".[dev]"
Set YT_RESEARCH_GENERAL=1 and your own YOUTUBE_API_KEY in the process
environment. Launch the server using python -m youtube_niche_mcp.server.
On Windows, scripts/run-yt-research.ps1 also sets the general-research profile.

## Important limitations
- Ratios use current lifetime views, NOT actual historical Day-7/30 views.
- Historical milestones exist only if actual past snapshots were saved.
- WatchMCP is optional and separate; its source, media and model credentials
  are NOT bundled with this repository. Video reliability needs live validation.
- Old niche/F1-F23 implementation remains for rollback but is disabled with
  YT_RESEARCH_GENERAL=1. NexLev is disabled in the active profile.
- No private analytics, local databases, model keys or user media are included.
- See docs/yt-research-outlier-inspection-v1-2026-11-05.md for methodology.

## Sharing and future updates
GitHub repository starts private. Share by inviting collaborators.
For public sharing, first review privacy, copyrights and dependencies.
To sync future committed changes, configure a GitHub remote and install
the source post-commit hook using:
  python scripts/sync-github-share.py --install-hook
This mirrors the committed source and pushes it when GitHub is authenticated.

No open-source license has been selected. Public visibility by itself
does not grant third-party reuse rights.
