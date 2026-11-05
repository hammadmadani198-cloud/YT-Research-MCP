"""Official MCP Python SDK v2 stdio skeleton; no collection side effects."""

import json
import logging
import os

from youtube_niche_mcp import (
    __version__,
    export_research,
    general_research,
    inspection_research,
    outlier_research,
    snapshot_research,
)
from youtube_niche_mcp.collectors.nexlev.contracts import capability_report
from youtube_niche_mcp.config import ConfigurationError, Settings
from youtube_niche_mcp.db.schema import SCHEMA_VERSION
from youtube_niche_mcp.logging import configure_logging
from youtube_niche_mcp.schemas.status import ServerStatus
from youtube_niche_mcp.services.capabilities import capabilities, operational_status
from youtube_niche_mcp.services.catalog import IMPLEMENTED_TOOLS, PLANNED_TOOLS
from youtube_niche_mcp.tools.registration import PublicMCPServer, register
from youtube_niche_mcp.tools.runtime import PublicSurface

STATUS_URI = "youtube-niche://status"


def server_status(settings: Settings | None = None) -> ServerStatus:
    settings = settings or Settings.from_env()
    try:
        history = operational_status(settings)
    except Exception:
        history = {"history_count": 0, "state": "unavailable", "schema_version": None}
    return ServerStatus(
        version=__version__,
        schema_version=SCHEMA_VERSION,
        implemented_tools=[
            name
            for name in IMPLEMENTED_TOOLS
            if os.getenv("YTNMCP_RESEARCH_ONLY") != "1"
            or name not in {"youtube_niche_watchlist", "youtube_competitor_watch"}
        ],
        planned_tools=list(PLANNED_TOOLS),
        youtube_api_key_present=settings.youtube_api_key is not None,
        live_collection_configured=bool(settings.youtube_api_key or settings.nexlev_api_key),
        history_state="available" if history["history_count"] else "insufficient_history",
        database_state=history["state"],
        actual_schema_version=history["schema_version"],
        nexlev_capabilities=capability_report(settings.nexlev_api_key is not None),
        capabilities=[
            item.model_dump(mode="json")
            for item in capabilities(settings, history_count=history["history_count"])
        ],
    )


def create_server(settings: Settings | None = None, **runtime_options) -> PublicMCPServer:
    settings = settings or Settings.from_env()
    if os.getenv("YT_RESEARCH_GENERAL") == "1":
        # The active research profile does not import/execute legacy niche scoring or NexLev.
        settings = settings.model_copy(update={"nexlev_api_key": None})
        server = PublicMCPServer(
            "YT Research",
            version=__version__,
            instructions=(
                "General public YouTube research only. YouTube Data API first, yt-dlp fallback, "
                "local Watch Video engine. No niche approval rules, no NexLev and no other MCP."
            ),
        )
        server.public_secrets = (
            (settings.youtube_api_key.get_secret_value(),) if settings.youtube_api_key else ()
        )
        server.general_tool_names = {
            "youtube_search",
            "youtube_video_details",
            "youtube_channel_uploads",
            "youtube_watch_video",
            "youtube_watch_health",
            "youtube_watch_status",
            "youtube_watch_frames",
            "youtube_channel_deep_uploads",
            "youtube_channel_outliers",
            "youtube_inspection_plan",
            "youtube_inspection_review",
            "youtube_view_snapshot",
            "youtube_view_history",
            "youtube_export_outliers",
        }

        @server.resource("yt-research://status", mime_type="application/json")
        def research_status() -> str:
            return json.dumps(
                {
                    "name": "YT Research",
                    "mode": "general",
                    "public_tools": sorted(server.general_tool_names),
                    "niche_decision_rules": "disabled",
                    "nexlev": "disabled",
                    "external_mcp": "none",
                    "data_priority": ["youtube_data_api", "yt_dlp"],
                    "watch": "local_watch_engine",
                    "youtube_api_key_present": bool(settings.youtube_api_key),
                }
            )

        general_research.register(server, settings)
        outlier_research.register(server, settings)
        inspection_research.register(server, settings)
        snapshot_research.register(server, settings)
        export_research.register(server, settings)
        return server
    server = PublicMCPServer(
        "YouTubeNicheFinderMCP",
        version=__version__,
        instructions=(
            "Phase 8 public research tools over the verified F1-F23 engine. Stored evidence "
            "by default; acquisition requires an explicit permission-gated refresh. "
            "Multi-axis decisions include F18; optional F17 is sorting-only. "
            "Watch definitions store intent with no scheduler. No success forecasts."
        ),
    )

    @server.resource(STATUS_URI, mime_type="application/json")
    def foundation_status() -> str:
        """Read the implementation status without database or network writes."""
        return server_status(settings).model_dump_json()

    register(server, PublicSurface(settings, **runtime_options))
    return server


def main() -> None:
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        import sys

        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    configure_logging(settings)
    logging.getLogger(__name__).info("server_starting_phase_8_stdio")
    create_server(settings).run(transport="stdio")


if __name__ == "__main__":
    main()
