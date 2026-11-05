"""Classification claims are evidence, distinct from an adjudicated decision."""

from datetime import UTC
from enum import StrEnum
from typing import Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from youtube_niche_mcp.domain.foundation import valid_id


class ClassificationState(StrEnum):
    VERIFIED = "verified"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    EXCLUDED = "excluded"


class MembershipState(StrEnum):
    INCLUDED = "included"
    UNCERTAIN = "included_with_uncertainty"
    EXCLUDED = "excluded"
    PENDING = "pending_classification"
    CONFLICT = "source_conflict"
    INSUFFICIENT = "insufficient_evidence"


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("*", mode="after")
    @classmethod
    def utc(cls, value):
        if hasattr(value, "tzinfo") and value.tzinfo is not None:
            return value.astimezone(UTC)
        return value


class Subject(FrozenModel):
    entity_kind: Literal["channel", "video"]
    entity_id: str

    @model_validator(mode="after")
    def canonical(self) -> Self:
        if not valid_id(self.entity_kind, self.entity_id):
            raise ValueError("Canonical channel/video ID required")
        return self


class Claim(FrozenModel):
    subject: Subject
    field: Literal[
        "duration_seconds",
        "surface_format",
        "live_status",
        "spoken_language",
        "faceless",
        "subscriber_count",
        "continuity",
        "creator_relation",
        "niche_membership",
        "publication_at",
        "account_created_at",
        "niche_entry",
        "activity",
    ]
    value: JsonValue
    basis: Literal[
        "official_metadata",
        "official_surface",
        "default_audio_language",
        "default_language",
        "caption_metadata",
        "transcript_review",
        "human_review",
        "sample_review",
        "provider_label",
        "text_language",
        "region",
        "thumbnail",
        "production_style",
        "public_disclosure",
        "shared_company",
        "explicit_network",
        "documented_source",
    ]
    source: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    observed_at: AwareDatetime
    available_at: AwareDatetime
    reason: str = Field(min_length=1)
    # Coverage is scoped, never inferred from a provider boolean or a thumbnail.
    complete_review: bool = False
    reviewed_video_ids: tuple[str, ...] = ()
    supporting_decision_ids: tuple[str, ...] = ()
    eligible_video_count: int | None = Field(default=None, ge=0)
    data_origin: Literal["api_data", "provider_data", "independent_annotation"] = "api_data"
    permission_state: Literal["policy_required", "permitted"] = "policy_required"
    expires_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.available_at < self.observed_at:
            raise ValueError("Claim unavailable before observation")
        if self.expires_at is not None and self.expires_at <= self.available_at:
            raise ValueError("Claim expired before availability")
        ids = self.reviewed_video_ids
        if len(set(ids)) != len(ids) or any(not valid_id("video", vid) for vid in ids):
            raise ValueError("Unique canonical reviewed video IDs required")
        if self.eligible_video_count is not None and len(ids) > self.eligible_video_count:
            raise ValueError("Reviewed coverage exceeds eligible sample")
        if self.data_origin != "independent_annotation" and self.permission_state == "permitted":
            # No caller-supplied boolean can confer an API/provider permission.
            raise ValueError("External data requires a separately verified policy integration")
        return self


class Rule(FrozenModel):
    rule_id: str
    decision_type: str
    description: str
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class Classification(FrozenModel):
    subject: Subject
    decision_type: str
    label: str
    state: ClassificationState
    confidence: Literal["unknown", "low", "medium", "high"]
    rule_version: str
    evidence_ids: tuple[str, ...] = ()
    source: str
    observed_at: AwareDatetime
    available_at: AwareDatetime
    decided_at: AwareDatetime
    reason: str
    conflicts: tuple[str, ...] = ()
    details: dict[str, JsonValue] = Field(default_factory=dict)
    permission_state: Literal["policy_required", "permitted"] = "policy_required"
    expires_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        labels = {
            "long_form": {"duration_eligible", "below_threshold", "unknown"},
            "surface_format": {
                "short_form_confirmed",
                "standard_vod_confirmed",
                "probable_short",
                "probable_vod",
                "unknown",
            },
            "live_status": {
                "currently_live",
                "scheduled_live",
                "archived_live",
                "ordinary_vod",
                "unknown",
            },
            "spoken_language": {
                "verified_english",
                "likely_english",
                "mixed_language",
                "non_english",
                "unknown",
            },
            "faceless": {
                "verified_faceless",
                "likely_faceless",
                "hybrid",
                "host_central",
                "unknown",
            },
            "current_small": {
                "known_small",
                "known_not_small",
                "hidden",
                "threshold_uncertain",
                "unknown",
            },
            "niche_entry": {"first_observed_niche_entry", "unknown"},
            "continuity": {
                "continuity_consistent",
                "possible_pivot",
                "likely_pivot",
                "continuity_unknown",
                "unknown",
            },
            "activity": {
                "active_observed",
                "low_output",
                "currently_inactive_observed",
                "insufficient_followup",
                "status_unknown",
                "unknown",
            },
            "creator_independence": {"documented_group", "unknown"},
        }
        if self.label not in labels.get(self.decision_type, set()):
            raise ValueError("Unsupported decision type/label")
        if self.state == ClassificationState.VERIFIED and not self.evidence_ids:
            raise ValueError("Verification requires preserved evidence")
        if not self.observed_at <= self.available_at <= self.decided_at:
            raise ValueError("Decision clocks out of order")
        if self.expires_at is not None and self.expires_at <= self.decided_at:
            raise ValueError("Decision input already expired")
        if not set(self.conflicts) <= set(self.evidence_ids):
            raise ValueError("Conflicting claims must be preserved evidence")
        if self.conflicts and self.state != ClassificationState.CONFLICTING:
            raise ValueError("Conflicting evidence requires an explicit conflict state")
        return self


