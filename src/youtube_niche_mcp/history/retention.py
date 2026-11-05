"""Scoped storage permission, never inferred from having an API key or cache TTL."""

from datetime import datetime

from pydantic import AwareDatetime, Field, model_validator

from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.models import FrozenModel
from youtube_niche_mcp.eligibility.rules import add_months
from youtube_niche_mcp.services.safety import identity, safe_json

RETENTION_CLASSES = {
    "live_cache": "TTL/stale policy; cache only, never evidence-history deletion",
    "refresh_limited_text": "30-day refresh/deletion; raw metadata captures remain bounded",
    "statistical_history": "30-day baseline; scoped acceptance required for at most 36 months",
    "derived_history": "Input permission and expiry bound derived decisions/memberships/cohorts",
    "independent_annotation": "Independently supplied annotation; no blanket API-data expiry",
    "internal_configuration": "Rules/taxonomy/frame definitions; immutable, no cache TTL",
    "policy_restricted": "Disabled without authorization; API key is not permission",
    "provider_raw": "NexLev raw response: 900 seconds; contract_review_required",
    "provider_text": "NexLev transcript/comment text: 3600 seconds; contract_review_required",
    "provider_normalized_public": "NexLev public fact candidates: 24 hours, official hydrate",
    "provider_historical_statistics": ("Auxiliary NexLev series: 24 hours; separate OWN_HISTORY"),
    "provider_annotation": "Provider classifications/estimates: 24 hours, no permission inferred",
    "owner_private_reserved": "Disabled; separate owner authorization/privacy lifecycle deferred",
}


class StoragePermission(FrozenModel):
    """Trusted administrative input documenting acceptance, not a request for it."""

    source: str = Field(min_length=1)
    approval_reference: str = Field(min_length=1)
    verified_by: str = Field(min_length=1)
    verified_at: AwareDatetime
    expires_at: AwareDatetime
    statistical_months: int = Field(ge=1, le=36, strict=True)

    @model_validator(mode="after")
    def coherent(self):
        if self.expires_at <= self.verified_at:
            raise ValueError("Acceptance validity interval required")
        return self


class RetentionRepository:
    def __init__(self, history):
        self.history = history
        self.connection = history.connection

    def record_permission(self, permission: StoragePermission):
        permission = StoragePermission.model_validate(permission.model_dump(mode="json"))
        if permission.verified_at > self.history.clock():
            raise ValueError("Cannot record future verification")
        body = permission.model_dump(mode="json")
        pid = identity(body, self.history.secrets)
        safe_json(body, self.history.secrets)
        with atomic(self.connection):
            self.connection.execute(
                "INSERT OR IGNORE INTO retention_permissions VALUES(?,?,?,?,?,?,?)",
                (
                    pid,
                    permission.source,
                    permission.approval_reference,
                    permission.verified_by,
                    timestamp(permission.verified_at),
                    timestamp(permission.expires_at),
                    permission.statistical_months,
                ),
            )
        return pid

    def archive(self, observation, observation_id):
        p = observation.provenance
        # Acceptance must have been verified when the statistics became available.
        # This does not rescue already-expired data or infer retrospective approval.
        row = self.connection.execute(
            """SELECT * FROM retention_permissions WHERE source=?
            AND verified_at<=? AND expires_at>? ORDER BY verified_at DESC,permission_id LIMIT 1""",
            (p.source, timestamp(p.available_at), timestamp(self.history.clock())),
        ).fetchone()
        if not row or not observation.metrics or p.available_at > self.history.clock():
            return
        expires = min(
            timestamp(add_months(p.observed_at, row["statistical_months"])), row["expires_at"]
        )
        if expires <= timestamp(self.history.clock()):
            return
        # Store only whitelisted statistical evidence. No titles, descriptions,
        # names, raw provider payloads, or text metadata accompany extended history.
        body = {
            "metrics": {k: v.model_dump(mode="json") for k, v in observation.metrics.items()},
            "metric_definition": observation.metric_definition,
        }
        self.connection.execute(
            "INSERT OR IGNORE INTO statistical_history VALUES(?,?,?,?,?,?,?,?,?)",
            (
                observation_id,
                observation.entity_kind,
                observation.entity_id,
                p.source,
                timestamp(p.observed_at),
                timestamp(p.available_at),
                expires,
                row["permission_id"],
                safe_json(body, self.history.secrets),
            ),
        )

    def snapshots(self, kind: str, entity_id: str, at: datetime):
        self.history.names(kind)
        rows = self.connection.execute(
            """SELECT h.* FROM statistical_history h
            JOIN retention_permissions p USING(permission_id)
            WHERE entity_kind=? AND entity_id=? AND h.observed_at<=? AND h.available_at<=?
            AND h.expires_at>? AND p.expires_at>?
            ORDER BY h.observed_at DESC,h.available_at DESC,h.observation_id""",
            (
                kind,
                entity_id,
                timestamp(at),
                timestamp(at),
                timestamp(self.history.clock()),
                timestamp(self.history.clock()),
            ),
        )
        return [dict(row) for row in rows]
