"""Exact modular public surface and a sanitized MCP validation boundary."""

import os

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from youtube_niche_mcp.services.safety import safe_json
from youtube_niche_mcp.tools import niche
from youtube_niche_mcp.tools.descriptions import DESCRIPTIONS
from youtube_niche_mcp.tools.errors import failure
from youtube_niche_mcp.tools.schemas import (
    CompetitorCompareRequest,
    CompetitorRequest,
    CompetitorWatchRequest,
    PublicResult,
)


class PublicMCPServer(MCPServer):
    """SDK validation errors may contain rejected values; never forward their text."""

    async def call_tool(self, name, arguments, context=None):
        try:
            if (
                name not in DESCRIPTIONS
                and name not in getattr(self, "general_tool_names", set())
                or not isinstance(arguments, dict)
                or set(arguments) != {"request"}
            ):
                raise ValueError
            if len(safe_json(arguments, self.public_secrets).encode()) > 128000:
                raise ValueError
            response = await super().call_tool(name, arguments, context)
            if response.structured_content is not None:
                # Structured output is authoritative. Mirroring its entire JSON in text
                # nearly doubles the actual MCP result and wastes the client's budget.
                response = response.model_copy(
                    update={
                        "content": [
                            TextContent(
                                type="text",
                                text=response.structured_content.get("summary", "Research result"),
                            )
                        ]
                    }
                )
            return response
        except UnexpectedToolError:
            result = failure("internal_error")
        except (ToolError, ValueError, TypeError):
            result = failure("invalid_input")
        except Exception:
            result = failure("internal_error")
        data = result.model_dump(mode="json")
        return CallToolResult(
            content=[TextContent(type="text", text=result.model_dump_json())],
            structured_content=data,
            is_error=True,
        )


def register(server, surface):
    server.public_secrets = surface.secrets
    niche.register(server, surface)

    @server.tool(
        name="youtube_competitor_analyze",
        description=DESCRIPTIONS["youtube_competitor_analyze"],
        structured_output=True,
        annotations=ToolAnnotations(
            read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=True
        ),
    )
    async def analyze(request: CompetitorRequest) -> PublicResult:
        return await surface.dispatch("youtube_competitor_analyze", request)

    @server.tool(
        name="youtube_competitor_compare",
        description=DESCRIPTIONS["youtube_competitor_compare"],
        structured_output=True,
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
    )
    async def compare(request: CompetitorCompareRequest) -> PublicResult:
        return await surface.dispatch("youtube_competitor_compare", request)

    if os.getenv("YTNMCP_RESEARCH_ONLY") != "1":

        @server.tool(
            name="youtube_competitor_watch",
            description=DESCRIPTIONS["youtube_competitor_watch"],
            structured_output=True,
            annotations=ToolAnnotations(
                read_only_hint=False,
                destructive_hint=False,
                idempotent_hint=False,
                open_world_hint=False,
            ),
        )
        async def watch(request: CompetitorWatchRequest) -> PublicResult:
            return await surface.dispatch("youtube_competitor_watch", request)
