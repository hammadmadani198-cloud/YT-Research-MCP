"""Strict, attributed, retention-bounded qualitative evidence and creator scenarios."""

from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from youtube_niche_mcp.eligibility.models import Boundary, FrozenModel

VERSION = "phase5-v1"
DIMENSIONS = (
    "F14",
    "F15",
    "F16",
    "F23",
    "content_gaps",
    "saturation",
    "packaging_patterns",
    "series_continuation_structure",
    "faceless_production",
    "source_to_story",
    "rights_legal",
    "platform_policy",
    "factual_editorial",
)
Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
SourceType = Literal[
    "deterministic_parser", "provider", "model", "image_review", "human", "creator_input"
]


class SampleManifest(FrozenModel):
    population_ids: tuple[str, ...]
    sample_ids: tuple[str, ...]
    method: Literal["seeded_hash", "declared_review"]
    seed: str
    budget: int = Field(ge=1, le=500)
    cutoff: AwareDatetime
    reason: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def valid(self):
        if len(set(self.population_ids)) != len(self.population_ids):
            raise ValueError("Population IDs must be unique")
        if len(set(self.sample_ids)) != len(self.sample_ids):
            raise ValueError("Sample IDs must be unique")
        if not set(self.sample_ids) <= set(self.population_ids):
            raise ValueError("Sample must belong to declared population")
        if len(self.sample_ids) > self.budget:
            raise ValueError("Review exceeds declared budget")
        if self.method == "seeded_hash":
            ordered = sorted(
                self.population_ids,
                key=lambda item: (
                    sha256(f"{self.seed}\0{item}".encode()).hexdigest(),
                    item,
                ),
            )
            if self.sample_ids != tuple(ordered[: self.budget]):
                raise ValueError("Seeded sample does not match deterministic ordering/budget")
        return self


class Material(FrozenModel):
    material_id: str = Field(min_length=1)
    kind: Literal["counts", "title", "thumbnail", "comment", "transcript", "independent", "creator"]
    sampled_timestamps: tuple[Money, ...] = ()
    expires_at: AwareDatetime | None = None
    permission_id: str | None = None


class SourceReview(FrozenModel):
    kind: Literal["source"] = "source"
    source_reference: str = Field(min_length=1, max_length=500)
    category: Literal[
        "official_report",
        "public_record",
        "academic",
        "book",
        "archive",
        "dataset",
        "expert",
        "other",
    ]
    source_family: str = Field(min_length=1, max_length=100)
    fragility: Literal["fragile", "robust", "unknown"] = "unknown"
    checked: bool
    accessible: bool | None
    credible: bool | None
    primary: bool | None
    checked_at: AwareDatetime
    fresh_through: AwareDatetime | None = None


class Premise(FrozenModel):
    kind: Literal["premise"] = "premise"
    candidate_id: str = Field(min_length=1)
    subject: str = Field(max_length=160)
    viewer_promise: str = Field(max_length=240)
    mechanism: str = Field(max_length=160)
    long_form_treatment: str = Field(max_length=300)
    source_annotation_ids: tuple[str, ...]
    production_path: str = Field(max_length=300)
    family_node_ids: tuple[str, ...]
    premise_node_id: str | None = None
    finalist: bool = False
    finite_inventory: bool = False
    recurring_entities: tuple[str, ...] = ()
    publication_at: AwareDatetime | None = None
    outcome_video_id: str | None = None


class PremiseRelation(FrozenModel):
    kind: Literal["relation"] = "relation"
    left_candidate_id: str
    right_candidate_id: str
    relation: Literal[
        "distinct",
        "near_duplicate",
        "same_topic_different_mechanism",
        "same_mechanism_different_subject",
        "uncertain",
    ]
    provider_evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def different(self):
        if self.left_candidate_id == self.right_candidate_id:
            raise ValueError("Relation requires two different premises")
        return self


