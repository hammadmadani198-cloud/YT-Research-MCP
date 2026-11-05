"""Retained offline decision service with immutable replay and transitive provenance."""

from collections import defaultdict

from youtube_niche_mcp import __version__
from youtube_niche_mcp.analysis.historical_protocol import evidence_digest
from youtube_niche_mcp.analysis.models import AnalysisBundle, AnalysisRun
from youtube_niche_mcp.analysis.numerics import json_numbers
from youtube_niche_mcp.analysis.repository import AnalysisRepository, AnalysisUnavailable
from youtube_niche_mcp.decision.confidence import robustness
from youtube_niche_mcp.decision.evidence import collect
from youtube_niche_mcp.decision.models import VERSION, DecisionOptions
from youtube_niche_mcp.decision.sensitivity import run_plan
from youtube_niche_mcp.decision.sorting import sorting_index
from youtube_niche_mcp.decision.synthesis import assemble
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.qualitative.dimensions import production_assessment, risk_assessment
from youtube_niche_mcp.qualitative.repository import ReviewRepository
from youtube_niche_mcp.services.safety import identity


def discovery_fingerprints(history, run_ids, cutoff):
    runs = {
        r["run_id"]: r
        for r in history.connection.execute("SELECT * FROM discovery_runs")
        if r["run_id"] in run_ids
    }
    pages, occurrences = defaultdict(list), defaultdict(list)
    for table, target, ordering in (
        ("discovery_pages", pages, "page_number"),
        ("discovery_results", occurrences, "rank"),
    ):
        for r in history.connection.execute(f"SELECT * FROM {table} ORDER BY run_id,{ordering}"):
            if r["run_id"] in runs:
                target[r["run_id"]].append(r)
    return tuple(
        {
            "run_id": rid,
            "cutoff": timestamp(cutoff),
            "hash": evidence_digest(runs[rid], pages[rid], occurrences[rid], timestamp(cutoff)),
        }
        for rid in sorted(runs)
    )


def validate_run(history, run):
    """Phase 3/4/5 readers retain their behavior; only phase6 manifests enter here."""
    ReviewRepository(history).validate(run.input_ids, run.options.cutoff)
    repository = AnalysisRepository(history)
    source_ids = []
    for rid in run.input_ids:
        if history.connection.execute(
            "SELECT 1 FROM analysis_runs WHERE run_id=?", (rid,)
        ).fetchone():
            source_ids.append(rid)
    for rid in source_ids:
        repository.read(rid)  # includes preserved Phase 4 discovery fingerprint verification
    saved = run.options.frozen_discovery
    current = discovery_fingerprints(history, {p["run_id"] for p in saved}, run.options.cutoff)
    if tuple(saved) != current:
        raise AnalysisUnavailable("source_conflict", "Frozen decision discovery evidence changed")
    if isinstance(run.options, DecisionOptions):
        for p in (run.options.creator, *run.options.policy_clocks):
            if p and p.expires_at <= history.clock():
                raise AnalysisUnavailable(
                    "policy_permission_required", "Decision profile/receipt retention expired"
                )


