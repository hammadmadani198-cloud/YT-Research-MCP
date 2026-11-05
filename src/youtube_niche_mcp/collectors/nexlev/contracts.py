"""Versioned allowlist from official documentation reviewed 2026-10-02."""

from dataclasses import dataclass
from enum import StrEnum

VERSION = "nexlev-contract-2026-10-02-v1"
BASE_URL = "https://prod.dashboard.nexlev.io"


class CapabilityState(StrEnum):
    AVAILABLE = "available"
    NOT_CONFIGURED = "not_configured"
    NOT_DOCUMENTED = "not_documented_for_rest"
    ORCHESTRATOR = "orchestrator_only"
    PLAN = "plan_restricted"
    OWNER = "owner_authorization_required"
    QUOTA = "quota_limited"
    TEMPORARY = "temporarily_unavailable"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    cost: int | None = 1
    bucket: str = "nexlev_rest_plan_balance"


ENDPOINTS = {
    "channel_about": Endpoint("GET", "/api/external/channels/about", ("id",)),
    "channel_videos": Endpoint(
        "GET", "/api/external/channels/videos", ("id",), ("sort_by", "token")
    ),
    "video_details": Endpoint("GET", "/api/external/videos/details", ("videoId",)),
    "transcript": Endpoint("GET", "/api/external/videos/transcript", ("videoId",)),
    "subtitle": Endpoint("GET", "/api/external/videos/subtitle", ("videoId",)),
    "comments": Endpoint("GET", "/api/external/videos/comments", ("videoId",), ("token",)),
    "youtube_search": Endpoint(
        "GET",
        "/api/external/youtube/search",
        ("query",),
        ("type", "sortBy", "duration", "uploadDate", "features", "geo", "lang", "token"),
        bucket="nexlev_rest_search_20_per_minute",
    ),
    "similar_channels": Endpoint(
        "POST",
        "/api/external/similar-channels/search",
        ("channelId",),
        ("channelType", "level"),
        20,
    ),
    "similar_videos": Endpoint(
        "POST", "/api/external/similar-videos/videos", ("videoId",), cost=10
    ),
    "similar_thumbnails": Endpoint(
        "POST", "/api/external/similar-thumbnails/search", (), ("text", "image_url"), 10
    ),
    "channel_analytics": Endpoint(
        "POST", "/api/external/analytics/channel-analytics", ("channelId",), cost=10
    ),
    "short_vs_long": Endpoint(
        "GET",
        "/api/external/analytics/channel-analytics/{channelId}/short-vs-long-views",
        ("channelId",),
    ),
    "geography_revenue_estimate": Endpoint(
        "POST",
        "/api/external/analytics/channel-analytics/geography-revenue",
        ("channelId",),
        cost=20,
    ),
    "rpm_estimate": Endpoint("GET", "/api/external/videos/rpm", ("videoId",)),
    "niche_overview": Endpoint(
        "POST", "/api/external/niche-overview/analyze", ("channelId",), cost=20
    ),
    "channel_analysis.create": Endpoint(
        "GET",
        "/api/external/channels/analysis/job/create",
        ("channel_id",),
        cost=20,
        bucket="nexlev_rest_analysis_create_100_per_hour",
    ),
    "channel_analysis.status": Endpoint(
        "GET",
        "/api/external/channels/analysis/job/status",
        ("job_id",),
        bucket="nexlev_rest_analysis_status_500_per_hour",
    ),
}
EXTERNAL = (
    "niche_finder.semantic",
    "niche_finder.filter",
    "latest_faceless",
    "faceless_outliers.semantic",
    "faceless_outliers.filter",
    "small_channel_viral",
    "suggested_catalog",
    "daily_analytics",
    "faceless_classifier",
    "monetization_claim",
)
RESERVED = ("cms_content_owner", "cms_network_search", "promotions")
ROUTES = tuple("nexlev." + name for name in (*ENDPOINTS, *EXTERNAL, *RESERVED))
CAPABILITY_ROUTES = {
    "semantic_niche_search": "niche_finder.semantic",
    "faceless_outlier_search": "faceless_outliers.semantic",
    "small_channel_viral_search": "small_channel_viral",
    "suggested_video_discovery": "suggested_catalog",
    "latest_faceless_discovery": "latest_faceless",
    "channel_about": "channel_about",
    "channel_catalog": "channel_videos",
    "video_details": "video_details",
    "transcripts": "transcript",
    "subtitles": "subtitle",
    "comments": "comments",
    "similar_channels": "similar_channels",
    "similar_videos": "similar_videos",
    "similar_thumbnails": "similar_thumbnails",
    "daily_history": "daily_analytics",
    "channel_analytics": "channel_analytics",
    "short_vs_long": "short_vs_long",
    "revenue_estimates": "geography_revenue_estimate",
    "rpm_estimates": "rpm_estimate",
    "monetization_claims": "monetization_claim",
    "faceless_classification": "faceless_classifier",
    "niche_overview": "niche_overview",
    "channel_analysis": "channel_analysis.create",
    "cms_ownership": "cms_content_owner",
    "cms_network_search": "cms_network_search",
    "promotions": "promotions",
    "owner_private_analytics": "owner_private",
    "swipefile": "swipefile",
    "thumbnail_generation": "thumbnail_generation",
}


def capability_report(configured: bool, overrides=None):
    overrides = overrides or {}
    result = []
    for capability, route in CAPABILITY_ROUTES.items():
        if route in ENDPOINTS:
            state = CapabilityState.AVAILABLE if configured else CapabilityState.NOT_CONFIGURED
            rest_state = state
        elif route in EXTERNAL:
            state, rest_state = CapabilityState.ORCHESTRATOR, CapabilityState.NOT_DOCUMENTED
        elif route == "owner_private":
            state = rest_state = CapabilityState.OWNER
        else:
            state = rest_state = CapabilityState.UNSUPPORTED
        state = CapabilityState(overrides.get(route, state))
        result.append(
            {
                "capability": capability,
                "route": "nexlev." + route,
                "state": state.value,
                "rest_state": state.value if route in ENDPOINTS else rest_state.value,
                "contract_version": VERSION,
                "network_probed": False,
                "account_plan": "unknown",
                "available_means": "configured_contract_only",
            }
        )
    return result