class GapReview(FrozenModel):
    kind: Literal["gap"] = "gap"
    scope: Literal["content", "packaging", "production"]
    demand: Literal["positive", "absent", "unknown", "comment_only"]
    demand_evidence_ids: tuple[str, ...] = ()
    supply: Literal["inadequate", "served", "unknown"]
    reviewed_alternative_ids: tuple[str, ...] = ()
    differentiated: bool | None
    feasible_production: bool | None
    source_annotation_ids: tuple[str, ...] = ()


class PackagingReview(FrozenModel):
    kind: Literal["packaging"] = "packaging"
    video_id: str
    title_length: int | None = Field(default=None, ge=0, le=1000)
    title_mechanisms: tuple[
        Literal[
            "question",
            "number",
            "superlative",
            "revelation",
            "conflict",
            "consequence",
            "transformation",
            "statement",
        ],
        ...,
    ] = ()
    promise_structure: str | None = Field(default=None, max_length=160)
    thumbnail_reviewed: bool = False
    face: Literal["face", "no_face", "unknown"] = "unknown"
    dominant_asset: Literal["map", "diagram", "object", "archive", "person", "other", "unknown"] = (
        "unknown"
    )
    text_density: Literal["low", "medium", "high", "unknown"] = "unknown"
    composition: str | None = Field(default=None, max_length=100)
    emotional_device: str | None = Field(default=None, max_length=100)
    provider_similarity_ids: tuple[str, ...] = ()


class Continuation(FrozenModel):
    kind: Literal["continuation"] = "continuation"
    from_candidate: str
    to_candidate: str
    structure: Literal[
        "entity",
        "chronological",
        "geographic",
        "category",
        "how_it_worked",
        "rise_fall",
        "comparison",
        "investigation",
    ]
    compatible: bool | None
    exhaustible: bool | None
    playlist_only: bool = False


class Task(FrozenModel):
    category: Literal[
        "research",
        "sourcing_fact_check",
        "script",
        "visuals",
        "rights",
        "edit_animation",
        "narration",
        "expertise",
        "updates",
        "revisions_overhead",
    ]
    hours: Money
    cash: Money
    required_skills: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    reason: str = Field(min_length=1, max_length=300)
    confidence: Literal["low", "medium", "high", "unknown"]


class ProductionReview(FrozenModel):
    kind: Literal["production"] = "production"
    case_id: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    method: Literal["timed_pilot", "estimate"]
    tasks: tuple[Task, ...] = Field(min_length=1)
    complete_task_inventory: bool = False
    required_capabilities: tuple[Literal["narration", "animation", "footage_access"], ...] = ()
    required_team_size: int | None = Field(default=None, ge=1)


class FacelessReview(FrozenModel):
    kind: Literal["faceless"] = "faceless"
    checked_paths: tuple[
        Literal[
            "archive",
            "map",
            "diagram",
            "document",
            "stock",
            "screen",
            "data",
            "animation",
            "voiceover",
            "original_graphics",
        ],
        ...,
    ]
    central_host_required: bool | None
    field_footage_required: bool | None
    expert_interview_required: bool | None
    source_annotation_ids: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()


class RightsReview(FrozenModel):
    kind: Literal["rights"] = "rights"
    asset_id: str
    asset_type: Literal[
        "broadcast",
        "sports",
        "movie_tv",
        "music",
        "archive",
        "news",
        "creator_clip",
        "stock",
        "public_domain",
        "logo",
        "original",
    ]
    dependency: Literal["low", "moderate", "high", "unknown"]
    clearance: Literal["verified", "required", "uncertain"]
    license_reference: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def verified_reference(self):
        if self.clearance == "verified" and not self.license_reference:
            raise ValueError("Verified clearance needs a reviewed reference")
        return self


class PolicyReview(FrozenModel):
    kind: Literal["policy"] = "policy"
    policy_url: Literal[
        "https://support.google.com/youtube/answer/1311392?hl=en",
        "https://support.google.com/youtube/answer/14328491?hl=en",
        "https://support.google.com/youtube/answer/6162278?hl=en",
        "https://support.google.com/youtube/answer/9783148?hl=en",
    ]
    policy_version: str = Field(min_length=1, max_length=100)
    retrieved_at: AwareDatetime
    refresh_by: AwareDatetime
    applicable_scope: str = Field(min_length=1, max_length=200)
    review_flags: tuple[
        Literal[
            "reused_content",
            "generic_repetitive",
            "mass_produced",
            "synthetic_disclosure",
            "advertiser_concern",
            "ai_persona_sensitive_advice",
        ],
        ...,
    ]

    @model_validator(mode="after")
    def refresh(self):
        if self.refresh_by <= self.retrieved_at:
            raise ValueError("Policy snapshot requires a finite refresh interval")
        return self