class TaxonomyNode(FrozenModel):
    node_id: str = Field(min_length=1)
    taxonomy_version: str = Field(min_length=1)
    label: str = Field(min_length=1)
    level: Literal["category", "niche", "sub_niche", "micro_niche", "topic_family", "video_premise"]
    parent_id: str | None = None
    available_at: AwareDatetime


class NicheMembership(FrozenModel):
    subject: Subject
    node_id: str
    taxonomy_version: str
    state: Literal["included", "uncertain", "excluded"]
    confidence: Literal["unknown", "low", "medium", "high"]
    evidence_ids: tuple[str, ...]
    rule_version: str
    source: str
    decided_at: AwareDatetime
    available_at: AwareDatetime
    reason: str
    semantic_layers: dict[
        Literal[
            "subject_entity",
            "viewer_promise",
            "explanatory_mechanism",
            "production_format",
            "spoken_language",
        ],
        tuple[str, ...],
    ] = Field(default_factory=dict)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.available_at > self.decided_at:
            raise ValueError("Membership cannot use future evidence")
        if not self.evidence_ids:
            raise ValueError("Membership requires evidence")
        return self


class Boundary(FrozenModel):
    boundary_id: str
    taxonomy_version: str
    node_ids: tuple[str, ...] = Field(min_length=1)
    include_descendants: bool = True
    inclusion_rules: tuple[str, ...] = ("documented subject membership",)
    exclusion_rules: tuple[str, ...] = ("explicit unrelated subject",)
    semantic_scope: dict[str, JsonValue] = Field(default_factory=dict)
    classifier_version: str
    uncertainties: tuple[str, ...] = ()


class CohortDefinition(FrozenModel):
    cohort_id: str = Field(min_length=1)
    kind: Literal["eligible_long_form", "small_channel", "entrant"]
    created_at: AwareDatetime
    known_at: AwareDatetime
    research_run: str
    boundary: Boundary
    publication_start: AwareDatetime
    publication_end: AwareDatetime
    entry_start: AwareDatetime | None = None
    entry_end: AwareDatetime | None = None
    long_form_rule: Literal["long_form_v1_6m", "long_form_v1_8m", "long_form_v1_10m"] = (
        "long_form_v1_8m"
    )
    small_rule: Literal["current_small_v1_50k", "current_small_v1_100k"] = "current_small_v1_50k"
    allow_archived_live: bool = False
    include_uncertain: bool = True
    # Rules are fixed in each frozen definition, not a global latest classifier.
    format_rule: str = "surface_format_v1"
    live_rule: str = "live_status_v1"
    language_rule: str = "spoken_language_v1"
    faceless_rule: str = "faceless_v1"
    entry_rule: str = "niche_entry_v1"

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.known_at > self.created_at or self.publication_start >= self.publication_end:
            raise ValueError("Invalid cohort clocks/window")
        if self.kind == "entrant" and (
            self.entry_start is None or self.entry_end is None or self.entry_start >= self.entry_end
        ):
            raise ValueError("Entrant cohort requires a declared entry window")
        return self


class Candidate(FrozenModel):
    subject: Subject
    entry_known_at: AwareDatetime | None = None


class CohortMember(FrozenModel):
    subject: Subject
    state: MembershipState
    reason: str
    exclusion_reason: str | None = None
    evidence_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    entry_status: dict[str, JsonValue] = Field(default_factory=dict)
    discovery_occurrences: tuple[dict[str, JsonValue], ...] = ()
    independence_unit: str
    independence_state: Literal["documented_group", "unknown"]
    uncertainties: tuple[str, ...] = ()
