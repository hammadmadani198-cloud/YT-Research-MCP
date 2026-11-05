"""Twelve niche tool registrations, including distinct local niche watch intent."""

import os

from mcp.types import ToolAnnotations

from youtube_niche_mcp.tools.descriptions import DESCRIPTIONS
from youtube_niche_mcp.tools.schemas import (
    CompareRequest,
    DetailRequest,
    DiscoverRequest,
    NicheWatchRequest,
    PublicResult,
    ResearchRequest,
)


def register(server, surface):
    def tool(name, *, writes=False, network=False):
        return server.tool(
            name=name,
            description=DESCRIPTIONS[name],
            structured_output=True,
            annotations=ToolAnnotations(
                read_only_hint=not writes,
                destructive_hint=False,
                idempotent_hint=name != "youtube_niche_watchlist",
                open_world_hint=network,
            ),
        )

    @tool("youtube_niche_research", writes=True, network=True)
    async def research(request: ResearchRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_research", request)

    @tool("youtube_niche_discover", writes=True, network=True)
    async def discover(request: DiscoverRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_discover", request)

    @tool("youtube_niche_compare")
    async def compare(request: CompareRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_compare", request)

    @tool("youtube_niche_outliers")
    async def outliers(request: DetailRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_outliers", request)

    @tool("youtube_niche_content_gaps")
    async def gaps(request: DetailRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_content_gaps", request)

    @tool("youtube_niche_packaging")
    async def packaging(request: DetailRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_packaging", request)

    @tool("youtube_niche_audience_demand")
    async def demand(request: DetailRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_audience_demand", request)

    @tool("youtube_niche_sustainability")
    async def sustainability(request: DetailRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_sustainability", request)

    @tool("youtube_niche_risk")
    async def risk(request: DetailRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_risk", request)

    @tool("youtube_niche_geo_language")
    async def language(request: DetailRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_geo_language", request)

    @tool("youtube_niche_history")
    async def history(request: DetailRequest) -> PublicResult:
        return await surface.dispatch("youtube_niche_history", request)

    if os.getenv("YTNMCP_RESEARCH_ONLY") != "1":

        @tool("youtube_niche_watchlist", writes=True)
        async def watch(request: NicheWatchRequest) -> PublicResult:
            return await surface.dispatch("youtube_niche_watchlist", request)
