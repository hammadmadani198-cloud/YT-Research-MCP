"""Bounded, reproducible internal bundle service; no live collection or public tools."""

from hashlib import sha256

from youtube_niche_mcp import __version__
from youtube_niche_mcp.analysis.models import AnalysisBundle, AnalysisRun, MetricResult
from youtube_niche_mcp.analysis.numerics import json_numbers
from youtube_niche_mcp.analysis.outcomes import resolve
from youtube_niche_mcp.analysis.repository import AnalysisRepository, AnalysisUnavailable
from youtube_niche_mcp.qualitative.dimensions import (
    content_gaps,
    faceless_feasibility,
    idea_feasibility,
    packaging_patterns,
    production_assessment,
    risk_assessment,
    saturation,
    series_structure,
    source_to_story,
)
from youtube_niche_mcp.qualitative.engagement import engagement_description
from youtube_niche_mcp.qualitative.models import (
    DIMENSIONS,
    VERSION,
    Finding,
    QualitativeOptions,
    SampleManifest,
)
from youtube_niche_mcp.qualitative.pilot import pilot_downside
from youtube_niche_mcp.qualitative.repository import ReviewRepository
from youtube_niche_mcp.services.safety import identity


def sample_manifest(population, budget, seed, cutoff):
    population = tuple(sorted(population))
    ordered = sorted(
        population, key=lambda item: (sha256(f"{seed}\0{item}".encode()).hexdigest(), item)
    )
    return SampleManifest(
        population_ids=population,
        sample_ids=tuple(ordered[:budget]),
        method="seeded_hash",
        seed=seed,
        budget=budget,
        cutoff=cutoff,
        reason="Bounded reproducible qualitative annotation review",
    )


