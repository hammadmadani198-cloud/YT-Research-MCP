"""Public read-only async client. Construction is offline; collection is explicit."""

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

import httpx

from youtube_niche_mcp.api.quota import QuotaLedger
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.domain.foundation import Outcome, valid_id
from youtube_niche_mcp.services.safety import safe_json

PARAMETERS = {
    "search.list": {
        "part",
        "q",
        "type",
        "channelId",
        "order",
        "maxResults",
        "pageToken",
        "regionCode",
        "relevanceLanguage",
        "publishedAfter",
        "publishedBefore",
        "videoDuration",
        "videoCategoryId",
    },
    "channels.list": {"part", "id", "forHandle", "forUsername", "maxResults", "pageToken", "hl"},
    "videos.list": {"part", "id", "hl"},
    "videos.batchGetStats": {"part", "id"},
    "playlistItems.list": {"part", "playlistId", "maxResults", "pageToken"},
    "playlists.list": {"part", "channelId", "maxResults", "pageToken", "hl"},
    "commentThreads.list": {"part", "videoId", "maxResults", "pageToken", "order", "textFormat"},
    "comments.list": {"part", "parentId", "maxResults", "pageToken", "textFormat"},
}
PARTS = {
    "search.list": {"snippet"},
    "channels.list": {"id", "snippet", "statistics", "contentDetails"},
    "videos.list": {
        "id",
        "snippet",
        "statistics",
        "contentDetails",
        "status",
        "liveStreamingDetails",
    },
    "videos.batchGetStats": {"id", "snippet", "statistics", "contentDetails"},
    "playlistItems.list": {"id", "snippet", "contentDetails", "status"},
    "playlists.list": {"id", "snippet", "contentDetails", "status"},
    "commentThreads.list": {"id", "snippet", "replies"},
    "comments.list": {"id", "snippet"},
}
KNOWN_REASONS = {
    "quotaExceeded",
    "dailyLimitExceeded",
    "rateLimitExceeded",
    "userRateLimitExceeded",
    "commentsDisabled",
    "videoNotFound",
    "channelNotFound",
    "playlistNotFound",
    "forbidden",
    "channelForbidden",
    "playlistItemsNotAccessible",
    "invalidParameter",
    "invalidCriteria",
    "keyInvalid",
}


class APIError(Exception):
    def __init__(
        self, endpoint: str, outcome: Outcome, reason: str, http_status: int | None = None
    ):
        self.endpoint, self.outcome, self.reason, self.http_status = (
            endpoint,
            outcome,
            reason,
            http_status,
        )
        super().__init__(f"{endpoint}: {outcome.value} ({reason})")


@dataclass(frozen=True)
class Page:
    endpoint: str
    number: int
    request_token: str | None
    request_at: datetime
    observed_at: datetime
    available_at: datetime
    body: dict = field(repr=False)
    outcome: Outcome = Outcome.AVAILABLE
    http_status: int | None = 200
    reason: str = "ok"
    requested_parts: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntityResult:
    entity_id: str
    outcome: Outcome
    page: Page
    item: dict | None = field(default=None, repr=False)


class YouTubeClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        ledger: QuotaLedger | None = None,
        clock: Callable = lambda: datetime.now(UTC),
        sleep: Callable = asyncio.sleep,
    ):
        self.settings, self.ledger, self.clock, self.sleep = (
            settings,
            ledger or QuotaLedger(),
            clock,
            sleep,
        )
        self._http = httpx.AsyncClient(
            transport=transport,
            timeout=settings.api_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._http.aclose()

    def _validate(self, endpoint: str, params: dict) -> None:
        if endpoint not in PARAMETERS or not params.keys() <= PARAMETERS[endpoint]:
            raise ValueError("Unsupported public API request")
        secrets = self.secret_values()
        safe_json(params, secrets)
        if not set(str(params.get("part", "")).split(",")) <= PARTS[endpoint]:
            raise ValueError("Unsupported public parts")
        limit = self.ledger.contract.endpoints[endpoint].page_limit
        if "maxResults" in params and (
            limit is None or not 1 <= int(params["maxResults"]) <= limit
        ):
            raise ValueError("Page size outside local supported range")
        if endpoint == "videos.batchGetStats" and not self.settings.batch_stats_enabled:
            raise APIError(endpoint, Outcome.UNAVAILABLE, "batch_not_enabled")

    def secret_values(self) -> tuple[str, ...]:
        key = self.settings.youtube_api_key
        return (key.get_secret_value(),) if key else ()

    async def request(self, endpoint: str, params: dict, *, number: int = 1) -> Page:
        self._validate(endpoint, params)
        if not self.settings.youtube_api_key:
            raise APIError(endpoint, Outcome.UNAVAILABLE, "api_key_absent")
        method = self.ledger.contract.endpoints[endpoint]
        headers = {"X-Goog-Api-Key": self.settings.youtube_api_key.get_secret_value()}
        for attempt in range(self.settings.api_max_retries + 1):
            requested = self.clock()
            self.ledger.record(endpoint, requested)
            try:
                response = await self._http.get(
                    "https://www.googleapis.com/youtube/v3/" + method.path,
                    params=params,
                    headers=headers,
                )
            except httpx.TransportError:
                error = APIError(endpoint, Outcome.TRANSIENT_ERROR, "transport_error")
            else:
                status = response.status_code
                if status == 200:
                    try:
                        body = response.json()
                        if not isinstance(body, dict) or not isinstance(body.get("items"), list):
                            raise ValueError
                        safe_json(body, self.secret_values())
                    except (ValueError, TypeError):
                        raise APIError(
                            endpoint, Outcome.PARTIAL_RESPONSE, "malformed_response", 200
                        ) from None
                    captured = self.clock()
                    return Page(
                        endpoint,
                        number,
                        params.get("pageToken"),
                        requested,
                        captured,
                        captured,
                        body,
                        requested_parts=tuple(str(params.get("part", "")).split(",")),
                    )
                try:
                    reasons = response.json().get("error", {}).get("errors", [])
                    reason = next(
                        (
                            v.get("reason")
                            for v in reasons
                            if isinstance(v, dict) and v.get("reason") in KNOWN_REASONS
                        ),
                        "http_error",
                    )
                except (ValueError, AttributeError, TypeError):
                    reason = "http_error"
                if reason in {"quotaExceeded", "dailyLimitExceeded"}:
                    outcome = Outcome.QUOTA_LIMITED
                elif (
                    status == 429
                    or 500 <= status <= 599
                    or reason in {"rateLimitExceeded", "userRateLimitExceeded"}
                ):
                    outcome = Outcome.TRANSIENT_ERROR
                elif status == 404:
                    outcome = Outcome.DELETED_OR_PRIVATE_UNKNOWN
                else:
                    outcome = Outcome.UNAVAILABLE
                error = APIError(endpoint, outcome, reason, status)
            if error.outcome != Outcome.TRANSIENT_ERROR or attempt == self.settings.api_max_retries:
                raise error from None
            await self.sleep(min(10, self.settings.api_retry_delay_seconds * 2**attempt))
        raise AssertionError("Unreachable retry state")

    async def pages(
        self, endpoint: str, params: dict, *, max_pages: int = 10
    ) -> AsyncIterator[Page]:
        if not 1 <= max_pages <= 1000:
            raise ValueError("Bounded page count required")
        options = dict(params)
        seen = {options.get("pageToken")} if options.get("pageToken") else set()
        for number in range(1, max_pages + 1):
            started = self.clock()
            try:
                page = await self.request(endpoint, options, number=number)
            except APIError as error:
                captured = self.clock()
                yield Page(
                    endpoint,
                    number,
                    options.get("pageToken"),
                    started,
                    captured,
                    captured,
                    {"items": []},
                    error.outcome,
                    error.http_status,
                    error.reason,
                )
                return
            token = page.body.get("nextPageToken")
            if token and (not isinstance(token, str) or token in seen):
                page = replace(
                    page, outcome=Outcome.PARTIAL_RESPONSE, reason="repeated_or_invalid_token"
                )
            elif token and number == max_pages:
                page = replace(page, outcome=Outcome.PARTIAL_RESPONSE, reason="page_limit")
            yield page
            if not token or page.outcome != Outcome.AVAILABLE:
                return
            seen.add(token)
            options["pageToken"] = token

    async def hydrate(
        self, kind: str, ids: list[str], *, batch_stats: bool = False
    ) -> list[EntityResult]:
        if kind not in {"video", "channel"} or (batch_stats and kind != "video"):
            raise ValueError("Unsupported hydration kind")
        unique = list(dict.fromkeys(ids))
        if any(not valid_id(kind, value) for value in unique):
            raise ValueError("Malformed hydration identifier")
        endpoint = "videos.batchGetStats" if batch_stats else f"{kind}s.list"
        parts = (
            "snippet,statistics,contentDetails"
            if kind == "channel" or batch_stats
            else "snippet,statistics,contentDetails,status,liveStreamingDetails"
        )
        results = []
        size = self.settings.api_batch_size
        for start in range(0, len(unique), size):
            chunk = unique[start : start + size]
            requested = self.clock()
            try:
                page = await self.request(endpoint, {"part": parts, "id": ",".join(chunk)})
            except APIError as error:
                captured = self.clock()
                page = Page(
                    endpoint,
                    1,
                    None,
                    requested,
                    captured,
                    captured,
                    {"items": []},
                    error.outcome,
                    error.http_status,
                    error.reason,
                )
                results.extend(EntityResult(value, error.outcome, page) for value in chunk)
                continue
            items = {
                v["id"]: v
                for v in page.body["items"]
                if isinstance(v, dict) and isinstance(v.get("id"), str) and v["id"] in chunk
            }
            summary = page.body.get("summary", {}) if batch_stats else {}
            malformed_summary = not isinstance(summary, dict)
            failed = summary.get("failedVideoIds", []) if isinstance(summary, dict) else []
            if not isinstance(failed, list) or any(not isinstance(v, str) for v in failed):
                failed, malformed_summary = [], True
            for value in chunk:
                item = items.get(value)
                outcome = (
                    Outcome.PARTIAL_RESPONSE
                    if malformed_summary
                    else Outcome.DELETED_OR_PRIVATE_UNKNOWN
                    if value in failed
                    else (Outcome.AVAILABLE if item is not None else Outcome.API_MISSING)
                )
                results.append(
                    EntityResult(
                        value, outcome, page, item if outcome == Outcome.AVAILABLE else None
                    )
                )
        return results

    async def uploads(self, playlist_id: str, *, max_pages: int = 10) -> AsyncIterator[Page]:
        async for page in self.pages(
            "playlistItems.list",
            {"part": "snippet,contentDetails", "playlistId": playlist_id, "maxResults": 50},
            max_pages=max_pages,
        ):
            yield page

    async def playlists(self, channel_id: str, *, max_pages: int = 10) -> AsyncIterator[Page]:
        async for page in self.pages(
            "playlists.list",
            {"part": "snippet,contentDetails", "channelId": channel_id, "maxResults": 50},
            max_pages=max_pages,
        ):
            yield page

    async def comment_threads(self, video_id: str, *, max_pages: int = 10) -> AsyncIterator[Page]:
        async for page in self.pages(
            "commentThreads.list",
            {
                "part": "snippet,replies",
                "videoId": video_id,
                "textFormat": "plainText",
                "maxResults": 100,
            },
            max_pages=max_pages,
        ):
            yield page

    async def replies(self, parent_id: str, *, max_pages: int = 10) -> AsyncIterator[Page]:
        async for page in self.pages(
            "comments.list",
            {
                "part": "snippet",
                "parentId": parent_id,
                "textFormat": "plainText",
                "maxResults": 100,
            },
            max_pages=max_pages,
        ):
            yield page
