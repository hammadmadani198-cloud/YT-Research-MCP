"""Narrow external evidence contract; trust is assigned by field, never by the caller."""

import re
from datetime import timedelta
from typing import Literal, Self

from pydantic import AwareDatetime, Field, JsonValue, StrictBool, StrictInt, model_validator

from youtube_niche_mcp.collectors.nexlev.contracts import RESERVED, ROUTES
from youtube_niche_mcp.domain.states import EvidenceState, Precision
from youtube_niche_mcp.eligibility.models import FrozenModel, Subject
from youtube_niche_mcp.services.safety import safe_json

FIELD_TRUST = {
    **dict.fromkeys(("channel_id", "video_id"), "T0"),
    **dict.fromkeys(
        (
            "title",
            "view_count",
            "subscriber_count",
            "video_count",
            "duration_seconds",
            "publication_at",
            "account_created_at",
            "audio_language",
        ),
        "T1",
    ),
    **dict.fromkeys(
        ("provider_index_at", "history", "transcript_metadata", "comment_metadata"), "T2"
    ),
    **dict.fromkeys(
        (
            "faceless",
            "spoken_language",
            "isAiChannel",
            "category",
            "format",
            "quality",
            "isQualified",
            "taxonomy_labels",
        ),
        "T3",
    ),
    **dict.fromkeys(
        (
            "outlier_score",
            "average_views",
            "median_views",
            "vph",
            "upload_frequency",
            "semantic_similarity",
            "format_similarity",
            "thumbnail_similarity",
        ),
        "T4",
    ),
    **dict.fromkeys(
        (
            "rpm",
            "rpm_range",
            "estimated_earnings",
            "monthly_revenue",
            "yearly_revenue",
            "monetized",
            "geography",
            "demographics",
        ),
        "T5",
    ),
}
COUNT_FIELDS = {"view_count", "subscriber_count", "video_count", "duration_seconds"}
TIME_FIELDS = {"publication_at", "account_created_at", "provider_index_at"}
RETENTION = {
    "provider_raw": 900,
    "provider_text": 3600,
    "normalized_public": 86400,
    "provider_history": 86400,
    "provider_annotation": 86400,
    "policy_restricted": 0,
    "owner_private_reserved": 0,
}


def plain_data(value):
    safe_json(value)
    encoded = safe_json(value)
    if len(encoded.encode()) > 2_000_000 or re.search(r"<\s*/?\s*[a-zA-Z][^>]*>", encoded):
        raise ValueError("Bounded plain evidence only; executable/HTML content prohibited")


class FieldClaim(FrozenModel):
    field: str
    value: JsonValue
    trust_class: Literal["T0", "T1", "T2", "T3", "T4", "T5"]
    state: EvidenceState = EvidenceState.APPROXIMATE
    raw_precision: Precision = Precision.UNKNOWN

    @model_validator(mode="after")
    def firewall(self) -> Self:
        if FIELD_TRUST.get(self.field) != self.trust_class:
            raise ValueError("Allowed field and internally assigned trust class required")
        plain_data(self.value)
        if self.field == "history":
            raise ValueError(
                "Use validated auxiliary history rows, never arbitrary history payload"
            )
        if self.field in {"transcript_metadata", "comment_metadata"}:
            allowed = {
                "content_hash",
                "selected_language",
                "auto_generated",
                "original",
                "translated",
                "available",
                "retention_state",
                "ordering",
                "disabled",
                "reply_relationship_state",
                "track_languages",
            }
            if not isinstance(self.value, dict) or not set(self.value) <= allowed:
                raise ValueError("Raw text belongs only in the expiring text cache")
        if (
            self.field in {"title", "audio_language", "spoken_language", "format"}
            and self.value is not None
            and not isinstance(self.value, str)
        ):
            raise ValueError("Plain string field required")
        if (
            self.field in COUNT_FIELDS
            and self.value is not None
            and (type(self.value) is not int or self.value < 0)
        ):
            raise ValueError("Nonnegative integer count/duration required")
        if self.field in TIME_FIELDS and self.value is not None:
            # Timestamp candidates keep date precision; date-only values are not fabricated UTC.
            from datetime import datetime

            if not isinstance(self.value, str):
                raise ValueError("Timestamp candidate must be a string")
            datetime.fromisoformat(self.value.replace("Z", "+00:00"))
        if (
            self.field in {"faceless", "monetized", "isAiChannel", "isQualified"}
            and self.value is not None
            and type(self.value) is not bool
        ):
            raise ValueError("Boolean provider flag required")
        if self.trust_class == "T0" and self.value is not None:
            Subject(entity_kind=self.field.removesuffix("_id"), entity_id=self.value)
        if self.state == EvidenceState.AVAILABLE and self.value is None:
            raise ValueError("Missing value cannot be available")
        return self


