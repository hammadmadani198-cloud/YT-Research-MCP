"""Public input and output contracts, defined before tool registration."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, model_validator

from youtube_niche_mcp.analysis.historical_models import HistoricalOptions
from youtube_niche_mcp.analysis.models import AnalysisOptions
from youtube_niche_mcp.decision.models import DecisionRubric, SensitivityPlan, SortConfig
from youtube_niche_mcp.eligibility.models import CohortDefinition
from youtube_niche_mcp.qualitative.models import CreatorCapacity, PilotProfile

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[\w.:-]+$")]
ChannelID = Annotated[str, Field(pattern=r"^UC[A-Za-z0-9_-]{22}$")]
VideoID = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{11}$")]
Mode = Literal["quick", "standard", "deep"]


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PageInput(PublicModel):
    limit: int = Field(default=10, ge=1, le=20, strict=True)
    cursor: str | None = Field(default=None, max_length=256)


class Acquisition(PublicModel):
    """Explicit bounded acquisition, separate from immutable analytical cutoffs."""

    refresh: bool = False
    request_id: Identifier | None = None
    provider_policy: Literal["official_only", "prefer_nexlev"] = "official_only"
    channel_ids: tuple[ChannelID, ...] = Field(default=(), max_length=100)
    video_ids: tuple[VideoID, ...] = Field(default=(), max_length=150)
    search: bool = False
    similar_channel: ChannelID | None = None

    @model_validator(mode="after")
    def explicit(self):
        if self.refresh and not self.request_id:
            raise ValueError("Refresh requires an explicit request identity")
        if not self.refresh and (
            self.search or self.channel_ids or self.video_ids or self.similar_channel
        ):
            raise ValueError("Acquisition targets require refresh")
        if self.refresh and not (
            self.search or self.channel_ids or self.video_ids or self.similar_channel
        ):
            raise ValueError("Refresh requires a bounded acquisition operation")
        if self.similar_channel and self.provider_policy != "prefer_nexlev":
            raise ValueError("Similarity acquisition requires explicit NexLev preference")
        return self


class ReviewPlan(PublicModel):
    review_ids: tuple[Identifier, ...] = Field(default=(), max_length=500)
    premise_ids: tuple[Identifier, ...] = Field(default=(), max_length=500)
    production_case_id: Identifier | None = None
    pilot: PilotProfile | None = None


class ResearchProfile(PublicModel):
    """Advanced explicit research conventions, never hidden universal thresholds."""

    measurement: AnalysisOptions | None = None
    channel_frame: CohortDefinition | None = None
    video_frame: CohortDefinition | None = None
    rubric: DecisionRubric | None = None
    historical: HistoricalOptions | None = None
    review: ReviewPlan | None = None
    sensitivity: SensitivityPlan | None = None

    @model_validator(mode="after")
    def frames(self):
        if (self.channel_frame is None) != (self.video_frame is None):
            raise ValueError("Both frame definitions are required together")
        if self.channel_frame and (
            self.channel_frame.kind not in {"entrant", "small_channel"}
            or self.video_frame.kind != "eligible_long_form"
            or self.channel_frame.boundary != self.video_frame.boundary
            or self.measurement is None
        ):
            raise ValueError("Compatible channel/video frame and measurement required")
        return self


class ResearchRequest(PageInput):
    query: str | None = Field(default=None, min_length=1, max_length=500)
    boundary_id: Identifier | None = None
    research_id: Identifier | None = None
    mode: Mode | None = None
    target_spoken_language: Literal["en"] | None = None
    geographic_context: str | None = Field(default=None, max_length=120)
    history_preference: Literal["available", "required", "exclude"] = "available"
    creator_profile: CreatorCapacity | None = None
    sorting: SortConfig | None = None
    advanced: ResearchProfile | None = None
    acquisition: Acquisition = Field(default_factory=Acquisition)

    @model_validator(mode="after")
    def subject(self):
        if not (
            self.query
            or self.boundary_id
            or self.research_id
            or (self.advanced and self.advanced.channel_frame)
        ):
            raise ValueError("A research subject is required")
        return self


class DiscoverRequest(PageInput):
    query: str = Field(min_length=1, max_length=500)
    taxonomy_version: Identifier | None = None
    mode: Mode = "standard"
    acquisition: Acquisition = Field(default_factory=Acquisition)


class DetailRequest(PageInput):
    research_id: Identifier


class CompareRequest(PublicModel):
    research_ids: tuple[Identifier, ...] = Field(min_length=2, max_length=10)
    sorting: SortConfig | None = None

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.research_ids)) != len(self.research_ids):
            raise ValueError("Distinct research identities required")
        return self


class CompetitorRequest(PageInput):
    channel_id: ChannelID
    research_id: Identifier | None = None
    acquisition: Acquisition = Field(default_factory=Acquisition)


class CompetitorCompareRequest(PublicModel):
    channel_ids: tuple[ChannelID, ...] = Field(min_length=2, max_length=10)
    research_id: Identifier | None = None

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.channel_ids)) != len(self.channel_ids):
            raise ValueError("Distinct channels required")
        return self


class WatchProfile(PublicModel):
    desired_metrics: tuple[
        Literal[
            "public_statistics",
            "floor",
            "repeatability",
            "history",
            "eligibility",
            "risk",
            "packaging",
            "demand",
        ],
        ...,
    ] = Field(min_length=1, max_length=8)
    cadence_days: int | None = Field(default=None, ge=1, le=365, strict=True)
    history_required: bool = False
    next_requested_check: AwareDatetime | None = None
    thresholds: dict[Literal["views", "uploads", "subscribers"], int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def bounded(self):
        if len(set(self.desired_metrics)) != len(self.desired_metrics) or any(
            type(v) is not int or v < 0 for v in self.thresholds.values()
        ):
            raise ValueError("Unique metrics and nonnegative integer thresholds required")
        return self


class WatchRequest(PageInput):
    action: Literal["create", "read", "update", "disable", "list"]
    watch_id: Identifier | None = None
    expected_revision: int | None = Field(default=None, ge=1, strict=True)
    profile: WatchProfile | None = None
    owner_context: Identifier = "local"
    expires_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def lifecycle(self):
        if self.action != "list" and not self.watch_id:
            raise ValueError("Watch identity required")
        if self.action in {"update", "disable"} and self.expected_revision is None:
            raise ValueError("Mutation requires expected revision")
        if self.action in {"create", "update"} and self.profile is None:
            raise ValueError("Explicit watch preferences required")
        return self


class NicheWatchRequest(WatchRequest):
    boundary_id: Identifier | None = None
    target_channels: tuple[ChannelID, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def target(self):
        if self.action == "create" and not self.boundary_id:
            raise ValueError("Niche watch requires a boundary")
        return self


class CompetitorWatchRequest(WatchRequest):
    channel_ids: tuple[ChannelID, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def target(self):
        if self.action == "create" and not self.channel_ids:
            raise ValueError("Competitor watch requires channels")
        return self


class MetricCard(PublicModel):
    dimension: str
    state: str
    value: JsonValue = None
    numerator: JsonValue = None
    denominator: JsonValue = None
    unit: str
    age_days: int
    goal: int
    mature: int
    pending: int
    unknown: int
    details: dict[str, JsonValue] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class PublicResult(PublicModel):
    state: str
    summary: str
    research_id: str | None = None
    reused_run: bool = False
    boundary: dict[str, JsonValue] = Field(default_factory=dict)
    metrics: list[MetricCard] = Field(default_factory=list)
    evidence: list[dict[str, JsonValue]] = Field(default_factory=list)
    confidence: dict[str, JsonValue] = Field(
        default_factory=lambda: {"level": "unknown", "F18": None, "history_maturity": "unavailable"}
    )
    supports: list[JsonValue] = Field(default_factory=list)
    concerns: list[JsonValue] = Field(default_factory=list)
    unknowns: list[JsonValue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: dict[str, JsonValue] = Field(default_factory=dict)
    quota: list[dict[str, JsonValue]] = Field(default_factory=list)
    capabilities: dict[str, JsonValue] = Field(default_factory=dict)
    data: dict[str, JsonValue] = Field(default_factory=dict)
    next_cursor: str | None = None
    next_available_actions: list[str] = Field(default_factory=list)


INPUTS = {
    "youtube_niche_research": ResearchRequest,
    "youtube_niche_discover": DiscoverRequest,
    "youtube_niche_compare": CompareRequest,
    **{
        f"youtube_niche_{name}": DetailRequest
        for name in (
            "outliers",
            "content_gaps",
            "packaging",
            "audience_demand",
            "sustainability",
            "risk",
            "geo_language",
            "history",
        )
    },
    "youtube_niche_watchlist": NicheWatchRequest,
    "youtube_competitor_analyze": CompetitorRequest,
    "youtube_competitor_compare": CompetitorCompareRequest,
    "youtube_competitor_watch": CompetitorWatchRequest,
}
