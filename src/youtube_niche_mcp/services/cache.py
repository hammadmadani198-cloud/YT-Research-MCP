"""Expiring live metadata cache, separate from append-only evidence and derived identity."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from youtube_niche_mcp.api.client import APIError
from youtube_niche_mcp.domain.foundation import Outcome, timestamp
from youtube_niche_mcp.services.safety import identity, safe_json


@dataclass(frozen=True)
class CacheEntry:
    payload: dict
    source: str
    fetched_at: str
    expires_at: str
    stale: bool


@dataclass(frozen=True)
class DerivedIdentity:
    input_identity: str
    analysis_version: str
    permission_state: str = "policy_permission_required"

    @property
    def key(self) -> str:
        return identity(vars(self))


class LiveCache:
    def __init__(
        self,
        connection,
        *,
        ttl_seconds=3600,
        stale_seconds=300,
        clock=lambda: datetime.now(UTC),
        secrets: tuple[str, ...] = (),
    ):
        if not 1 <= ttl_seconds <= 30 * 86400 or not 0 <= stale_seconds <= 86400:
            raise ValueError("Cache timing outside safe retention limits")
        self.connection, self.clock, self.secrets = connection, clock, secrets
        self.ttl, self.stale_ttl = ttl_seconds, stale_seconds

    def key(self, source: str, route: str, parameters: dict) -> str:
        return identity([source, route, parameters], self.secrets)

    def put(self, source: str, route: str, parameters: dict, payload: dict) -> CacheEntry:
        key = self.key(source, route, parameters)
        encoded = safe_json(payload, self.secrets)
        at = self.clock()
        expires = at + timedelta(seconds=self.ttl)
        stale_until = min(expires + timedelta(seconds=self.stale_ttl), at + timedelta(days=30))
        with self.connection:
            self.connection.execute(
                """INSERT INTO live_cache VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(cache_key)
                DO UPDATE SET payload_json=excluded.payload_json, fetched_at=excluded.fetched_at,
                expires_at=excluded.expires_at, stale_until=excluded.stale_until""",
                (key, source, encoded, timestamp(at), timestamp(expires), timestamp(stale_until)),
            )
        return CacheEntry(payload, source, timestamp(at), timestamp(expires), False)

    def get(
        self,
        source: str,
        route: str,
        parameters: dict,
        *,
        allow_stale=False,
        purpose="metadata_display",
    ) -> CacheEntry | None:
        if purpose != "metadata_display":
            raise ValueError("Live cache cannot provide historical or snapshot evidence")
        row = self.connection.execute(
            "SELECT * FROM live_cache WHERE cache_key=?", (self.key(source, route, parameters),)
        ).fetchone()
        if row is None:
            return None
        now = timestamp(self.clock())
        stale = row["expires_at"] <= now
        if stale and (not allow_stale or row["stale_until"] <= now):
            return None
        return CacheEntry(
            json.loads(row["payload_json"]),
            row["source"],
            row["fetched_at"],
            row["expires_at"],
            stale,
        )

    async def load(
        self, source: str, route: str, parameters: dict, fetch, *, allow_stale=False
    ) -> CacheEntry:
        entry = self.get(source, route, parameters)
        if entry:
            return entry
        try:
            payload = await fetch()
        except APIError as error:
            entry = self.get(source, route, parameters, allow_stale=allow_stale)
            if error.outcome == Outcome.TRANSIENT_ERROR and entry:
                return entry
            raise
        return self.put(source, route, parameters, payload)
