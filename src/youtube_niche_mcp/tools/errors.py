"""Fixed public error vocabulary. Never serialize dependency exception text."""

from youtube_niche_mcp.tools.schemas import PublicResult

MESSAGES = {
    "database_busy": "Storage is busy. Retry after the current writer finishes.",
    "database_unavailable": (
        "Storage cannot be read safely. Check access and integrity or restore a verified database."
    ),
    "invalid_input": "Inputs do not satisfy this tool's typed research contract.",
    "insufficient_evidence": (
        "Compatible retained evidence or an explicit research profile is required."
    ),
    "provider_not_configured": (
        "The requested provider is not configured; stored evidence remains usable."
    ),
    "provider_quota_limited": (
        "Requested acquisition is quota-limited; retained evidence remains usable."
    ),
    "permission_required": "Applicable source permission or retained dependencies are unavailable.",
    "history_unavailable": (
        "Compatible observed history is unavailable; current counts cannot fill it."
    ),
    "policy_refresh_required": "An applicable policy review requires refresh.",
    "incompatible_runs": (
        "Research modes, measurement definitions or frozen profiles are incompatible."
    ),
    "source_conflict": "Retained source evidence conflicts or its immutable manifest has changed.",
    "internal_error": "The request could not be completed. No private diagnostic data is returned.",
    "not_found": "The requested retained subject or watch definition is unavailable.",
    "revision_conflict": (
        "The watch revision changed or the creation identity has different preferences."
    ),
    "schema_upgrade_required": (
        "Storage requires an explicit administrative migration before this operation."
    ),
    "budget_exceeded": (
        "The retained frame exceeds the requested mode budget; choose"
        " a compatible mode or explicit frame."
    ),
}


class PublicError(Exception):
    def __init__(self, state):
        self.state = state if state in MESSAGES else "internal_error"
        super().__init__(MESSAGES[self.state])


def failure(state):
    state = state if state in MESSAGES else "internal_error"
    return PublicResult(state=state, summary=MESSAGES[state], unknowns=[state])