class QualitativeService:
    def __init__(self, history):
        self.history = history
        self.repository = AnalysisRepository(history)
        self.reviews = ReviewRepository(history)

    def annotate(self, annotation):
        return self.reviews.put(annotation)

    def inspect(self, run_id):
        return self.repository.read(run_id)

    def analyze(
        self, cohort_id, options: QualitativeOptions, *, video_cohort_id=None, persist=True
    ):
        options = QualitativeOptions.model_validate(options.model_dump(mode="json"))
        now = self.history.clock()
        for profile in (options.creator, options.pilot):
            if profile and profile.expires_at <= now:
                raise AnalysisUnavailable(
                    "policy_permission_required", "Creator input retention expired"
                )
        frame = self.repository.load(cohort_id, video_cohort_id, options)
        sample = sample_manifest(
            options.annotation_ids, options.review_budget, options.seed, options.cutoff
        )
        annotations = self.reviews.read_many(sample.sample_ids, options.cutoff)
        if any(a.boundary != frame.boundary for a in annotations):
            raise ValueError("Qualitative review boundary/taxonomy differs from frozen frame")
        video_ids = {v.video_id for v in frame.videos}
        if any(
            a.payload.kind in {"packaging", "comment_theme"} and a.payload.video_id not in video_ids
            for a in annotations
        ):
            raise ValueError(
                "Public packaging/comment review must belong to the frozen video frame"
            )
        contextual = [self.repository.read(rid) for rid in options.analysis_run_ids]
        if any(
            b.run.boundary != frame.boundary
            or b.run.options.cutoff > options.cutoff
            or b.run.formula_version not in {"phase3-v1", "phase4-v1"}
            for b in contextual
        ):
            raise ValueError(
                "Contextual analytics must be compatible known-at read-only Phase 3/4 runs"
            )
        input_ids = set(frame.input_ids) | set(sample.sample_ids) | set(options.analysis_run_ids)
        for profile in (options.creator, options.pilot):
            if profile:
                input_ids.update(
                    tid
                    for r in getattr(profile, "releases", ())
                    for t in r.tasks
                    for tid in t.evidence_ids
                )
        dependency_expiry = self.reviews.validate(input_ids, options.cutoff)
        expiries = [e for e in (frame.expires_at, dependency_expiry) if e]
        expiries.extend(p.expires_at for p in (options.creator, options.pilot) if p)
        body = {
            "version": VERSION,
            "software_version": __version__,
            "frame": frame.input_hash,
            "options": options.model_dump(mode="json"),
            "reviews": [a.model_dump(mode="json") for a in annotations],
            "contextual_hashes": [b.run.input_hash for b in contextual],
        }
        digest = identity(body, self.history.secrets)
        run_id = identity([VERSION, digest], self.history.secrets)
        if (
            persist
            and self.history.connection.execute(
                "SELECT 1 FROM analysis_runs WHERE run_id=?", (run_id,)
            ).fetchone()
        ):
            return self.inspect(run_id)
        run = AnalysisRun(
            run_id=run_id,
            formula_version=VERSION,
            formula_set=DIMENSIONS,
            cohort_id=frame.cohort_id,
            video_cohort_id=frame.video_cohort_id,
            boundary=frame.boundary,
            options=options,
            input_ids=tuple(sorted(input_ids)),
            input_hash=digest,
            software_version=__version__,
            created_at=now,
            expires_at=min(expiries) if expiries else None,
        )
        outcomes = tuple(
            sorted((resolve(v, options, now) for v in frame.videos), key=lambda o: o.video_id)
        )
        ideas = idea_feasibility(annotations, options.generated_candidate_ids)
        series = series_structure(annotations, options.generated_candidate_ids)
        ideas["continuation_depth"] = series["continuation_depth"]
        axes = {
            "F14": engagement_description(self.history, outcomes, annotations, options),
            "F15": ideas,
            "F16": production_assessment(annotations, options.creator, options.production_case_id),
            "F23": pilot_downside(options.pilot),
            "content_gaps": content_gaps(annotations),
            "saturation": saturation(annotations, contextual),
            "packaging_patterns": packaging_patterns(annotations),
            "series_continuation_structure": series,
            "faceless_production": faceless_feasibility(annotations),
            "source_to_story": source_to_story(annotations),
            **risk_assessment(annotations, now),
        }
        warning = ("Descriptive feasibility axes; no F17/F18, final ranking or recommendation",)
        if len(sample.sample_ids) < len(sample.population_ids):
            warning += ("Bounded annotation sample is not full-population coverage",)
        metrics = []
        for dimension in sorted(axes):
            detail = axes[dimension]
            finding = Finding(
                dimension=dimension,
                state=detail["state"],
                label=dimension,
                value=detail.get("value"),
                evidence_ids=tuple(sorted(input_ids)),
                coverage={
                    "population_size": len(sample.population_ids),
                    "sample_size": len(sample.sample_ids),
                    "method": sample.method,
                },
                source_types=tuple(sorted({a.source_type for a in annotations})),
                warnings=warning,
                limitations=tuple(detail.get("limitations", ("Explicit creator input required",))),
                generated_at=now,
                boundary=frame.boundary,
                analysis_run_ids=options.analysis_run_ids,
            )
            metrics.append(
                MetricResult(
                    formula_id=dimension,
                    formula_version=VERSION,
                    analysis_run_id=run_id,
                    cohort_id=frame.cohort_id,
                    boundary=frame.boundary,
                    cutoff=options.cutoff,
                    age_days=options.age_days,
                    tolerance_seconds=options.tolerance_seconds,
                    goal=options.goal,
                    sample_unit="reviewed_qualitative_evidence",
                    included=len(sample.sample_ids),
                    mature=sum(o.state == "available" for o in outcomes),
                    pending=sum(o.state == "pending_maturity" for o in outcomes),
                    unknown=sum(o.state not in {"available", "pending_maturity"} for o in outcomes),
                    excluded=len(sample.population_ids) - len(sample.sample_ids),
                    independent_units=0,
                    unresolved_ownership_channels=sum(
                        v.membership.independence_state == "unknown" for v in frame.videos
                    ),
                    numerator=detail.get("numerator"),
                    denominator=detail.get("denominator"),
                    value=detail.get("value"),
                    unit="fraction"
                    if dimension == "F15"
                    else "task_hours_per_release"
                    if dimension == "F16"
                    else options.pilot.currency
                    if dimension == "F23" and options.pilot
                    else "structured_descriptor",
                    state=detail["state"],
                    warnings=warning,
                    input_manifest_hash=digest,
                    details=json_numbers(
                        {
                            **detail,
                            "finding": finding.model_dump(mode="json"),
                            "sample_manifest": sample.model_dump(mode="json"),
                            "annotation_confidences": {
                                a.annotation_id: a.confidence for a in annotations
                            },
                        }
                    ),
                )
            )
        bundle = AnalysisBundle(run=run, outcomes=outcomes, metrics=tuple(metrics))
        return self.repository.store(bundle) if persist else bundle
