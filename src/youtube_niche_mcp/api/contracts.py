"""Single versioned, replaceable public endpoint/quota contract."""

from dataclasses import dataclass, field

CONTRACT_VERSION = "google-public-2026-10-02"


@dataclass(frozen=True)
class Endpoint:
    path: str
    cost: int = 1
    bucket: str = "general"
    page_limit: int | None = None


ENDPOINTS = {
    "search.list": Endpoint("search", bucket="search", page_limit=50),
    "channels.list": Endpoint("channels", page_limit=50),
    "videos.list": Endpoint("videos"),
    "playlistItems.list": Endpoint("playlistItems", page_limit=50),
    "playlists.list": Endpoint("playlists", page_limit=50),
    "commentThreads.list": Endpoint("commentThreads", page_limit=100),
    "comments.list": Endpoint("comments", page_limit=100),
    "videos.batchGetStats": Endpoint("videos:batchGetStats", bucket="video_stats"),
}


@dataclass(frozen=True)
class QuotaContract:
    version: str = CONTRACT_VERSION
    endpoints: dict[str, Endpoint] = field(default_factory=lambda: dict(ENDPOINTS))
    default_daily_assumptions: dict[str, int] = field(
        default_factory=lambda: {"search": 100, "general": 10_000, "video_stats": 10_000}
    )

    def __post_init__(self):
        if set(self.endpoints) != set(ENDPOINTS):
            raise ValueError("Quota contract must cover public endpoints exactly")
        if any(v.cost < 1 or v.path != ENDPOINTS[k].path for k, v in self.endpoints.items()):
            raise ValueError("Invalid quota contract")
