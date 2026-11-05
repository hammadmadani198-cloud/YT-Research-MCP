# Research-only YT Niche Finder profile (2026-11-04)

Purpose: hide two watch-definition tools that store preferences but do not execute monitoring. They are not needed for Sir Ammar Nisar's immediate research workflow.

Active public tools in this profile: 13 of original 15.
Disabled from MCP tool registration:
- youtube_niche_watchlist
- youtube_competitor_watch

No deletion: both implementations, watch tables, saved data, F1-F23 calculations and original catalog remain intact. Other tools including history, risk, geo_language, audience_demand and competitor analysis remain available.

Activation: set process environment YTNMCP_RESEARCH_ONLY=1 before starting the server.
The Windows tunnel launch scripts in tunnel/run-mcp.ps1 and tunnel/run-mcp.cmd set this variable (local tunnel files are intentionally Git-ignored).
The tracked scripts/run-research-only.ps1 provides the same research-only launch mode for future clean installations.
Rollback: remove that environment setting (or set it to 0) and restart the server. The full 15-tool public catalog then returns.

Proof: local MCP client lists 15 tools in default mode and exactly 13 in research-only mode. New tests in tests/test_research_only_profile.py passed.
Existing focused suite: 94 passed, one permission-state test failed with permission_required instead of configured/available. It must be investigated separately and is not claimed as fully green.

Note: there is NO scheduler or automatic background data collection. Historical view curves require a separate snapshots system. No YouTube Data API or NexLev research was triggered by this profile change.