class HistoryPoint(FrozenModel):
    date: AwareDatetime
    subscribers: StrictInt | None = None
    views: StrictInt | None = None
    videos: StrictInt | None = None
    data_fetched_at: AwareDatetime | None = None


class ProviderRecord(FrozenModel):
    provider: Literal["nexlev"] = "nexlev"
    route: str
    subject: Subject
    provider_record_id: str = Field(min_length=1, max_length=256)
    provider_created_at: AwareDatetime | None = None
    provider_updated_at: AwareDatetime | None = None
    provider_capture_at: AwareDatetime | None = None
    fetch_at: AwareDatetime
    observed_at: AwareDatetime
    available_at: AwareDatetime
    claims: tuple[FieldClaim, ...] = Field(max_length=64)
    rank: int | None = Field(default=None, ge=1)
    page_number: int = Field(default=1, ge=1)
    normalization_version: Literal["nexlev-normalize-v1"] = "nexlev-normalize-v1"
    history: tuple[HistoryPoint, ...] = Field(default=(), max_length=3660)
    confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.route not in ROUTES or self.route.removeprefix("nexlev.") in RESERVED:
            raise ValueError("Supported nonprivate evidence route required")
        if not self.fetch_at <= self.observed_at <= self.available_at:
            raise ValueError("Local retrieval/observation/availability clocks inconsistent")
        if len({c.field for c in self.claims}) != len(self.claims):
            raise ValueError("A record cannot silently collapse repeated field claims")
        if self.history and self.route != "nexlev.daily_analytics":
            raise ValueError("Auxiliary history requires its separate route")
        for c in self.claims:
            if (
                c.trust_class == "T0"
                and c.field == self.subject.entity_kind + "_id"
                and c.value != self.subject.entity_id
            ):
                raise ValueError("Identifier does not match the subject")
        if any(
            c.field == "transcript_metadata"
            and isinstance(c.value, dict)
            and (c.value.get("translated") is True or c.value.get("original") is not True)
            for c in self.claims
        ) and any(c.field == "spoken_language" for c in self.claims):
            raise ValueError(
                "Translated/unknown-origin subtitle track cannot assert spoken language"
            )
        plain_data(self.model_dump(mode="json"))
        return self

    @property
    def expires_at(self):
        return self.observed_at + timedelta(seconds=RETENTION["normalized_public"])


class DiscoveryContext(FrozenModel):
    query: str = Field(default="", max_length=4000)
    mode: Literal["semantic", "filter", "catalog", "similarity", "weak_case_discovery_route"]
    filters: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    query_version: str = Field(default="external-query-v1", max_length=128)
    limit: int = Field(default=50, ge=1, le=1000)
    total_results: int | None = Field(default=None, ge=0)
    has_more: StrictBool | None = None
    result_ceiling: int | None = Field(default=None, ge=1)
    coverage_state: Literal["partial_coverage", "provider_index", "selected_candidates"] = (
        "partial_coverage"
    )
    coverage_limitations: tuple[str, ...] = ("Provider coverage is not a YouTube census",)
    seed_id: str | None = None
    depth: int | None = Field(default=None, ge=1, le=4)
    requested_channel_type: Literal["all", "short"] | None = None
    async_job_id: str | None = None
    requested_history_days: int | None = Field(default=None, ge=1, le=3660)
    ordering: str = "provider_order_unknown"


class EvidenceBatch(FrozenModel):
    batch_id: str = Field(min_length=1, max_length=128)
    provider: Literal["nexlev"] = "nexlev"
    route: str
    fetch_at: AwareDatetime
    records: tuple[ProviderRecord, ...] = Field(default=(), max_length=1000)
    discovery: DiscoveryContext | None = None
    access_mode: Literal["external_orchestrated", "documented_rest"] = "external_orchestrated"

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.route not in ROUTES or self.route.removeprefix("nexlev.") in RESERVED:
            raise ValueError("Unknown/reserved route prohibited")
        if any(r.route != self.route or r.fetch_at != self.fetch_at for r in self.records):
            raise ValueError("Batch route/fetch must match every record")
        if self.discovery and any(r.rank is None for r in self.records):
            raise ValueError("Discovery occurrences must preserve rank")
        plain_data(self.model_dump(mode="json"))
        return self
