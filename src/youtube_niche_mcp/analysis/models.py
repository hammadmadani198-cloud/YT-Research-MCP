"""Versioned analysis inputs and reproducible, denominator-bearing results."""

from datetime import timedelta
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, Field, JsonValue, model_validator

from youtube_niche_mcp.analysis.historical_models import HistoricalOptions
from youtube_niche_mcp.decision.models import DecisionOptions, SensitivityOptions
from youtube_niche_mcp.eligibility.models import Boundary, CohortMember, FrozenModel
from youtube_niche_mcp.qualitative.models import QualitativeOptions

VERSION = "phase3-v1"
FORMULAS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F19", "F22", "floor")


class CatalogCoverage(FrozenModel):
    channel_id: str
    through: AwareDatetime
    available_at: AwareDatetime
    evidence_reference: str = Field(min_length=1)

    @model_validator(mode="after")
    def known_coverage(self):
        if self.through > self.available_at:
            raise ValueError("Catalog review cannot ascertain a future interval")
        return self


class AnalysisOptions(FrozenModel):
    cutoff: AwareDatetime
    age_days: int = Field(gt=0, strict=True)
    tolerance_seconds: int = Field(ge=0, le=604800, strict=True)
    goal: int = Field(ge=0, strict=True)
    low_threshold: int = Field(ge=0, strict=True)
    own_minimum: int = Field(ge=1, strict=True)
    peer_video_minimum: int = Field(ge=1, strict=True)
    peer_channel_minimum: int = Field(ge=1, strict=True)
    pooling_k: int = Field(gt=0, strict=True)
    breadth_k: int = Field(ge=1, strict=True)
    classification_minimum: Decimal = Field(ge=0, le=1)
    exposure_days: int = Field(gt=0, strict=True)
    first_k: Literal[5, 10] | None
    # The frame is reviewed/enumerated, not a claim of a YouTube census.
    finite_frame_reference: str | None = Field(default=None, min_length=1)
    coverage: tuple[CatalogCoverage, ...] = ()
    candidate_id: str | None = None
    baseline_cutoff: AwareDatetime | None = None
    anchor_id: str | None = None
    anchor_channel_id: str | None = None
    anchor_cutoff: AwareDatetime | None = None
    independence_policy: Literal["frozen_groups_unknown_provisional"] = (
        "frozen_groups_unknown_provisional"
    )
    missing_policy: Literal["never_zero_never_miss"] = "never_zero_never_miss"
    quantile_version: Literal["type7-v1"] = "type7-v1"
    observation_policy: Literal["official-exact-forward-window-v1"] = (
        "official-exact-forward-window-v1"
    )

    @model_validator(mode="after")
    def coherent(self):
        if self.candidate_id and self.baseline_cutoff is None:
            raise ValueError("Relative lift requires an explicit reference landmark")
        if self.anchor_channel_id and self.anchor_cutoff is None:
            raise ValueError("Rule anchor requires an explicit known-at landmark")
        for at in (self.baseline_cutoff, self.anchor_cutoff):
            if at and at > self.cutoff:
                raise ValueError("Landmark cannot follow analysis cutoff")
        if any(c.available_at > self.cutoff for c in self.coverage):
            raise ValueError("Future catalog review cannot ascertain past exposure")
        if len({c.channel_id for c in self.coverage}) != len(self.coverage):
            raise ValueError("Unique catalog coverage per channel required")
        return self

    @property
    def age(self):
        return timedelta(days=self.age_days)


class Snapshot(FrozenModel):
    observation_id: str
    source: str
    source_kind: str
    observed_at: AwareDatetime
    available_at: AwareDatetime
    expires_at: AwareDatetime
    value: int | None = Field(default=None, ge=0, strict=True)
    precision: str = "unknown"
    evidence_state: str = "insufficient_history"
    metric_definition: str
    outcome: str = "available"


class VideoInput(FrozenModel):
    video_id: str
    channel_id: str | None
    publication_at: AwareDatetime | None
    membership: CohortMember
    snapshots: tuple[Snapshot, ...] = ()
    topic_families: tuple[str, ...] = ()
    topic_conflict: bool = False
    identity_conflict: bool = False
    policy_blocked: bool = False


class AnalysisFrame(FrozenModel):
    cohort_id: str
    video_cohort_id: str
    kind: str
    boundary: Boundary
    freeze_at: AwareDatetime
    video_freeze_at: AwareDatetime
    members: tuple[CohortMember, ...]
    videos: tuple[VideoInput, ...]
    input_ids: tuple[str, ...]
    expires_at: AwareDatetime | None
    input_hash: str


class Outcome(FrozenModel):
    video_id: str
    channel_id: str | None
    publication_at: AwareDatetime | None
    maturity_at: AwareDatetime | None
    state: str
    value: int | None = Field(default=None, ge=0, strict=True)
    observation_id: str | None = None
    observed_at: AwareDatetime | None = None
    available_at: AwareDatetime | None = None
    reason: str

    @model_validator(mode="after")
    def unknown_is_not_zero(self):
        if (self.state == "available") != (self.value is not None):
            raise ValueError("Only an observed available outcome has a value")
        return self


class MetricResult(FrozenModel):
    formula_id: str
    formula_version: str = VERSION
    analysis_run_id: str
    cohort_id: str
    boundary: Boundary
    cutoff: AwareDatetime
    age_days: int
    tolerance_seconds: int
    goal: int
    sample_unit: str = "video_outcome"
    included: int
    mature: int
    pending: int
    unknown: int
    excluded: int
    independent_units: int
    unresolved_ownership_channels: int
    numerator: Decimal | int | None
    denominator: Decimal | int | None
    value: Decimal | int | None
    unit: str
    state: str
    warnings: tuple[str, ...]
    input_manifest_hash: str
    details: dict[str, JsonValue] = Field(default_factory=dict)


class AnalysisRun(FrozenModel):
    run_id: str
    formula_version: str = VERSION
    formula_set: tuple[str, ...] = FORMULAS
    cohort_id: str
    video_cohort_id: str
    boundary: Boundary
    options: (
        AnalysisOptions
        | HistoricalOptions
        | QualitativeOptions
        | DecisionOptions
        | SensitivityOptions
    )
    input_ids: tuple[str, ...]
    input_hash: str
    software_version: str
    created_at: AwareDatetime
    expires_at: AwareDatetime | None


class AnalysisBundle(FrozenModel):
    run: AnalysisRun
    outcomes: tuple[Outcome, ...]
    metrics: tuple[MetricResult, ...]
