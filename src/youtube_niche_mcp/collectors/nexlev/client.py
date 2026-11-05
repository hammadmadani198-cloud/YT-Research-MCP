"""Explicit documented REST calls, bounded retries/pagination/jobs, no startup probes."""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

from youtube_niche_mcp.api.quota import QuotaLedger
from youtube_niche_mcp.collectors.nexlev.contracts import (
    BASE_URL,
    ENDPOINTS,
    VERSION,
    CapabilityState,
    capability_report,
)
from youtube_niche_mcp.domain.foundation import timestamp, valid_id
from youtube_niche_mcp.services.safety import safe_json


class NexLevError(RuntimeError):
    def __init__(self, state: CapabilityState, status: int | None = None):
        self.state, self.status = state, status
        super().__init__(f"NexLev request unavailable: {state.value}")


@dataclass(frozen=True)
class ProviderQuotaEntry:
    endpoint: str
    request_count: int
    documented_cost: int | None
    charged_cost: int | None
    bucket: str
    requested_at: str
    contract_version: str = VERSION
    provider: str = "nexlev"
    access_mode: str = "documented_rest"
    cached_free: bool | None = None
    http_status: int | None = None
    plan_state: str = "unknown"


class ProviderQuotaLedger(QuotaLedger):
    """Same ledger/sink architecture; unknown charge is never represented as known zero."""

    def __init__(self, sink=None):
        super().__init__(sink=sink)

    def check_limit(self, route, at):
        limits = {
            "youtube_search": (60, 20),
            "channel_analysis.create": (3600, 100),
            "channel_analysis.status": (3600, 500),
        }
        if route in limits:
            seconds, maximum = limits[route]
            since = timestamp(at - timedelta(seconds=seconds))
            count = sum(
                e.request_count
                for e in self.entries
                if e.endpoint == "nexlev." + route and e.requested_at > since
            )
            if count >= maximum:
                raise NexLevError(CapabilityState.QUOTA)

    def record_response(self, route, at, status, payload, parameters):
        endpoint = ENDPOINTS[route]
        cost = 60 if route == "similar_channels" and parameters.get("level") == 4 else endpoint.cost
        cached = None
        if route.startswith("channel_analysis."):
            item = payload[0] if isinstance(payload, list) and payload else payload
            if isinstance(item, dict) and type(item.get("cached")) is bool:
                cached = item["cached"]
        charged = (
            0
            if status is not None and (status >= 400 or cached is True)
            else (cost if status is not None and 200 <= status < 300 else None)
        )
        entry = ProviderQuotaEntry(
            "nexlev." + route,
            1,
            cost,
            charged,
            endpoint.bucket,
            timestamp(at),
            cached_free=cached,
            http_status=status,
        )
        if self.sink:
            self.sink(entry)
        self.entries.append(entry)

    def totals(self):
        return {
            "provider": "nexlev",
            "requests": len(self.entries),
            "known_charged_cost": sum(e.charged_cost or 0 for e in self.entries),
            "unknown_charge_requests": sum(e.charged_cost is None for e in self.entries),
            "account_balance": None,
            "account_plan": "unknown",
        }


@dataclass(frozen=True)
class Response:
    route: str
    fetched_at: datetime
    available_at: datetime
    payload: dict | list = field(repr=False)
    status: int = 200
    request_parameters: dict = field(default_factory=dict, repr=False)