class DecisionService:
    def __init__(self, history):
        self.history = history
        self.repository = AnalysisRepository(history)

    def inspect(self, run_id):
        bundle = self.repository.read(run_id)
        if bundle.run.formula_version != VERSION:
            raise ValueError("Decision inspect requires a Phase 6 run")
        return bundle

    def analyze(self, options: DecisionOptions, *, persist=True):
        options = DecisionOptions.model_validate(options.model_dump(mode="json"))
        now = self.history.clock()
        if options.cutoff > now:
            raise ValueError("Future decision cutoff")
        if options.creator and options.creator.expires_at <= now:
            raise AnalysisUnavailable("policy_permission_required", "Creator profile expired")
        if any(p.expires_at <= now for p in options.policy_clocks):
            raise AnalysisUnavailable(
                "policy_permission_required", "Independent policy clock receipt expired"
            )
        base = self.repository.read(options.base_run_id)
        if base.run.formula_version != "phase3-v1":
            raise ValueError("A canonical Phase 3 base run is required")
        if any(
            getattr(base.run.options, key) != getattr(options, key)
            for key in ("cutoff", "age_days", "goal", "tolerance_seconds")
        ):
            raise ValueError("Decision measurement options must match canonical base run")
        frame = self.repository.load(base.run.cohort_id, base.run.video_cohort_id, base.run.options)
        source, unavailable = [], []
        for rid in (*options.historical_run_ids, *options.qualitative_run_ids):
            try:
                b = self.repository.read(rid)
            except AnalysisUnavailable as exc:
                unavailable.append({"run_id": rid, "state": exc.state})
                continue
            expected = "phase4-v1" if rid in options.historical_run_ids else "phase5-v1"
            if (
                b.run.formula_version != expected
                or b.run.boundary != frame.boundary
                or b.run.cohort_id != base.run.cohort_id
                or b.run.video_cohort_id != base.run.video_cohort_id
            ):
                raise ValueError("Contextual run version/cohort/boundary mismatch")
            if (
                b.run.options.cutoff > options.cutoff
                or b.run.options.age_days != options.age_days
                or b.run.options.goal != options.goal
                or b.run.options.tolerance_seconds != options.tolerance_seconds
            ):
                raise ValueError("Contextual run must use known-at compatible measurement")
            source.append(b)
        metrics = {m.formula_id: m for m in base.metrics}
        for b in source:
            for m in b.metrics:
                if m.formula_id in metrics:
                    raise ValueError(
                        "Ambiguous multiple contextual metrics; select one run per dimension"
                    )
                metrics[m.formula_id] = m
        evidence = collect(self.history, frame, base, source, options)
        dependencies = set(evidence.pop("dependencies")) | {
            base.run.run_id,
            *(b.run.run_id for b in source),
        }
        annotations = evidence.pop("annotations")
        dependencies.update(a.annotation_id for a in annotations)
        route_ids = {
            r["run_id"]
            for m in (*frame.members, *(v.membership for v in frame.videos))
            for r in m.discovery_occurrences
        }
        fingerprints = discovery_fingerprints(self.history, route_ids, options.cutoff)
        if len(fingerprints) != len(route_ids):
            raise AnalysisUnavailable(
                "policy_permission_required", "Frozen discovery provenance unavailable"
            )
        options = options.model_copy(update={"frozen_discovery": fingerprints})
        expiry = ReviewRepository(self.history).validate(dependencies, options.cutoff)
        expiries = [e for e in (expiry, frame.expires_at, base.run.expires_at) if e]
        expiries.extend(p.expires_at for p in (options.creator, *options.policy_clocks) if p)
        # Retained policy snapshots can be explicit inputs outside sampled reviews.
        policies = [a for a in annotations if a.payload.kind == "policy"]
        if policies and "platform_policy" not in metrics:
            detail = risk_assessment(policies, now)["platform_policy"]
            metrics["platform_policy"] = base.metrics[0].model_copy(
                update={
                    "formula_id": "platform_policy",
                    "formula_version": "phase5-v1",
                    "state": detail["state"],
                    "value": None,
                    "details": json_numbers(detail),
                }
            )
        digest = identity(
            {
                "version": VERSION,
                "software_version": __version__,
                "frame": frame.input_hash,
                "options": options.model_dump(mode="json"),
                "source_hashes": [(b.run.run_id, b.run.input_hash) for b in (base, *source)],
                "evidence": json_numbers(evidence),
                "dependencies": sorted(dependencies),
                "unavailable": unavailable,
            },
            self.history.secrets,
        )
        rid = identity([VERSION, digest], self.history.secrets)
        if (
            persist
            and self.history.connection.execute(
                "SELECT 1 FROM analysis_runs WHERE run_id=?", (rid,)
            ).fetchone()
        ):
            return self.inspect(rid)
        generic = assemble(
            metrics,
            options.rubric,
            policy_state=evidence["policy"]["state"],
            classifications=evidence["classifications"],
        )
        comparisons, derived = run_plan(
            self.history,
            self.repository,
            base,
            frame,
            source,
            metrics,
            generic,
            evidence,
            options,
            persist,
        )
        confidence = robustness(evidence, generic, comparisons, options)
        generic["confidence"] = confidence["confidence"]
        generic["sensitivity_warnings"] = [
            r["label"]
            for r in comparisons
            if not r["comparable"] or r["material"] or not r["same_decision"]
        ]
        if generic["state"] == "supported" and (
            generic["sensitivity_warnings"] or confidence["confidence"] != "high"
        ):
            generic["state"] = "supported_with_caveats"
        # F17 and fit run after canonical generic conclusion and cannot feed back into it.
        sort = sorting_index(
            metrics, options.f17, essential_evidence_complete=not generic["insufficiency_gates"]
        )
        fit = (
            production_assessment(annotations, options.creator, None)
            if options.creator
            else {"state": "generic_assessment", "profile_id": None}
        )
        dependencies.update(derived)
        derived_expiry = (
            ReviewRepository(self.history).validate(dependencies, options.cutoff)
            if persist
            else expiry
        )
        if derived_expiry:
            expiries.append(derived_expiry)
        run = AnalysisRun(
            run_id=rid,
            formula_version=VERSION,
            formula_set=("F17", "F18", "decision"),
            cohort_id=frame.cohort_id,
            video_cohort_id=frame.video_cohort_id,
            boundary=frame.boundary,
            options=options,
            input_ids=tuple(sorted(dependencies)),
            input_hash=digest,
            software_version=__version__,
            created_at=now,
            expires_at=min(expiries) if expiries else None,
        )
        results = []
        for fid, state, value, detail in (
            ("F18", confidence["confidence"], confidence["specification_agreement"], confidence),
            ("F17", sort["state"], sort["value"], sort),
            (
                "decision",
                generic["state"],
                None,
                {
                    **generic,
                    "evidence": evidence,
                    "sensitivity": comparisons,
                    "creator_fit": fit,
                    "unavailable_source_runs": unavailable,
                    "manifest": options.model_dump(mode="json"),
                },
            ),
        ):
            results.append(
                base.metrics[0].model_copy(
                    update={
                        "formula_id": fid,
                        "formula_version": VERSION,
                        "analysis_run_id": rid,
                        "state": state,
                        "value": value,
                        "numerator": confidence["consistent_specifications"]
                        if fid == "F18"
                        else None,
                        "denominator": confidence["comparable_specifications"]
                        if fid == "F18"
                        else None,
                        "sample_unit": "predeclared_specification"
                        if fid == "F18"
                        else "research_decision",
                        "unit": "specification_agreement_fraction"
                        if fid == "F18"
                        else "sorting_index_0_100"
                        if fid == "F17"
                        else "structured_research_state",
                        "warnings": (
                            "Not success probability; no public research tools or live calls",
                        ),
                        "input_manifest_hash": digest,
                        "details": json_numbers(detail),
                    }
                )
            )
        bundle = AnalysisBundle(
            run=run,
            outcomes=base.outcomes,
            metrics=tuple(sorted(results, key=lambda m: m.formula_id)),
        )
        return self.repository.store(bundle) if persist else bundle
