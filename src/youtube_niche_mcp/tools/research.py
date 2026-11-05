"""Stored-evidence orchestration. No tool-specific metric equations."""

import json
from hashlib import sha256

from youtube_niche_mcp.analysis.historical_models import HistoricalOptions
from youtube_niche_mcp.analysis.historical_service import HistoricalService
from youtube_niche_mcp.analysis.repository import AnalysisRepository
from youtube_niche_mcp.analysis.service import AnalysisService
from youtube_niche_mcp.decision.models import DecisionOptions, SensitivityPlan
from youtube_niche_mcp.decision.service import DecisionService
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.cohorts import CohortBuilder
from youtube_niche_mcp.eligibility.models import Candidate, CohortDefinition, Subject
from youtube_niche_mcp.eligibility.repository import EligibilityRepository
from youtube_niche_mcp.qualitative.models import QualitativeOptions
from youtube_niche_mcp.qualitative.service import QualitativeService
from youtube_niche_mcp.services.safety import identity
from youtube_niche_mcp.tools.errors import PublicError

BUDGETS = {
    "quick": {
        "channels": [15, 25],
        "videos": [100, 250],
        "search_pages": 2,
        "review": 25,
        "sensitivity": 8,
        "similarity_depth": 1,
    },
    "standard": {
        "channels": [30, 50],
        "videos": [300, 800],
        "search_pages": 6,
        "review": 100,
        "sensitivity": 24,
        "similarity_depth": 1,
    },
    "deep": {
        "channels": [60, 100],
        "videos": [1000, 3000],
        "search_pages": 20,
        "review": 500,
        "sensitivity": 48,
        "similarity_depth": 2,
    },
}


