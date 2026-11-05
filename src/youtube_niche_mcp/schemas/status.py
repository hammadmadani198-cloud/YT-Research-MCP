from typing import Literal

from pydantic import BaseModel, ConfigDict


class ServerStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = "YouTubeNicheFinderMCP"
    version: str
    phase: Literal[8] = 8
    status: Literal["research_tools_available"] = "research_tools_available"
    research_engine_complete: Literal[True] = True
    public_tool_surface_complete: Literal[True] = True
    schema_version: int
    implemented_tools: list[str]
    planned_tools: list[str]
    live_collection_enabled: Literal[False] = False
    live_collection_configured: bool = False
    live_collection_policy: Literal["explicit_request_permission_gated"] = (
        "explicit_request_permission_gated"
    )
    youtube_api_key_present: bool = False
    history_state: str = "insufficient_history"
    database_state: str = "not_initialized"
    actual_schema_version: int | None = None
    registered_research_tool_count: Literal[15] = 15
    capabilities: list[dict] = []
    nexlev_capabilities: list[dict] = []
    eligibility_foundation_enabled: Literal[True] = True
    cohort_foundation_enabled: Literal[True] = True
    qualitative_analysis_available: Literal[True] = True
    production_analysis_available: Literal[True] = True
    risk_analysis_available: Literal[True] = True
    decision_synthesis_available: Literal[True] = True
    robustness_analysis_available: Literal[True] = True
    sorting_only_index_available: Literal[True] = True
    limitation: str = (
        "Phase 7 public research surface (15/15). Stored-only defaults; explicit refresh "
        "requires configuration and permission. Watches are intent only. No success prediction."
    )
