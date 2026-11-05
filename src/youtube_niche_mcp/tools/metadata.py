"""Short-lived display metadata. Never an input to a frozen analytical formula."""

import re

from youtube_niche_mcp.api.client import YouTubeClient
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.services.cache import LiveCache

SOURCE = "youtube:channels.list"
ROUTE = "public_declared_country"


def permission(history):
    at = timestamp(history.clock())
    return history.connection.execute(
        "SELECT permission_id,expires_at FROM retention_permissions WHERE source=? "
        "AND verified_at<=? AND expires_at>? ORDER BY verified_at DESC,permission_id LIMIT 1",
        (SOURCE, at, at),
    ).fetchone()


def declared_country(history, channel_id):
    entry = LiveCache(history.connection, clock=history.clock).get(
        SOURCE, ROUTE, {"channel_id": channel_id}
    )
    if entry and entry.fetched_at <= timestamp(history.clock()):
        accepted = history.connection.execute(
            "SELECT 1 FROM retention_permissions WHERE permission_id=? AND source=? "
            "AND verified_at<=? AND expires_at>?",
            (
                entry.payload.get("permission_id"),
                SOURCE,
                entry.fetched_at,
                timestamp(history.clock()),
            ),
        ).fetchone()
        value = entry.payload.get("declared_country")
        if accepted and isinstance(value, str) and re.fullmatch(r"[A-Z]{2}", value):
            return {
                "state": "declared_metadata",
                "value": value,
                "source": SOURCE,
                "observed_at": entry.fetched_at,
                "expires_at": entry.expires_at,
                "scope": "current_metadata_context; not audience geography or history",
            }
    return {"state": "unknown", "value": None}


class MetadataYouTubeClient(YouTubeClient):
    def __init__(self, settings, *, history, **kwargs):
        super().__init__(settings, **kwargs)
        self.display_history = history

    async def hydrate(self, kind, ids, *, batch_stats=False):
        results = await super().hydrate(kind, ids, batch_stats=batch_stats)
        accepted = permission(self.display_history) if kind == "channel" else None
        if accepted:
            cache = LiveCache(
                self.display_history.connection,
                ttl_seconds=86400,
                stale_seconds=0,
                clock=self.display_history.clock,
                secrets=self.display_history.secrets,
            )
            for result in results:
                value = (result.item or {}).get("snippet", {}).get("country")
                if isinstance(value, str) and re.fullmatch(r"[A-Z]{2}", value):
                    cache.put(
                        SOURCE,
                        ROUTE,
                        {"channel_id": result.entity_id},
                        {"declared_country": value, "permission_id": accepted[0]},
                    )
        return results