class FactualReview(FrozenModel):
    kind: Literal["factual"] = "factual"
    domain: Literal[
        "medical",
        "legal",
        "finance",
        "crime",
        "geopolitics",
        "history_controversy",
        "science",
        "documented_technical_history",
        "other",
    ]
    verification_burden: Literal["low", "moderate", "high", "unknown"]
    identifiable_entity: bool
    allegation_verification_needed: bool
    disputed_claims: bool
    volatile: bool
    correction_burden: Literal["low", "moderate", "high", "unknown"]
    source_annotation_ids: tuple[str, ...] = ()


class CommentTheme(FrozenModel):
    kind: Literal["comment_theme"] = "comment_theme"
    video_id: str
    theme: Literal[
        "question",
        "confusion",
        "factual_objection",
        "followup",
        "vocabulary",
        "trust_friction",
        "topic_request",
    ]
    route: str = Field(min_length=1, max_length=100)
    order: str = Field(min_length=1, max_length=100)
    pages: int = Field(ge=0)
    sample_size: int = Field(ge=0)
    retrieved_at: AwareDatetime
    relationship: Literal["top_level", "reply", "mixed"]
    availability: Literal["available", "disabled", "deleted", "unknown"]
    source: str = Field(min_length=1, max_length=200)


Payload = Annotated[
    SourceReview
    | Premise
    | PremiseRelation
    | GapReview
    | PackagingReview
    | Continuation
    | ProductionReview
    | FacelessReview
    | RightsReview
    | PolicyReview
    | FactualReview
    | CommentTheme,
    Field(discriminator="kind"),
]


class Annotation(FrozenModel):
    annotation_id: str = Field(min_length=1)
    version: Literal["phase5-v1"] = VERSION
    boundary: Boundary
    source_type: SourceType
    reviewer: str = Field(min_length=1, max_length=100)
    system_version: str = Field(min_length=1, max_length=100)
    model_version: str | None = None
    prompt_version: str | None = None
    rubric_version: str = Field(min_length=1, max_length=100)
    materials: tuple[Material, ...] = Field(min_length=1, max_length=500)
    sample: SampleManifest
    input_ids: tuple[str, ...] = Field(default=(), max_length=500)
    available_at: AwareDatetime
    decided_at: AwareDatetime
    expires_at: AwareDatetime
    confidence: Literal["low", "medium", "high", "unknown"]
    rationale: str = Field(min_length=1, max_length=400)
    limitations: tuple[Annotated[str, Field(max_length=300)], ...] = Field(min_length=1)
    payload: Payload

    @model_validator(mode="after")
    def provenance(self):
        if self.available_at > self.decided_at or self.decided_at >= self.expires_at:
            raise ValueError("Annotation clocks/expiry are incoherent")
        if self.sample.cutoff > self.decided_at:
            raise ValueError("Review cannot sample future material")
        if not {m.material_id for m in self.materials} <= set(self.sample.sample_ids):
            raise ValueError("Reviewed materials must be in sample manifest")
        if self.source_type == "model" and (not self.model_version or not self.prompt_version):
            raise ValueError("Model review needs model and prompt versions")
        for m in self.materials:
            if m.kind in {"comment", "transcript", "thumbnail", "title"}:
                if not m.expires_at or self.expires_at > m.expires_at:
                    raise ValueError(
                        "Public text/media derivation needs bounded material retention"
                    )
                if self.source_type in {"provider", "model"} and (
                    not m.permission_id or m.permission_id not in self.input_ids
                ):
                    raise ValueError(
                        "Provider/model text/media requires explicit retained permission"
                    )
        p = self.payload
        times = []
        if isinstance(p, SourceReview):
            times.append(p.checked_at)
        if isinstance(p, CommentTheme):
            times.append(p.retrieved_at)
        if isinstance(p, Premise) and p.publication_at:
            times.append(p.publication_at)
        if isinstance(p, PolicyReview):
            times.append(p.retrieved_at)
            if self.expires_at > p.refresh_by:
                raise ValueError("Policy derivative must expire by refresh deadline")
        if any(t > self.available_at for t in times):
            raise ValueError("Reviewed evidence was not available at decision time")
        return self


