import json
import os
import sys

import anyio
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from youtube_niche_mcp.schemas.status import ServerStatus
from youtube_niche_mcp.server import STATUS_URI, create_server
from youtube_niche_mcp.services.catalog import PLANNED_TOOLS


@pytest.mark.anyio
async def test_mcp_initializes_and_exposes_honest_status(tmp_path):
    with anyio.fail_after(20):
        async with Client(create_server(), raise_exceptions=True) as client:
            assert sorted(t.name for t in (await client.list_tools()).tools) == sorted(
                PLANNED_TOOLS
            )
            result = await client.read_resource(STATUS_URI)
            payload = ServerStatus.model_validate_json(result.contents[0].text)
            assert payload.phase == 8
            assert not payload.live_collection_enabled
            assert payload.implemented_tools == list(PLANNED_TOOLS)
            assert payload.planned_tools == list(PLANNED_TOOLS)
            resources = await client.list_resources()
            assert [str(resource.uri) for resource in resources.resources] == [STATUS_URI]
    assert not (tmp_path / "test.sqlite3").exists()


@pytest.mark.stdio
@pytest.mark.anyio
async def test_real_stdio_session(tmp_path):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "youtube_niche_mcp.server"],
        env={**os.environ, "YTNMCP_DB_PATH": str(tmp_path / "never-created.sqlite3")},
        cwd=tmp_path,
    )
    with anyio.fail_after(20):
        async with Client(parameters, read_timeout_seconds=10) as client:
            assert sorted(t.name for t in (await client.list_tools()).tools) == sorted(
                PLANNED_TOOLS
            )
            result = await client.read_resource(STATUS_URI)
            payload = json.loads(result.contents[0].text)
            assert payload["status"] == "research_tools_available"
            assert len(payload["planned_tools"]) == 15
    assert not (tmp_path / "never-created.sqlite3").exists()
