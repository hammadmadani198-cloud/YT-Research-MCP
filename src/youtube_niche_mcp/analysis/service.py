"""Internal offline metric bundle API; no network or public tool registration."""

from youtube_niche_mcp import __version__
from youtube_niche_mcp.analysis.baselines import baseline
from youtube_niche_mcp.analysis.bounds import bounds
from youtube_niche_mcp.analysis.breadth import breadth
from youtube_niche_mcp.analysis.concentration import concentration
from youtube_niche_mcp.analysis.exposure import exposure
from youtube_niche_mcp.analysis.floor import floor
from youtube_niche_mcp.analysis.models import (
    VERSION,
    AnalysisBundle,
    AnalysisOptions,
    AnalysisRun,
    MetricResult,
)
from youtube_niche_mcp.analysis.numerics import json_numbers, ratio
from youtube_niche_mcp.analysis.outcomes import EXCLUDED, resolve
from youtube_niche_mcp.analysis.repeatability import repeatability
from youtube_niche_mcp.analysis.repository import AnalysisRepository
from youtube_niche_mcp.services.safety import identity


class AnalysisService:
    def __init__(self, history):
        self.history = history
        self.repository = AnalysisRepository(history)

    def analyze(self, cohort_id, options: AnalysisOptions, *, video_cohort_id=None, persist=True):
        options = AnalysisOptions.model_validate(options.model_dump(mode="json"))
        frame = self.repository.load(cohort_id, video_cohort_id, options)
        identity_body = {
            "version": VERSION,
            "software_version": __version__,
            "frame": frame.input_hash,
            "options": options.model_dump(mode="json"),
        }
        run_id = identity(identity_body, self.history.secrets)
        run = AnalysisRun(
            run_id=run_id,
            cohort_id=frame.cohort_id,
            video_cohort_id=frame.video_cohort_id,
            boundary=frame.boundary,
            options=options,
            input_ids=frame.input_ids,
            input_hash=frame.input_hash,
            software_version=__version__,
            created_at=self.history.clock(),
            expires_at=frame.expires_at,
        )
        outcomes = tuple(
            sorted(
                (resolve(v, options, self.history.clock()) for v in frame.videos),
                key=lambda o: o.video_id,
            )
        )
        known = [o for o in outcomes if o.state == "available"]
        pending = sum(o.state == "pending_maturity" for o in outcomes)
        excluded = sum(o.state in EXCLUDED for o in outcomes)
        unknown = len(outcomes) - len(known) - pending - excluded
        units = {
            v.membership.independence_unit
            for v in frame.videos
            if v.membership.independence_state == "documented_group"
        }
        units.update(
            m.independence_unit for m in frame.members if m.independence_state == "documented_group"
        )
        ownership_unknown = {
            v.channel_id for v in frame.videos if v.membership.independence_state == "unknown"
        }
        warning = ["Descriptive researched-frame result; not a population probability"]
        if pending or unknown:
            warning.append("Pending outcomes are not misses; unknown outcomes are not zero")
        if len(known) < 10:
            warning.append("Small observed sample; research sample targets are exploratory")
        if ownership_unknown:
            warning.append("Unknown ownership is not established independence")
        default_state = (
            "partial_coverage"
            if known and (pending or unknown)
            else "available"
            if known
            else "pending_maturity"
            if pending and not unknown
            else "insufficient_history"
            if outcomes
            else "insufficient_sample"
        )
        metrics = []

        def emit(fid, value, numerator, denominator, unit, details, state=None, extra=()):
            metrics.append(
                MetricResult(
                    formula_id=fid,
                    analysis_run_id=run_id,
                    cohort_id=cohort_id,
                    boundary=frame.boundary,
                    cutoff=options.cutoff,
                    age_days=options.age_days,
                    tolerance_seconds=options.tolerance_seconds,
                    goal=options.goal,
                    included=len(outcomes) - excluded,
                    mature=len(known),
                    pending=pending,
                    unknown=unknown,
                    excluded=excluded,
                    independent_units=len(units),
                    unresolved_ownership_channels=len(ownership_unknown),
                    numerator=numerator,
                    denominator=denominator,
                    value=value,
                    unit=unit,
                    state=state or default_state,
                    warnings=tuple(warning + list(extra)),
                    input_manifest_hash=frame.input_hash,
                    details=json_numbers(details),
                )
            )

        b, pooled, baseline_detail = baseline(frame, outcomes, options)
        candidate = next((o for o in known if o.video_id == options.candidate_id), None)
        lift = ratio(candidate.value + 1, b + 1) if candidate and b is not None else None
        emit(
            "F1",
            lift,
            candidate.value + 1 if candidate else None,
            b + 1 if b is not None else None,
            "times",
            {
                **baseline_detail,
                "candidate_id": options.candidate_id,
                "absolute_views": candidate.value if candidate else None,
            },
            state="available"
            if lift is not None
            else "insufficient_history"
            if not candidate
            else "insufficient_sample",
            extra=("Tiny baseline inflates relative lift; inspect absolute reach",)
            if b is not None and b <= 1
            else (),
        )
        emit(
            "F2",
            pooled,
            baseline_detail.get("pooled_log"),
            1 if pooled is not None else None,
            "views",
            baseline_detail,
            state="available" if pooled is not None else "insufficient_sample",
        )
        hits = sum(o.value >= options.goal for o in known)
        emit(
            "F3",
            ratio(hits, len(known)),
            hits,
            len(known),
            "fraction",
            {
                "hits": hits,
                "misses": len(known) - hits,
                "hit_ids": [o.video_id for o in known if o.value >= options.goal],
                "known_only": bool(pending or unknown),
            },
        )
        raw_exposure = exposure(frame, outcomes, options, grouped=False)
        grouped_exposure = exposure(frame, outcomes, options, grouped=True)
        emit(
            "F4",
            raw_exposure.get("fraction"),
            raw_exposure.get("successful"),
            raw_exposure.get("entrants"),
            "fraction",
            raw_exposure,
            state=raw_exposure["state"],
        )
        balanced, floor_detail = floor(outcomes, options)
        emit("F5", balanced, balanced, floor_detail["contributing_channels"], "views", floor_detail)
        emit(
            "floor",
            floor_detail["low_fraction"],
            floor_detail["low_count"],
            len(known),
            "fraction",
            floor_detail,
        )
        mass = concentration(frame, outcomes, options)
        emit(
            "F6",
            mass["videos"]["top1"],
            max((o.value for o in known), default=None),
            mass["videos"]["total"],
            "fraction",
            mass,
            state=default_state if mass["videos"]["total"] else "insufficient_sample",
        )
        follow = repeatability(frame, outcomes, options)
        emit(
            "F7",
            follow.get("windows", {}).get("5", {}).get("R_k"),
            follow.get("windows", {}).get("5", {}).get("hits"),
            5,
            "fraction",
            follow,
            state=follow["state"],
        )
        demand = breadth(frame, outcomes, options)
        emit(
            "F8",
            demand["value"],
            demand["value"],
            len(demand["families"]),
            "topic_families",
            demand,
            state=demand["state"],
        )
        emit(
            "F9",
            mass["channels"]["HHI"],
            mass["channels"]["HHI"],
            1,
            "HHI",
            mass,
            state=default_state if mass["channels"]["total"] else "insufficient_sample",
        )
        if frame.kind != "entrant":
            grouped_exposure = {
                "state": "insufficient_sample",
                "reason": "F19 requires a frozen entrant frame",
            }
        emit(
            "F19",
            grouped_exposure.get("fraction"),
            grouped_exposure.get("successful"),
            grouped_exposure.get("entrants"),
            "fraction",
            grouped_exposure,
            state=grouped_exposure["state"],
        )
        finite = bounds(
            len(outcomes) - excluded,
            hits,
            pending + unknown,
            options.finite_frame_reference is not None,
        )
        emit(
            "F22",
            finite["lower"],
            hits,
            finite["n"],
            "finite_frame_fraction",
            finite,
            state=finite["state"],
        )
        bundle = AnalysisBundle(
            run=run, outcomes=outcomes, metrics=tuple(sorted(metrics, key=lambda m: m.formula_id))
        )
        return self.repository.store(bundle) if persist else bundle

    def inspect(self, run_id):
        return self.repository.read(run_id)
