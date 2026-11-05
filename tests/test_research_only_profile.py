"""Research-only mode hides non-executing watch-intent tools without affecting analysis."""

import json

import pytest
from mcp import Client

from youtube_niche_mcp.server import STATUS_URI, create_server
from youtube_niche_mcp.services.catalog import IMPLEMENTED_TOOLS

WATCH_INTENT = {"youtube_niche_watchlist", "youtube_competitor_watch"}


@pytest.mark.anyio
async def test_research_only_hides_watch_intent(monkeypatch):
    monkeypatch.setenv("YTNMCP_RESEARCH_ONLY", "1")
    async with Client(create_server()) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert names == set(IMPLEMENTED_TOOLS) - WATCH_INTENT
        state = json.loads((await client.read_resource(STATUS_URI)).contents[0].text)
        assert set(state["implemented_tools"]) == names
        assert set(state["planned_tools"]) == set(IMPLEMENTED_TOOLS)


@pytest.mark.anyio
async def test_default_surface_unchanged(monkeypatch):
    monkeypatch.delenv("YTNMCP_RESEARCH_ONLY", raising=False)
    async with Client(create_server()) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert names == set(IMPLEMENTED_TOOLS)