class CreatorCapacity(FrozenModel):
    profile_id: str = Field(min_length=1)
    declared_at: AwareDatetime
    expires_at: AwareDatetime
    hours_per_week: Money | None = None
    monthly_cash: Money | None = None
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    releases_per_week: Money | None = None
    skills: tuple[str, ...] | None = None
    narration: bool | None = None
    animation: bool | None = None
    footage_access: bool | None = None
    team_size: int | None = Field(default=None, ge=1)


class PilotRelease(FrozenModel):
    release_id: str
    publication_at: AwareDatetime
    delay_days: int = Field(default=0, ge=0)
    cash_outflow_at: AwareDatetime | None = None
    tasks: tuple[Task, ...] = Field(min_length=1)


class PilotProfile(FrozenModel):
    profile_id: str = Field(min_length=1)
    declared_at: AwareDatetime
    expires_at: AwareDatetime
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    setup_at: AwareDatetime
    setup_cash: Money
    setup_hours: Money
    releases: tuple[PilotRelease, ...] = Field(min_length=1, max_length=100)
    evaluation_hours: Money = Decimal(0)
    overhead_hours: Money = Decimal(0)
    contracted_overhead_cash: Money = Decimal(0)
    overhead_at: AwareDatetime
    cash_limit: Money | None = None
    hour_limit: Money | None = None
    runway_until: AwareDatetime | None = None
    outcome_age_days: int = Field(gt=0)
    break_even_criteria_reference: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def schedule(self):
        if len({r.release_id for r in self.releases}) != len(self.releases):
            raise ValueError("Unique pilot releases required")
        if self.expires_at <= self.declared_at:
            raise ValueError("Creator scenario must have valid retention")
        if any(r.publication_at < self.setup_at for r in self.releases):
            raise ValueError("Pilot publications cannot precede setup")
        return self


class QualitativeOptions(FrozenModel):
    version: Literal["phase5-v1"] = VERSION
    cutoff: AwareDatetime
    age_days: int = Field(gt=0)
    tolerance_seconds: int = Field(ge=0, le=604800)
    goal: int = Field(ge=0)
    annotation_ids: tuple[str, ...] = Field(default=(), max_length=5000)
    generated_candidate_ids: tuple[str, ...] = Field(default=(), max_length=5000)
    analysis_run_ids: tuple[str, ...] = Field(default=(), max_length=20)
    review_budget: int = Field(default=100, ge=1, le=500)
    seed: str = "phase5"
    production_case_id: str | None = None
    creator: CreatorCapacity | None = None
    pilot: PilotProfile | None = None

    @property
    def age(self):
        return timedelta(days=self.age_days)

    @model_validator(mode="after")
    def coherent(self):
        for ids in (self.annotation_ids, self.generated_candidate_ids, self.analysis_run_ids):
            if len(set(ids)) != len(ids):
                raise ValueError("Input inventories require unique IDs")
        for profile in (self.creator, self.pilot):
            if profile and (
                profile.declared_at > self.cutoff or profile.expires_at <= profile.declared_at
            ):
                raise ValueError("Creator inputs must be known at cutoff and retention valid")
        return self


class Finding(FrozenModel):
    dimension: str
    state: str
    label: str
    value: Decimal | int | None = None
    evidence_ids: tuple[str, ...]
    coverage: dict[str, int | str | None]
    confidence: Literal["annotation_specific_only"] = "annotation_specific_only"
    source_types: tuple[SourceType, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    generated_at: AwareDatetime
    boundary: Boundary
    analysis_run_ids: tuple[str, ...]
