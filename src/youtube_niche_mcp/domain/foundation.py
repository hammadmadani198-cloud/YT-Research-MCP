"""Typed captures and explicit outcomes; no analytics or timeless metric values."""

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from youtube_niche_mcp.domain.evidence import NumericEvidence
from youtube_niche_mcp.domain.provenance import Provenance
from youtube_niche_mcp.domain.states import EvidenceState


def timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def valid_id(kind: str, value: str) -> bool:
    pattern = r"UC[A-Za-z0-9_-]{22}" if kind == "channel" else r"[A-Za-z0-9_-]{11}"
    return bool(re.fullmatch(pattern, value))


class Outcome(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DELETED_OR_PRIVATE_UNKNOWN = "deleted_or_private_unknown"
    PROVIDER_MISSING = "provider_missing"
    API_MISSING = "API_missing"
    PARTIAL_RESPONSE = "partial_response"
    TRANSIENT_ERROR = "transient_error"
    QUOTA_LIMITED = "quota_limited"
    SOURCE_CONFLICT = "source_conflict"

    @property
    def evidence_state(self) -> EvidenceState:
        if self == self.AVAILABLE:
            return EvidenceState.AVAILABLE
        if self == self.SOURCE_CONFLICT:
            return EvidenceState.SOURCE_CONFLICT
        if self in (self.PARTIAL_RESPONSE, self.TRANSIENT_ERROR, self.QUOTA_LIMITED):
            return EvidenceState.PARTIAL_COVERAGE
        return EvidenceState.NOT_PUBLICLY_AVAILABLE


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str | None = None
    channel_id: str | None = None
    account_created_at: AwareDatetime | None = None
    publication_at: AwareDatetime | None = None
    publication_semantics: str | None = None
    upload_at: AwareDatetime | None = None
    playlist_added_at: AwareDatetime | None = None
    provider_index_at: AwareDatetime | None = None
    duration: str | None = None
    uploads_playlist_id: str | None = None
    subscriber_hidden: bool | None = None
    default_audio_language: str | None = None
    default_language: str | None = None
    live_broadcast_content: Literal["none", "live", "upcoming"] | None = None
    live_details_checked: bool = False
    actual_start_at: AwareDatetime | None = None
    actual_end_at: AwareDatetime | None = None
    scheduled_start_at: AwareDatetime | None = None

    @field_validator(
        "account_created_at",
        "publication_at",
        "upload_at",
        "playlist_added_at",
        "provider_index_at",
        "actual_start_at",
        "actual_end_at",
        "scheduled_start_at",
    )
    @classmethod
    def utc_clocks(cls, value):
        return value.astimezone(UTC) if value else None


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    capture_id: str = Field(min_length=1, max_length=128)
    entity_kind: Literal["channel", "video"]
    entity_id: str
    request_at: AwareDatetime
    provenance: Provenance
    outcome: Outcome = Outcome.AVAILABLE
    outcome_detail: str = Field(default="ok", max_length=128)
    http_status: int | None = Field(default=None, ge=100, le=599)
    metadata: Metadata = Field(default_factory=Metadata)
    metrics: dict[str, NumericEvidence] = Field(default_factory=dict)
    metric_definition: str

    @field_validator("request_at")
    @classmethod
    def utc_request(cls, value):
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not valid_id(self.entity_kind, self.entity_id):
            raise ValueError("Malformed entity identifier")
        if self.request_at > self.provenance.observed_at:
            raise ValueError("Capture cannot precede request")
        allowed = (
            {"view_count", "video_count", "subscriber_count"}
            if self.entity_kind == "channel"
            else {"view_count", "like_count", "comment_count"}
        )
        if not self.metrics.keys() <= allowed:
            raise ValueError("Unsupported public metric")
        for evidence in self.metrics.values():
            if evidence.provenance.model_dump(exclude={"precision"}) != self.provenance.model_dump(
                exclude={"precision"}
            ):
                raise ValueError("Metric provenance must match capture")
            if evidence.value is not None and (
                not isinstance(evidence.value, int) or evidence.value < 0
            ):
                raise ValueError("Public counts must be nonnegative integers")
            if self.outcome != Outcome.AVAILABLE and evidence.value is not None:
                raise ValueError("Failed capture cannot contain fabricated counts")
        if (
            self.metadata.subscriber_hidden
            and self.metrics.get("subscriber_count")
            and self.metrics["subscriber_count"].value is not None
        ):
            raise ValueError("Hidden subscriber count is unknown")
        return self


class Capability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    enabled: bool
    state: EvidenceState
    reason: str


class Decision(BaseModel):
    """Storage input only; Phase 1 never computes eligibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_kind: Literal["channel", "video"]
    entity_id: str
    decision_type: str
    state: EvidenceState
    confidence: Literal["unknown", "low", "medium", "high"] = "unknown"
    source: str
    reason: str
    rule_version: str
    observed_at: AwareDatetime
    available_at: AwareDatetime
    decided_at: AwareDatetime

    @field_validator("observed_at", "available_at", "decided_at")
    @classmethod
    def utc_clocks(cls, value):
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def clocks(self) -> Self:
        if not valid_id(self.entity_kind, self.entity_id):
            raise ValueError("Malformed subject")
        if not self.observed_at <= self.available_at <= self.decided_at:
            raise ValueError("Decision clocks out of order")
        return self
