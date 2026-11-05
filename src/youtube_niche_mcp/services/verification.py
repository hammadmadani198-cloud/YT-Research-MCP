"""Non-destructive foundation checks. Never contact YouTube or migrate the real DB."""

import asyncio
import importlib
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
from mcp import Client

from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import migrate
from youtube_niche_mcp.db.status import integrity, status
from youtube_niche_mcp.domain.evidence import NumericEvidence
from youtube_niche_mcp.domain.foundation import Capability, Decision, Metadata, Observation
from youtube_niche_mcp.domain.provenance import Provenance
from youtube_niche_mcp.schemas.status import ServerStatus
from youtube_niche_mcp.server import STATUS_URI, create_server
from youtube_niche_mcp.services.catalog import IMPLEMENTED_TOOLS, PLANNED_TOOLS


async def check_mcp() -> dict:
    with anyio.fail_after(15):
        return await _inspect_mcp()


async def _inspect_mcp() -> dict:
    async with Client(create_server(), raise_exceptions=True, read_timeout_seconds=10) as client:
        tools = await client.list_tools()
        names = sorted(tool.name for tool in tools.tools)
        if names != sorted(IMPLEMENTED_TOOLS):
            raise ValueError("Registered tools disagree with implemented catalog")
        resource = await client.read_resource(STATUS_URI)
        payload = ServerStatus.model_validate_json(resource.contents[0].text)
        if payload.planned_tools != list(PLANNED_TOOLS):
            raise ValueError("Planned tool catalog differs from status resource")
    return {
        "initialized": True,
        "registered_tools": names,
        "planned_tool_count": len(PLANNED_TOOLS),
    }


def verify(settings: Settings) -> dict:
    checks = []

    def run(name, action):
        try:
            detail = action()
            checks.append({"name": name, "passed": True, "detail": detail})
        except Exception as exc:
            # Exception values may contain credentials supplied by dependencies or bad input.
            checks.append({"name": name, "passed": False, "error_type": type(exc).__name__})

    def imports():
        for module in ("mcp", "pydantic", "httpx", "youtube_niche_mcp.cli"):
            importlib.import_module(module)
        return {"ok": True}

    def schema_check():
        from jsonschema import Draft202012Validator

        from youtube_niche_mcp.analysis.historical_models import HistoricalOptions, Panel, Window
        from youtube_niche_mcp.analysis.models import (
            AnalysisBundle,
            AnalysisOptions,
            AnalysisRun,
            MetricResult,
            Outcome,
        )
        from youtube_niche_mcp.decision.models import (
            DecisionOptions,
            PolicyClock,
            SensitivityOptions,
            SortConfig,
        )
        from youtube_niche_mcp.eligibility.models import (
            Claim,
            Classification,
            CohortDefinition,
            CohortMember,
            NicheMembership,
            TaxonomyNode,
        )
        from youtube_niche_mcp.history.retention import StoragePermission
        from youtube_niche_mcp.qualitative.models import (
            Annotation,
            CreatorCapacity,
            Finding,
            PilotProfile,
            QualitativeOptions,
            SampleManifest,
        )

        models = (
            Settings,
            Provenance,
            NumericEvidence,
            ServerStatus,
            Capability,
            Decision,
            Metadata,
            Observation,
            Claim,
            Classification,
            CohortDefinition,
            CohortMember,
            NicheMembership,
            TaxonomyNode,
            StoragePermission,
            AnalysisOptions,
            AnalysisRun,
            AnalysisBundle,
            MetricResult,
            Outcome,
            HistoricalOptions,
            Panel,
            Window,
            Annotation,
            CreatorCapacity,
            Finding,
            PilotProfile,
            QualitativeOptions,
            SampleManifest,
            DecisionOptions,
            SensitivityOptions,
            SortConfig,
            PolicyClock,
        )
        for model in models:
            Draft202012Validator.check_schema(model.model_json_schema())
        from youtube_niche_mcp.tools.schemas import INPUTS, PublicResult

        for model in (*INPUTS.values(), PublicResult):
            Draft202012Validator.check_schema(model.model_json_schema())
        return {
            "validated_models": len(models) + len(set(INPUTS.values())) + 1,
            "public_tool_schemas": len(INPUTS),
        }

    def database_check():
        path = settings.db_path.resolve()
        if path.exists():
            with connect(path, read_only=True, timeout=settings.db_timeout_seconds) as connection:
                result = status(connection)
                result["integrity"] = integrity(connection)
                if result["migration_state"] != "current" or not result["integrity"]["ok"]:
                    raise ValueError("Database needs migration or repair")
                return result
        ancestor = path.parent
        while not ancestor.exists():
            ancestor = ancestor.parent
        # Probe the selected filesystem using a temporary DB; remove it on completion.
        with (
            TemporaryDirectory(prefix="ytnmcp-verify-", dir=ancestor) as temporary,
            connect(Path(temporary) / "probe.sqlite3") as connection,
        ):
            migrate(connection)
            if not integrity(connection)["ok"]:
                raise ValueError("Temporary database failed integrity")
        return {"state": "not_initialized", "accessible": True, "action": "run migrate explicitly"}

    run("imports", imports)
    run("configuration", settings.safe_summary)
    run("schemas", schema_check)
    run("database", database_check)
    run("mcp_initialization_and_registration", lambda: asyncio.run(check_mcp()))
    return {"ok": all(check["passed"] for check in checks), "phase": 8, "checks": checks}
