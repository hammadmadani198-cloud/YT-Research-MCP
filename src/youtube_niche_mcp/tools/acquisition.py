"""Explicit, allowlisted provider acquisition; no startup probes or automatic scheduling."""

from youtube_niche_mcp.api.client import APIError
from youtube_niche_mcp.api.quota import QuotaLedger
from youtube_niche_mcp.collectors.discovery import DiscoveryService
from youtube_niche_mcp.collectors.nexlev.client import (
    NexLevClient,
    NexLevError,
    ProviderQuotaLedger,
)
from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository
from youtube_niche_mcp.collectors.nexlev.service import NexLevService
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.services.safety import identity
from youtube_niche_mcp.services.snapshots import SnapshotService
from youtube_niche_mcp.tools.errors import PublicError
from youtube_niche_mcp.tools.metadata import MetadataYouTubeClient
from youtube_niche_mcp.tools.research import BUDGETS


def permitted(history, source):
    at = timestamp(history.clock())
    return bool(
        history.connection.execute(
            (
                "SELECT 1 FROM retention_permissions WHERE source=? AND "
                "verified_at<=? AND expires_at>? LIMIT 1"
            ),
            (source, at, at),
        ).fetchone()
    )


async def acquire(
    history,
    settings,
    request,
    *,
    youtube_transport=None,
    nexlev_transport=None,
    usage=None,
    warnings=None,
):
    plan = request.acquisition
    if not plan.refresh:
        return [], []
    mode = getattr(request, "mode", None) or "standard"
    cap = BUDGETS[mode]
    if len(plan.channel_ids) > cap["channels"][1] or len(plan.video_ids) > cap["videos"][1]:
        raise PublicError("budget_exceeded")
    if plan.search and not getattr(request, "query", None):
        raise PublicError("invalid_input")
    required = []
    if plan.search:
        required += ["youtube:search.list", "youtube:videos.list"]
    if plan.video_ids:
        required.append("youtube:videos.list")
    if plan.channel_ids:
        required.append("youtube:channels.list")
    if required and settings.youtube_api_key is None:
        raise PublicError("provider_not_configured")
    if any(not permitted(history, s) for s in required):
        raise PublicError("permission_required")
    warnings = warnings if warnings is not None else []
    usage = usage if usage is not None else []
    rid = identity([plan.model_dump(mode="json"), getattr(request, "query", None), mode])[:32]
    if required:
        ledger = QuotaLedger(sink=history.record_quota)
        try:
            async with MetadataYouTubeClient(
                settings,
                history=history,
                transport=youtube_transport,
                ledger=ledger,
                clock=history.clock,
            ) as client:
                video_ids = list(plan.video_ids)
                if plan.search:
                    # Weak-case route intentionally has no minimum-view/subscriber outcome filter.
                    discovery = await DiscoveryService(client, history).collect(
                        "public-search-" + rid,
                        query=request.query,
                        page_size=50,
                        max_pages=cap["search_pages"],
                    )
                    video_ids += [
                        r[0]
                        for r in history.connection.execute(
                            (
                                "SELECT result_id FROM discovery_results WHERE run_id=? AND "
                                "result_type='video' AND outcome='available' ORDER BY rank LIMIT ?"
                            ),
                            ("public-search-" + rid, cap["videos"][1]),
                        )
                    ]
                    if discovery.get("run", {}).get("outcome") == "quota_limited":
                        warnings.append("provider_quota_limited")
                video_ids = list(dict.fromkeys(video_ids))[: cap["videos"][1]]
                if video_ids or plan.channel_ids:
                    outcome = await SnapshotService(client, history).capture(
                        "public-snapshot-" + rid,
                        video_ids=video_ids,
                        channel_ids=list(plan.channel_ids),
                    )
                    if history.connection.execute(
                        "SELECT 1 FROM snapshot_targets WHERE job_id=? AND outcome='quota_limited'",
                        ("public-snapshot-" + rid,),
                    ).fetchone():
                        warnings.append("provider_quota_limited")
                    if history.connection.execute(
                        "SELECT 1 FROM snapshot_targets WHERE job_id=? AND outcome IN "
                        "('transient_error','permission_denied','api_missing')",
                        ("public-snapshot-" + rid,),
                    ).fetchone():
                        warnings.append("provider_temporarily_unavailable")
                    if outcome.get("job", {}).get("status") not in {None, "completed", "complete"}:
                        warnings.append(
                            "Acquisition has partial target coverage; no missing outcome is filled."
                        )
        except APIError as exc:
            warnings.append(
                "provider_quota_limited"
                if exc.outcome.value == "quota_limited"
                else "provider_temporarily_unavailable"
            )
        finally:
            usage += [
                {
                    "provider": "youtube",
                    "request_class": e.endpoint,
                    "requests": e.request_count,
                    "documented_cost": e.assumed_cost,
                    "recorded_assumed_cost": e.assumed_cost,
                    "actual_charged_cost": None,
                    "bucket": e.bucket,
                    "quota_state": "recorded_contract_assumption",
                    "contract_version": e.contract_version,
                }
                for e in ledger.entries
            ]
            if not ledger.entries:
                usage.append(
                    {
                        "provider": "youtube",
                        "requests": 0,
                        "recorded_assumed_cost": 0,
                        "quota_state": "reused_collection_manifest",
                    }
                )
    if plan.similar_channel:
        if not settings.nexlev_api_key:
            warnings.append("provider_not_configured:nexlev; official/stored evidence retained")
        elif not permitted(history, "nexlev.similar_channels"):
            warnings.append(
                "permission_required:nexlev.similar_channels; official/stored evidence retained"
            )
        else:
            repository = NexLevRepository(history)
            quota = ProviderQuotaLedger(sink=repository.record_quota)
            nid = "public-similarity-" + rid
            existing = history.connection.execute(
                "SELECT expires_at FROM provider_runs WHERE run_id=?",
                (nid,),
            ).fetchone()
            expired_identity = bool(existing and existing[0] <= timestamp(history.clock()))
            if expired_identity:
                warnings.append("Expired similarity collection identity requires a new request_id.")
            try:
                if not existing:
                    client = NexLevClient(
                        settings, transport=nexlev_transport, clock=history.clock, quota=quota
                    )
                    try:
                        await NexLevService(client, repository).acquire(
                            nid,
                            "similar_channels",
                            {
                                "channelId": plan.similar_channel,
                                "level": cap["similarity_depth"],
                                "channelType": "all",
                            },
                        )
                    finally:
                        await client.aclose()
            except NexLevError as exc:
                warnings.append(
                    "provider_quota_limited:nexlev"
                    if exc.state.value == "quota_limited"
                    else "provider_unavailable:nexlev; official/stored evidence retained"
                )
            finally:
                usage += [
                    {
                        "provider": "nexlev",
                        "request_class": e.endpoint,
                        "requests": e.request_count,
                        "documented_cost": e.documented_cost,
                        "actual_charged_cost": e.charged_cost,
                        "cached_free": e.cached_free,
                        "bucket": e.bucket,
                        "quota_state": e.plan_state,
                        "contract_version": e.contract_version,
                    }
                    for e in quota.entries
                ]
                if existing:
                    usage.append(
                        {
                            "provider": "nexlev",
                            "requests": 0,
                            "actual_charged_cost": 0,
                            "quota_state": "expired_identity_requires_new_request"
                            if expired_identity
                            else "reused_collection_manifest",
                        }
                    )
    return usage, warnings
