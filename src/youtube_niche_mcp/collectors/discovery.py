"""Every discovery occurrence survives; canonical identity alone is deduplicated."""

from datetime import timedelta

from youtube_niche_mcp import __version__
from youtube_niche_mcp.api.client import YouTubeClient
from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import Outcome, timestamp, valid_id
from youtube_niche_mcp.history.repository import HistoryRepository
from youtube_niche_mcp.services.safety import safe_json


class DiscoveryService:
    def __init__(self, client: YouTubeClient, repository: HistoryRepository):
        self.client, self.repository = client, repository

    async def collect(
        self,
        run_id: str,
        *,
        route: str = "search.list",
        query: str = "",
        filters: dict | None = None,
        page_size: int = 50,
        max_pages: int = 10,
    ) -> dict:
        if route not in {"search.list", "playlistItems.list"} or not run_id or len(run_id) > 128:
            raise ValueError("Supported route and explicit run identity required")
        if not 1 <= max_pages <= 1000:
            raise ValueError("Bounded page count required")
        parameters = {
            "part": "snippet" if route == "search.list" else "snippet,contentDetails",
            "maxResults": page_size,
        }
        if route == "search.list":
            parameters.update(q=query, type="video", order="relevance")
        parameters.update(filters or {})
        self.client._validate(route, parameters)
        encoded = safe_json(
            {"parameters": parameters, "max_pages": max_pages}, self.client.secret_values()
        )
        safe_json([run_id, query], self.client.secret_values())
        connection = self.repository.connection
        existing = connection.execute(
            "SELECT * FROM discovery_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if existing:
            if (
                existing["filters_json"] != encoded
                or existing["route"] != route
                or existing["query"] != query
            ):
                raise ValueError("Discovery replay cannot change its manifest")
            if existing["finished_at"] is None:
                raise ValueError(
                    "Interrupted discovery requires a new run identity; "
                    "original partial manifest preserved"
                )
            return self.manifest(run_id)
        started = self.client.clock()
        with atomic(connection):
            connection.execute(
                "INSERT INTO discovery_runs "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)",
                (
                    run_id,
                    query,
                    route,
                    "youtube",
                    parameters.get("order"),
                    encoded,
                    parameters.get("regionCode"),
                    parameters.get("relevanceLanguage"),
                    "uploads_catalog" if route == "playlistItems.list" else "search_discovery",
                    parameters["maxResults"],
                    timestamp(started),
                    "running",
                    __version__,
                    timestamp(started + timedelta(days=30)),
                ),
            )
        rank, final = 0, Outcome.AVAILABLE
        async for page in self.client.pages(route, parameters, max_pages=max_pages):
            final = page.outcome
            with atomic(connection):
                connection.execute(
                    "INSERT INTO discovery_pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        page.number,
                        page.request_token,
                        page.body.get("nextPageToken")
                        if isinstance(page.body.get("nextPageToken"), str)
                        else None,
                        timestamp(page.request_at),
                        timestamp(page.observed_at),
                        timestamp(page.available_at),
                        page.outcome.value,
                        page.http_status,
                        page.reason,
                    ),
                )
                for page_rank, item in enumerate(page.body["items"], start=1):
                    rank += 1
                    entity_id, kind = self.result_identity(route, item)
                    valid = (
                        kind in {"video", "channel"}
                        and isinstance(entity_id, str)
                        and valid_id(kind, entity_id)
                    )
                    outcome = Outcome.AVAILABLE if valid else Outcome.PARTIAL_RESPONSE
                    if not valid:
                        final = Outcome.PARTIAL_RESPONSE
                    connection.execute(
                        "INSERT INTO discovery_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            run_id,
                            rank,
                            page.number,
                            page_rank,
                            entity_id,
                            kind,
                            "returned_identifier" if valid else "malformed_or_missing_identifier",
                            outcome.value,
                            timestamp(page.observed_at),
                            timestamp(page.available_at),
                        ),
                    )
                    if valid:
                        self.repository.ensure_entity(kind, entity_id, page.available_at)
            if final != Outcome.AVAILABLE and page.outcome == Outcome.AVAILABLE:
                # Bad IDs do not terminate pagination; mark overall coverage partial.
                final = Outcome.PARTIAL_RESPONSE
        malformed = connection.execute(
            "SELECT 1 FROM discovery_results WHERE run_id=? AND outcome!=? LIMIT 1",
            (run_id, Outcome.AVAILABLE.value),
        ).fetchone()
        if malformed and final == Outcome.AVAILABLE:
            final = Outcome.PARTIAL_RESPONSE
        with atomic(connection):
            connection.execute(
                "UPDATE discovery_runs SET finished_at=?, outcome=? WHERE run_id=?",
                (timestamp(self.client.clock()), final.value, run_id),
            )
        return self.manifest(run_id)

    @staticmethod
    def result_identity(route: str, item) -> tuple[str | None, str | None]:
        if not isinstance(item, dict):
            return None, None
        if route == "playlistItems.list":
            details = item.get("contentDetails")
            snippet = item.get("snippet")
            resource = snippet.get("resourceId", {}) if isinstance(snippet, dict) else {}
            value = details.get("videoId") if isinstance(details, dict) else None
            value = value or (resource.get("videoId") if isinstance(resource, dict) else None)
            return value if isinstance(value, str) else None, "video"
        resource = item.get("id")
        if not isinstance(resource, dict):
            return resource if isinstance(resource, str) else None, None
        for kind in ("video", "channel"):
            value = resource.get(kind + "Id")
            if value is not None:
                return value if isinstance(value, str) else None, kind
        return None, None

    def manifest(self, run_id: str) -> dict:
        connection = self.repository.connection
        run = connection.execute(
            "SELECT * FROM discovery_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run and run["expires_at"] <= timestamp(self.client.clock()):
            return {"run": None, "pages": [], "results": [], "retention_state": "expired"}
        return {
            "run": dict(run) if run else None,
            "pages": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM discovery_pages WHERE run_id=? ORDER BY page_number", (run_id,)
                )
            ],
            "results": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM discovery_results WHERE run_id=? ORDER BY rank", (run_id,)
                )
            ],
        }
