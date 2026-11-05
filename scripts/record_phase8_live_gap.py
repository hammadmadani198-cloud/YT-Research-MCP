"""Record this release's absent-key gap and exercise the real query without HTTP."""

import json
from datetime import UTC, datetime
from pathlib import Path

import anyio

from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.status import integrity
from youtube_niche_mcp.tools.runtime import PublicSurface
from youtube_niche_mcp.tools.schemas import INPUTS

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TABLES = (
    "channel_observations",
    "video_observations",
    "analysis_runs",
    "research_watches",
    "quota_requests",
)


def counts(settings):
    with connect(settings.db_path) as connection:
        assert integrity(connection)["ok"]
        return {n: connection.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] for n in TABLES}


async def inspect(settings):
    surface, workflow = PublicSurface(settings), []
    before = counts(settings)
    for name, request in (
        ("youtube_niche_discover", {"query": "industrial history documentary", "mode": "quick"}),
        ("youtube_niche_research", {"query": "industrial history documentary", "mode": "quick"}),
        ("youtube_niche_watchlist", {"action": "list", "owner_context": "release-validation"}),
        ("youtube_competitor_watch", {"action": "list", "owner_context": "release-validation"}),
    ):
        result = await surface.dispatch(name, INPUTS[name].model_validate(request))
        assert result.state in {"insufficient_evidence", "available"}, result.state
        assert all(q["requests"] == 0 for q in result.quota)
        workflow.append(
            {
                "tool": name,
                "input": request,
                "output": result.model_dump(mode="json"),
                "bytes": len(result.model_dump_json().encode()),
            }
        )
    assert counts(settings) == before
    return workflow, before


def main():
    gates = json.loads((DOCS / "phase-8-gates.json").read_text())
    for name in ("offline_acceptance", "local_security_privacy", "provider_contract_refresh"):
        assert gates[name]["state"] == "passed", name
    settings = Settings.from_env().model_copy(update={"db_path": ROOT / "data/research.sqlite3"})
    presence = {
        "youtube": settings.youtube_api_key is not None,
        "nexlev": settings.nexlev_api_key is not None,
    }
    if any(presence.values()):
        raise ValueError("Credential state changed; this diagnostic makes no authenticated calls")
    workflow, before = anyio.run(inspect, settings)
    assert not any(before.values()), "This release gap receipt requires the verified empty database"
    now = datetime.now(UTC).isoformat()
    report = {
        "phase": 8,
        "recorded_at": now,
        "state": "skipped_not_configured",
        "release_classification": "release_candidate_with_live_provider_gap",
        "purpose": "release_validation",
        "gates": gates,
        "providers": {
            n: {
                "credential_present": False,
                "live_state": "skipped_not_configured",
                "requests": 0,
                "documented_assumed_quota": 0,
                "actual_charged_for_these_requests": 0,
                "account_remaining_quota": "unknown",
            }
            for n in presence
        },
        "calls": [],
        "mock_calls_are_live": False,
        "real_niche": {
            "query": "industrial history documentary",
            "requested_mode": "quick",
            "state": "insufficient_evidence",
            "live_workflow": "skipped_not_configured",
            "stored_only_workflow": workflow,
            "observed_channels": 0,
            "observed_videos": 0,
            "eligible_channels": 0,
            "eligible_videos": 0,
            "reviews": 0,
            "mature_historical_observations": 0,
            "coverage": "none; not a population absence claim",
            "research_id": None,
            "dependent_calls": "skipped_missing_research_id_or_real_targets",
            "watch_creation": "skipped_missing_real_boundary_or_targets",
            "database_counts_before_after": before,
        },
        "no_alternate_credentials_loaded": True,
        "no_policy_permission_created": True,
        "previous_attempts": [
            {
                "state": "diagnostic_failed_before_tool_or_http_call",
                "cause": (
                    "Initial read-only diagnostic queried quota_ledger instead of quota_requests"
                ),
                "requests": 0,
                "resolution": "Used actual schema table; preserved source integrity",
            }
        ],
    }
    (DOCS / "phase-8-live-call-receipt.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    gates["controlled_live"] = {
        "state": "skipped_not_configured",
        "recorded_at": now,
        "requests": 0,
    }
    gates["real_niche"] = {"state": "unverified_live_gap", "recorded_at": now}
    (DOCS / "phase-8-gates.json").write_text(json.dumps(gates, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "provider_key_presence": presence,
                "requests": 0,
                "quota": 0,
                "real_niche_state": "insufficient_evidence",
                "database_counts": before,
            }
        )
    )


if __name__ == "__main__":
    main()
