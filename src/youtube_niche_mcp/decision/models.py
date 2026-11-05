"""Explicit, bounded decision configuration embedded in existing analysis manifests."""

from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, Field, JsonValue, model_validator

from youtube_niche_mcp.eligibility.models import FrozenModel
from youtube_niche_mcp.qualitative.models import CreatorCapacity

VERSION = "phase6-v1"
AXES = {
    "performance": ("F1", "F2", "F3"),
    "ordinary_floor": ("F5", "floor"),
    "repeatability": ("F7", "F20"),
    "entrant_accessibility": ("F4", "F19", "F21"),
    "demand_breadth": ("F8",),
    "concentration": ("F6", "F9"),
    "momentum_history": ("F10", "F11", "F12", "F13", "F20", "F21"),
    "differentiation": ("content_gaps", "saturation", "packaging_patterns"),
    "idea_depth": ("F15", "series_continuation_structure"),
    "production": ("F16", "faceless_production"),
    "sources": ("source_to_story",),
    "rights": ("rights_legal",),
    "platform_policy": ("platform_policy",),
    "factual_risk": ("factual_editorial",),
    "pilot_downside": ("F23",),
}
SORTABLE = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F15", "F16", "F19")
RULE_PATHS = {
    "F5": {("video_median",), ("video_q25",)},
    "F8": {("value",)},
    "F19": {("fraction",), ("upload_fraction",), ("known_only_fraction",)},
    "F15": {("validated_distinct_count",), ("human_review_count",)},
    "F23": {("planned_hours",), ("planned_cash_loss",)},
}
FAMILIES = ("route", "provider", "threshold", "boundary", "missingness", "ownership", "qualitative")
STATES = (
    "supported",
    "supported_with_caveats",
    "mixed_evidence",
    "weak_under_goal",
    "insufficient_evidence",
    "high_execution_burden",
    "high_rights_or_policy_dependency",
    "history_immature",
)


class MetricRule(FrozenModel):
    formula_id: str
    path: tuple[str, ...] = ()  # empty means MetricResult.value, otherwise details path
    direction: Literal["at_least", "at_most"]
    threshold: Decimal
    reference: str = Field(min_length=1)
    material_tolerance: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def internal(self):
        if self.formula_id not in {f for values in AXES.values() for f in values}:
            raise ValueError("Rules may reference only validated internal evidence dimensions")
        if not self.threshold.is_finite():
            raise ValueError("Finite threshold required")
        if self.path and self.path not in RULE_PATHS.get(self.formula_id, set()):
            raise ValueError("Only allowlisted canonical numeric paths can grade a conclusion")
        return self


class DecisionRubric(FrozenModel):
    version: str = Field(min_length=1)
    rules: tuple[MetricRule, ...] = Field(max_length=40)
    required_axes: tuple[str, ...] = (
        "performance",
        "ordinary_floor",
        "repeatability",
        "entrant_accessibility",
        "demand_breadth",
        "idea_depth",
        "production",
        "sources",
        "rights",
        "platform_policy",
        "factual_risk",
    )
    required_history: tuple[Literal["F10", "F11", "F12", "F13", "F20", "F21"], ...] = (
        "F10",
        "F11",
        "F12",
        "F13",
        "F20",
        "F21",
    )

    @model_validator(mode="after")
    def valid(self):
        if (
            not self.required_axes
            or len(set(self.required_axes)) != len(self.required_axes)
            or not set(self.required_axes) <= AXES.keys()
        ):
            raise ValueError("Unique supported required axes expected")
        if len(set(self.required_history)) != len(self.required_history):
            raise ValueError("Unique required historical dimensions expected")
        keys = [(r.formula_id, r.path) for r in self.rules]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate/conflicting grading rules")
        return self


class SortDimension(FrozenModel):
    formula_id: Literal["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F15", "F16", "F19"]
    weight: Decimal = Field(gt=0)
    low: Decimal
    high: Decimal
    direction: Literal["higher", "lower"]
    essential: bool = True
    benchmark_reference: str = Field(min_length=1)

    @model_validator(mode="after")
    def endpoints(self):
        if (
            not all(x.is_finite() for x in (self.weight, self.low, self.high))
            or self.high <= self.low
        ):
            raise ValueError("Finite ordered external normalization endpoints required")
        return self


class SortConfig(FrozenModel):
    version: str = Field(min_length=1)
    dimensions: tuple[SortDimension, ...] = Field(min_length=1, max_length=12)
    allow_partial: bool = False
    normalization: Literal["external_linear_clamped_v1"] = "external_linear_clamped_v1"

    @model_validator(mode="after")
    def unique(self):
        if len({d.formula_id for d in self.dimensions}) != len(self.dimensions):
            raise ValueError("Unique F17 dimensions required")
        return self