class ResearchEngine:
    def __init__(self, history):
        self.history, self.c = history, history.connection
        self.repository = AnalysisRepository(history)
        self.decisions = DecisionService(history)
        self.eligibility = EligibilityRepository(history)
        self._contexts = {}

    def boundaries(self):
        now = timestamp(self.history.clock())
        rows = self.c.execute(
            "SELECT definition_json FROM cohort_definitions WHERE known_at<=? AND created_at<=? "
            "AND (expires_at IS NULL OR expires_at>?) ORDER BY cohort_id LIMIT 1001",
            (now, now, now),
        ).fetchall()
        if len(rows) > 1000:
            raise PublicError("budget_exceeded")
        result = {}
        for row in rows:
            d = CohortDefinition.model_validate_json(row[0])
            if d.boundary.boundary_id in result and result[d.boundary.boundary_id] != d.boundary:
                raise PublicError("source_conflict")
            result[d.boundary.boundary_id] = d.boundary
        return result

    def boundary_id(self, request):
        if request.boundary_id:
            return request.boundary_id
        if request.advanced and request.advanced.channel_frame:
            return request.advanced.channel_frame.boundary.boundary_id
        rows = self.c.execute(
            "SELECT node_id,taxonomy_version,label FROM taxonomy_nodes WHERE available_at<=? "
            "AND instr(lower(label),lower(?))>0 ORDER BY taxonomy_version,node_id LIMIT 101",
            (timestamp(self.history.clock()), request.query or ""),
        ).fetchall()
        if len(rows) > 100:
            raise PublicError("budget_exceeded")
        nodes = {(r[0], r[1]) for r in rows}
        choices = [
            bid
            for bid, b in self.boundaries().items()
            if any((nid, b.taxonomy_version) in nodes for nid in b.node_ids)
        ]
        if len(choices) != 1:
            raise PublicError("insufficient_evidence")
        return choices[0]

    def resolve(self, boundary_id, versions=("phase6-v1", "phase3-v1"), mode=None):
        now = timestamp(self.history.clock())
        rows = self.c.execute(
            "SELECT run_id,formula_version,manifest_json FROM analysis_runs "
            "WHERE created_at<=? AND (expires_at IS NULL OR expires_at>?) "
            "ORDER BY created_at DESC,run_id DESC LIMIT 1001",
            (now, now),
        ).fetchall()
        if len(rows) > 1000:
            raise PublicError("budget_exceeded")
        for version in versions:
            for r in rows:
                manifest = json.loads(r[2])
                if r[1] != version or manifest["boundary"]["boundary_id"] != boundary_id:
                    continue
                if (
                    version == "phase6-v1"
                    and manifest["options"].get("decision_version") != "phase6-v1"
                ):
                    continue
                # Generic boundary/query lookup must not inherit another retained capacity profile.
                # Explicit run IDs remain usable within the trusted local research context.
                if version == "phase6-v1" and manifest["options"].get("creator") is not None:
                    continue
                if (
                    mode
                    and version == "phase6-v1"
                    and manifest["options"]["sensitivity"]["mode"] != mode
                ):
                    continue
                return self.repository.read(r[0])
        raise PublicError("insufficient_evidence")

    def context(self, research_id):
        if research_id in self._contexts:
            return self._contexts[research_id]
        decision = self.decisions.inspect(research_id)
        if not isinstance(decision.run.options, DecisionOptions):
            raise PublicError("invalid_input")
        bundles = [self.repository.read(rid) for rid in decision.run.options.analysis_run_ids]
        metrics = {m.formula_id: m for b in bundles for m in b.metrics}
        metrics.update({m.formula_id: m for m in decision.metrics})
        base = next(b for b in bundles if b.run.formula_version == "phase3-v1")
        frame = self.repository.load(base.run.cohort_id, base.run.video_cohort_id, base.run.options)
        self._contexts[research_id] = (decision, base, metrics, frame)
        return self._contexts[research_id]

    def freeze(self, profile, mode):
        """Select retained candidates without consulting their performance, then freeze."""
        cd, vd, options = profile.channel_frame, profile.video_frame, profile.measurement
        if cd.created_at > options.cutoff or vd.created_at > options.cutoff:
            raise PublicError("invalid_input")
        builder = CohortBuilder(self.eligibility)
        nodes = builder.nodes(vd)
        at, now = timestamp(vd.known_at), timestamp(self.history.clock())
        rows = self.c.execute(
            "SELECT entity_kind,entity_id,node_id,taxonomy_version FROM niche_memberships "
            "WHERE available_at<=? AND decided_at<=? AND (expires_at IS NULL OR expires_at>?) "
            "ORDER BY entity_kind,entity_id LIMIT 20001",
            (at, at, now),
        ).fetchall()
        if len(rows) > 20000:
            raise PublicError("budget_exceeded")
        candidates = {
            (r[0], r[1]) for r in rows if r[2] in nodes and r[3] == vd.boundary.taxonomy_version
        }
        videos = self.c.execute(
            "WITH ranked AS (SELECT o.video_id,o.metadata_json,ROW_NUMBER() OVER "
            "(PARTITION BY o.video_id ORDER BY o.observed_at "
            "DESC,o.available_at DESC,o.observation_id) n "
            "FROM video_observations o JOIN source_records s USING(source_id) "
            "WHERE o.observed_at<=? AND o.available_at<=? AND s.expires_at>?) "
            "SELECT video_id,metadata_json FROM ranked WHERE n=1 ORDER BY video_id LIMIT 20001",
            (at, at, now),
        ).fetchall()
        if len(videos) > 20000:
            raise PublicError("budget_exceeded")
        mapping = {
            r[0]: json.loads(r[1]).get("channel_id")
            for r in videos
            if ("video", r[0]) in candidates
        }
        channels = {cid for cid in mapping.values() if cid} | {
            sid for kind, sid in candidates if kind == "channel"
        }

        def order(sid):
            return (sha256(f"phase7:{vd.boundary.boundary_id}:{sid}".encode()).hexdigest(), sid)

        cap = BUDGETS[mode]
        selected_channels = sorted(channels, key=order)[: cap["channels"][1]]
        selected_videos = sorted(
            (vid for vid, cid in mapping.items() if cid in selected_channels), key=order
        )[: cap["videos"][1]]
        if not selected_channels or not selected_videos:
            raise PublicError("insufficient_evidence")
        # A frame is immutable and mode-specific, including its sampling manifest identity.
        seed = identity(
            [
                cd.model_dump(mode="json"),
                vd.model_dump(mode="json"),
                mode,
                selected_channels,
                selected_videos,
            ]
        )
        cd = cd.model_copy(update={"cohort_id": "public-channels-" + seed[:24]})
        vd = vd.model_copy(update={"cohort_id": "public-videos-" + seed[:24]})
        for vid in selected_videos:
            for rule in (
                vd.long_form_rule,
                vd.format_rule,
                vd.live_rule,
                vd.language_rule,
                vd.faceless_rule,
            ):
                if not self.eligibility.latest(
                    Subject(entity_kind="video", entity_id=vid), rule, vd.known_at
                ):
                    self.eligibility.evaluate(
                        Subject(entity_kind="video", entity_id=vid), rule, at=vd.known_at
                    )
        for cid in selected_channels:
            if not self.eligibility.latest(
                Subject(entity_kind="channel", entity_id=cid), cd.small_rule, cd.known_at
            ):
                self.eligibility.evaluate(
                    Subject(entity_kind="channel", entity_id=cid), cd.small_rule, at=cd.known_at
                )
        builder.freeze(
            vd,
            tuple(
                Candidate(subject=Subject(entity_kind="video", entity_id=v))
                for v in selected_videos
            ),
        )
        builder.freeze(
            cd,
            tuple(
                Candidate(
                    subject=Subject(entity_kind="channel", entity_id=v),
                    entry_known_at=cd.known_at if cd.kind == "entrant" else None,
                )
                for v in selected_channels
            ),
        )
        return AnalysisService(self.history).analyze(
            cd.cohort_id, options, video_cohort_id=vd.cohort_id
        )

    def research(self, request):
        profile = request.advanced
        source = self.repository.read(request.research_id) if request.research_id else None
        if (
            source
            and request.boundary_id
            and source.run.boundary.boundary_id != request.boundary_id
        ):
            raise PublicError("invalid_input")
        mode = request.mode or (
            source.run.options.sensitivity.mode
            if source and source.run.formula_version == "phase6-v1"
            else "standard"
        )
        if source is None and not (profile and profile.channel_frame):
            source = self.resolve(self.boundary_id(request), mode=request.mode)
            if request.mode is None and source.run.formula_version == "phase6-v1":
                mode = source.run.options.sensitivity.mode
        previous = source if source and source.run.formula_version == "phase6-v1" else None
        if previous and not isinstance(previous.run.options, DecisionOptions):
            raise PublicError("invalid_input")
        changes = (
            profile is not None
            or request.creator_profile is not None
            or request.sorting is not None
            or request.history_preference == "exclude"
        )
        if previous and not changes:
            if mode != previous.run.options.sensitivity.mode:
                raise PublicError("incompatible_runs")
            self.check_budget(previous.run.run_id, mode)
            return previous, True
        rubric = (
            profile.rubric
            if profile and profile.rubric
            else previous.run.options.rubric
            if previous
            else None
        )
        if rubric is None:
            raise PublicError("insufficient_evidence")
        creator = request.creator_profile or (previous.run.options.creator if previous else None)
        if profile and profile.channel_frame:
            base = self.freeze(profile, mode)
        elif previous:
            base = self.repository.read(previous.run.options.base_run_id)
        elif source and source.run.formula_version == "phase3-v1":
            base = source
        else:
            raise PublicError("insufficient_evidence")
        if profile and profile.measurement and not profile.channel_frame:
            base = AnalysisService(self.history).analyze(
                base.run.cohort_id, profile.measurement, video_cohort_id=base.run.video_cohort_id
            )
        measure = {
            k: getattr(base.run.options, k)
            for k in ("cutoff", "age_days", "goal", "tolerance_seconds")
        }
        frame = self.repository.load(base.run.cohort_id, base.run.video_cohort_id, base.run.options)
        cap = BUDGETS[mode]
        if len(frame.members) > cap["channels"][1] or len(frame.videos) > cap["videos"][1]:
            raise PublicError("budget_exceeded")
        historical_ids, qualitative_ids = [], []
        if (
            previous
            and all(getattr(previous.run.options, k) == v for k, v in measure.items())
            and not (profile and profile.channel_frame)
        ):
            historical_ids = list(previous.run.options.historical_run_ids)
            qualitative_ids = list(previous.run.options.qualitative_run_ids)
        if request.history_preference == "exclude":
            historical_ids = []
        elif (profile and profile.historical) or not historical_ids:
            historical = (
                profile.historical
                if profile and profile.historical
                else HistoricalOptions(
                    **measure, creator_group_version="stored_disclosed_groups_v1"
                )
            )
            h = HistoricalService(self.history).analyze(
                base.run.cohort_id, historical, video_cohort_id=base.run.video_cohort_id
            )
            historical_ids = [h.run.run_id]
        if (profile and profile.review) or not qualitative_ids or request.creator_profile:
            review = profile.review if profile else None
            retained_review = (
                self.repository.read(qualitative_ids[0]).run.options if qualitative_ids else None
            )
            ids = (
                review.review_ids
                if review
                else retained_review.annotation_ids
                if retained_review
                else ()
            )
            premises = (
                review.premise_ids
                if review
                else retained_review.generated_candidate_ids
                if retained_review
                else ()
            )
            q = QualitativeService(self.history).analyze(
                base.run.cohort_id,
                QualitativeOptions(
                    **measure,
                    annotation_ids=ids,
                    generated_candidate_ids=premises,
                    review_budget=cap["review"],
                    seed=f"phase7-{mode}",
                    analysis_run_ids=(base.run.run_id, *historical_ids),
                    creator=creator,
                    pilot=review.pilot
                    if review
                    else retained_review.pilot
                    if retained_review
                    else None,
                    production_case_id=review.production_case_id
                    if review
                    else retained_review.production_case_id
                    if retained_review
                    else None,
                ),
                video_cohort_id=base.run.video_cohort_id,
            )
            qualitative_ids = [q.run.run_id]
        sensitivity = (
            profile.sensitivity
            if profile and profile.sensitivity
            else SensitivityPlan(
                mode=mode, declared_at=base.run.options.cutoff, max_runs=cap["sensitivity"]
            )
        )
        if sensitivity.mode != mode or sensitivity.max_runs > cap["sensitivity"]:
            raise PublicError("incompatible_runs")
        options = DecisionOptions(
            **measure,
            base_run_id=base.run.run_id,
            historical_run_ids=tuple(historical_ids),
            qualitative_run_ids=tuple(qualitative_ids),
            rubric=rubric,
            sensitivity=sensitivity,
            creator=creator,
            f17=request.sorting,
            policy_snapshot_ids=previous.run.options.policy_snapshot_ids if previous else (),
            policy_clocks=previous.run.options.policy_clocks if previous else (),
        )
        existing = {
            r[0]
            for r in self.c.execute(
                "SELECT run_id FROM analysis_runs WHERE formula_version='phase6-v1'"
            )
        }
        decision = self.decisions.analyze(options)
        return decision, decision.run.run_id in existing

    def check_budget(self, research_id, mode):
        _, _, _, frame = self.context(research_id)
        if (
            len(frame.members) > BUDGETS[mode]["channels"][1]
            or len(frame.videos) > BUDGETS[mode]["videos"][1]
        ):
            raise PublicError("budget_exceeded")