class NexLevClient:
    name = "nexlev"

    def __init__(
        self,
        settings,
        *,
        transport=None,
        clock=lambda: datetime.now(UTC),
        sleep=asyncio.sleep,
        quota=None,
        event_sink=None,
    ):
        self.settings, self.clock, self.sleep = settings, clock, sleep
        self.quota = quota or ProviderQuotaLedger()
        self.event_sink = event_sink
        self.overrides = {}
        self.probed = set()
        self.http = httpx.AsyncClient(
            base_url=BASE_URL,
            transport=transport,
            timeout=settings.nexlev_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )

    def secret_values(self):
        return tuple(
            k.get_secret_value()
            for k in (self.settings.nexlev_api_key, self.settings.youtube_api_key)
            if k is not None
        )

    def capabilities(self):
        report = capability_report(self.settings.nexlev_api_key is not None, self.overrides)
        for item in report:
            item["network_probed"] = item["route"].removeprefix("nexlev.") in self.probed
        return report

    async def aclose(self):
        await self.http.aclose()

    def validate(self, route, parameters, deep_mode=False):
        if route not in ENDPOINTS:
            raise NexLevError(CapabilityState.NOT_DOCUMENTED)
        endpoint = ENDPOINTS[route]
        if set(parameters) - set(endpoint.required + endpoint.optional) or any(
            name not in parameters for name in endpoint.required
        ):
            raise ValueError("Documented endpoint parameters required")
        safe_json(
            {("continuation" if k == "token" else k): v for k, v in parameters.items()},
            self.secret_values(),
        )
        for name, value in parameters.items():
            if name in {"id", "channelId", "channel_id", "videoId"}:
                if not valid_id("video" if name == "videoId" else "channel", value):
                    raise ValueError("Canonical identifier required")
            elif name == "level":
                if type(value) is not int or not 1 <= value <= 4:
                    raise ValueError("Documented similarity level required")
            elif not isinstance(value, str) or not value or len(value) > 8000:
                raise ValueError("Bounded documented string parameter required")
        enums = {
            "sort_by": {"latest", "oldest", "popular"},
            "channelType": {"all", "short"},
            "type": {"video", "channel", "playlist", "shorts", "movie", "show"},
            "sortBy": {"relevance", "popularity", "rating", "date", "views"},
            "duration": {"short", "medium", "long"},
            "uploadDate": {"hour", "today", "week", "month", "year"},
        }
        if any(k in parameters and parameters[k] not in allowed for k, allowed in enums.items()):
            raise ValueError("Documented enum value required")
        if route == "similar_thumbnails":
            if not deep_mode or len(parameters) != 1:
                raise ValueError("Deep mode and exactly one thumbnail search input required")
            if "image_url" in parameters and not re.fullmatch(
                r"https://(?:i|img)\.ytimg\.com/vi/[\w-]{11}/[\w.-]+", parameters["image_url"]
            ):
                raise ValueError("Public YouTube thumbnail URL required")
        if "job_id" in parameters and not re.fullmatch(r"[\w-]{1,128}", parameters["job_id"]):
            raise ValueError("Bounded job identifier required")
        return endpoint

    async def request(self, route, parameters, *, deep_mode=False):
        route = route.removeprefix("nexlev.")
        endpoint = self.validate(route, parameters, deep_mode)
        if self.settings.nexlev_api_key is None:
            raise NexLevError(CapabilityState.NOT_CONFIGURED)
        # Never retry costly POST analyses, job creation, or quota exhaustion.
        retries = (
            self.settings.api_max_retries
            if endpoint.method == "GET" and not (route.endswith(".create"))
            else 0
        )
        for attempt in range(retries + 1):
            at = self.clock()
            try:
                self.quota.check_limit(route, at)
            except NexLevError:
                self.overrides[route] = CapabilityState.QUOTA
                raise
            body, status, payload = dict(parameters), None, {}
            path = endpoint.path
            if "{channelId}" in path:
                path = path.format(channelId=body.pop("channelId"))
            try:
                self.probed.add(route)
                response = await self.http.request(
                    endpoint.method,
                    path,
                    headers={
                        "Authorization": "Bearer " + self.settings.nexlev_api_key.get_secret_value()
                    },
                    params=body if endpoint.method == "GET" else None,
                    json=body if endpoint.method == "POST" else None,
                    timeout=self.settings.nexlev_similarity_timeout_seconds
                    if route == "similar_channels"
                    else self.settings.nexlev_timeout_seconds,
                )
                status = response.status_code
                if 200 <= status < 300:
                    payload = response.json()
                    if not isinstance(payload, dict | list):
                        raise ValueError("Malformed response")
                    safe_json(payload, self.secret_values())
            except (httpx.HTTPError, ValueError):
                self.quota.record_response(route, at, status, {}, parameters)
                state = CapabilityState.TEMPORARY
            else:
                self.quota.record_response(route, at, status, payload, parameters)
                if 200 <= status < 300:
                    self.overrides.pop(route, None)
                    return Response(
                        "nexlev." + route,
                        at,
                        self.clock(),
                        payload,
                        status,
                        {("continuation" if k == "token" else k): v for k, v in parameters.items()},
                    )
                state = (
                    CapabilityState.NOT_CONFIGURED
                    if status == 401
                    else CapabilityState.PLAN
                    if status == 403
                    else CapabilityState.QUOTA
                    if status == 429
                    else CapabilityState.UNSUPPORTED
                    if status in {400, 404}
                    else CapabilityState.TEMPORARY
                )
            self.overrides[route] = state
            if state != CapabilityState.TEMPORARY or attempt == retries:
                raise NexLevError(state, status) from None
            await self.sleep(self.settings.api_retry_delay_seconds)
        raise AssertionError("Bounded retry invariant")

    async def pages(self, route, parameters, *, max_pages=10):
        if not 1 <= max_pages <= 100:
            raise ValueError("Bounded page count required")
        if route.removeprefix("nexlev.") not in {"channel_videos", "comments", "youtube_search"}:
            raise ValueError("Documented pagination route required")
        params, seen = dict(parameters), set()
        for number in range(1, max_pages + 1):
            result = await self.request(route, params)
            payload = result.payload
            token = payload.get("continuation") if isinstance(payload, dict) else None
            yield number, result
            if token is None or token == "":
                return
            if not isinstance(token, str) or token in seen:
                raise NexLevError(CapabilityState.TEMPORARY)
            seen.add(token)
            params["token"] = token

    async def analysis_job(self, channel_id, *, max_polls=5, poll_seconds=1):
        if not 1 <= max_polls <= 100 or not 0 <= poll_seconds <= 10:
            raise ValueError("Bounded job polling required")
        created = await self.request("channel_analysis.create", {"channel_id": channel_id})
        item = (
            created.payload[0]
            if isinstance(created.payload, list) and created.payload
            else (created.payload)
        )
        job = item.get("job_id") if isinstance(item, dict) else None
        if not isinstance(job, str) or not re.fullmatch(r"[\w-]{1,128}", job):
            raise NexLevError(CapabilityState.TEMPORARY)

        def event(state, result=None):
            entry = {
                "job_id": job,
                "channel_id": channel_id,
                "state": state,
                "route": "nexlev.channel_analysis.status",
                "at": timestamp(self.clock()),
                "cached": item.get("cached"),
                "poll_limit": max_polls,
            }
            if self.event_sink:
                self.event_sink(entry)
            return {**entry, "response": result}

        event("created")
        for _ in range(max_polls):
            try:
                result = await self.request("channel_analysis.status", {"job_id": job})
            except NexLevError:
                event("temporarily_unavailable")
                raise
            payload = result.payload
            state = payload.get("status", "unknown") if isinstance(payload, dict) else "unknown"
            if state in {"completed", "failed", "partial", "unavailable"}:
                return event(state, result)
            event("pending")
            await self.sleep(poll_seconds)
        return event("timeout")