class CohortVariant(FrozenModel):
    variant_id: str = Field(min_length=1)
    family: Literal["threshold", "boundary"]
    label: Literal["6m", "8m", "10m", "50k", "100k", "broad", "practical", "narrow"]
    cohort_id: str
    video_cohort_id: str
    declared_at: AwareDatetime
    omissions: tuple[str, ...] = ()
    research_reference: str = Field(min_length=1)
    contextual_run_ids: tuple[str, ...] = Field(default=(), max_length=12)


class SensitivityPlan(FrozenModel):
    version: Literal["phase6-oat-v1"] = "phase6-oat-v1"
    mode: Literal["quick", "standard", "deep"] = "standard"
    declared_at: AwareDatetime
    goals: tuple[int, ...] = Field(default=(), max_length=4)
    cohorts: tuple[CohortVariant, ...] = Field(default=(), max_length=8)
    required_families: tuple[
        Literal[
            "route", "provider", "threshold", "boundary", "missingness", "ownership", "qualitative"
        ],
        ...,
    ] = FAMILIES
    max_runs: int = Field(default=24, ge=1, le=48, strict=True)

    @model_validator(mode="after")
    def budget(self):
        cap = {"quick": 8, "standard": 24, "deep": 48}[self.mode]
        if self.max_runs > cap:
            raise ValueError("Sensitivity budget exceeds declared mode")
        if len(set(self.goals)) != len(self.goals) or any(
            type(g) is not int or g < 0 for g in self.goals
        ):
            raise ValueError("Unique nonnegative integer goals required")
        if len({v.variant_id for v in self.cohorts}) != len(self.cohorts):
            raise ValueError("Unique cohort variant IDs required")
        if any(v.declared_at > self.declared_at for v in self.cohorts):
            raise ValueError("Alternative boundaries/cohorts must be predeclared")
        if len(set(self.required_families)) != len(self.required_families):
            raise ValueError("Unique sensitivity families required")
        return self


class PolicyClock(FrozenModel):
    """Independent retained receipt; contains no expired policy content or favorable finding."""

    snapshot_id: str = Field(min_length=1)
    retrieved_at: AwareDatetime
    refresh_by: AwareDatetime
    available_at: AwareDatetime
    expires_at: AwareDatetime
    provenance_reference: str = Field(min_length=1)

    @model_validator(mode="after")
    def clocks(self):
        if (
            not self.retrieved_at < self.refresh_by
            or not self.retrieved_at <= self.available_at < self.expires_at
        ):
            raise ValueError("Invalid independent policy receipt clocks")
        return self


class DecisionOptions(FrozenModel):
    decision_version: Literal["phase6-v1"] = VERSION
    cutoff: AwareDatetime
    age_days: int = Field(gt=0, strict=True)
    tolerance_seconds: int = Field(ge=0, le=604800, strict=True)
    goal: int = Field(ge=0, strict=True)
    base_run_id: str
    historical_run_ids: tuple[str, ...] = Field(default=(), max_length=6)
    qualitative_run_ids: tuple[str, ...] = Field(default=(), max_length=6)
    rubric: DecisionRubric
    sensitivity: SensitivityPlan
    policy_snapshot_ids: tuple[str, ...] = Field(default=(), max_length=20)
    policy_clocks: tuple[PolicyClock, ...] = Field(default=(), max_length=20)
    creator: CreatorCapacity | None = None
    f17: SortConfig | None = None
    f18_config: Literal["dimension_rubric_specification_agreement_v1"] = (
        "dimension_rubric_specification_agreement_v1"
    )
    frozen_discovery: tuple[dict[str, JsonValue], ...] = ()

    @property
    def analysis_run_ids(self):
        return (self.base_run_id, *self.historical_run_ids, *self.qualitative_run_ids)

    @model_validator(mode="after")
    def known(self):
        if self.sensitivity.declared_at > self.cutoff:
            raise ValueError("Sensitivity plan must precede decision cutoff")
        if len(set(self.analysis_run_ids)) != len(self.analysis_run_ids):
            raise ValueError("Unique source run IDs required")
        if self.creator and self.creator.declared_at > self.cutoff:
            raise ValueError("Future creator profile")
        if any(p.available_at > self.cutoff for p in self.policy_clocks):
            raise ValueError("Future policy receipt")
        return self


class SensitivityOptions(FrozenModel):
    sensitivity_version: Literal["phase6-sensitivity-v1"] = "phase6-sensitivity-v1"
    cutoff: AwareDatetime
    age_days: int
    tolerance_seconds: int
    goal: int
    parent_run_id: str
    family: Literal[
        "route", "provider", "threshold", "boundary", "missingness", "ownership", "qualitative"
    ]
    label: str
    changed_option: dict[str, JsonValue]
    source_run_ids: tuple[str, ...]
    input_identity: str
    comparison_version: Literal["declared_rule_flip_or_tolerance_v1"] = (
        "declared_rule_flip_or_tolerance_v1"
    )
    frozen_discovery: tuple[dict[str, JsonValue], ...] = ()
