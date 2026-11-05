"""Capability descriptions do not substitute for collection or authorization."""

from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.schema import SCHEMA_VERSION
from youtube_niche_mcp.db.status import status
from youtube_niche_mcp.domain.foundation import Capability
from youtube_niche_mcp.domain.states import EvidenceState as State


def capabilities(settings: Settings, *, history_count: int = 0) -> list[Capability]:
    return [
        *(
            Capability(
                name=name,
                enabled=True,
                state=State.AVAILABLE,
                reason="Offline attributed review with sampling and retention gates; "
                "multi-axis research synthesis available with explicit evidence gates",
            )
            for name in (
                "qualitative_analysis_available",
                "production_analysis_available",
                "risk_analysis_available",
                "decision_synthesis_available",
                "robustness_analysis_available",
                "sorting_only_index_available",
            )
        ),
        Capability(
            name="historical_analytics_implemented",
            enabled=True,
            state=State.AVAILABLE,
            reason="Offline F10–F13/F20/F21; prospective history and stable panel gates apply",
        ),
        Capability(
            name="offline_core_analytics",
            enabled=True,
            state=State.AVAILABLE,
            reason="Frozen-frame F1–F9/F19/F22; input-specific permission/history gates apply",
        ),
        Capability(
            name="offline_eligibility_and_cohorts",
            enabled=True,
            state=State.AVAILABLE,
            reason="Versioned deterministic primitives; external-data permissions stay explicit",
        ),
        Capability(
            name="youtube_public_api",
            enabled=settings.youtube_api_key is not None,
            state=State.AVAILABLE if settings.youtube_api_key else State.NOT_PUBLICLY_AVAILABLE,
            reason="Configured; reachability not tested"
            if settings.youtube_api_key
            else "YOUTUBE_API_KEY absent",
        ),
        Capability(
            name="snapshot_history",
            enabled=history_count > 0,
            state=State.AVAILABLE if history_count else State.INSUFFICIENT_HISTORY,
            reason="Unexpired captures exist; coverage is not guaranteed"
            if history_count
            else "No unexpired captures",
        ),
        Capability(
            name="auxiliary_provider",
            enabled=False,
            state=State.NOT_PUBLICLY_AVAILABLE,
            reason="No provider configured",
        ),
        Capability(
            name="derived_analytics",
            enabled=False,
            state=State.POLICY_PERMISSION_REQUIRED,
            reason="Extended API-derived retention/analytics requires scoped policy acceptance",
        ),
        Capability(
            name="extended_retention",
            enabled=False,
            state=State.POLICY_PERMISSION_REQUIRED,
            reason="Scoped statistical acceptance unverified; cache/text/history classes separate",
        ),
        Capability(
            name="captions_and_owner_analytics",
            enabled=False,
            state=State.OWNER_AUTHORIZATION_REQUIRED,
            reason="No owner OAuth authorization",
        ),
        Capability(
            name="historical_age_fixed_metrics",
            enabled=False,
            state=State.INSUFFICIENT_HISTORY,
            reason="Current totals cannot reconstruct past age-fixed metrics",
        ),
    ]


def operational_status(settings: Settings) -> dict:
    from datetime import UTC, datetime

    from youtube_niche_mcp.domain.foundation import timestamp

    result = {
        "ok": True,
        "state": "not_initialized",
        "schema_version": None,
        "channel_observations": 0,
        "video_observations": 0,
        "snapshot_jobs": 0,
        "history_count": 0,
        "retention_purge_required": False,
    }
    if settings.db_path.exists():
        with connect(
            settings.db_path, read_only=True, timeout=settings.db_timeout_seconds
        ) as connection:
            version = status(connection)["schema_version"]
            result["schema_version"] = version
            if version != SCHEMA_VERSION:
                result["state"] = "migration_required"
                return result
            result["state"] = "initialized"
            now = timestamp(datetime.now(UTC))
            for kind in ("channel", "video"):
                result[f"{kind}_observations"] = connection.execute(
                    f"""SELECT COUNT(*) FROM {kind}_observations o JOIN source_records s
                    ON s.source_id=o.source_id WHERE expires_at>? AND o.available_at<=?
                    AND o.outcome='available'""",
                    (now, now),
                ).fetchone()[0]
            result["history_count"] = result["channel_observations"] + result["video_observations"]
            result["snapshot_jobs"] = connection.execute(
                "SELECT COUNT(*) FROM snapshot_jobs"
            ).fetchone()[0]
            result["retention_purge_required"] = bool(
                connection.execute(
                    "SELECT 1 FROM source_records WHERE expires_at<=? LIMIT 1", (now,)
                ).fetchone()
            )
    return result
