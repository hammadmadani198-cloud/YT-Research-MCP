"""Offline historical bundle using the Phase 3 persistence and dependency lifecycle."""

import json
from datetime import datetime

from youtube_niche_mcp import __version__
from youtube_niche_mcp.analysis.historical_formulas import (
    catalog,
    momentum,
    panel_summary,
    post_hit,
    result,
    supply,
    supply_change,
    velocity,
    winner_change,
    winners,
)
from youtube_niche_mcp.analysis.historical_models import (
    HISTORY_FORMULAS,
    HISTORY_VERSION,
    HistoricalOptions,
)
from youtube_niche_mcp.analysis.historical_protocol import (
    comparable_protocol,
    digest,
    read_protocols,
)
from youtube_niche_mcp.analysis.history_gate import availability
from youtube_niche_mcp.analysis.models import (
    AnalysisBundle,
    AnalysisOptions,
    AnalysisRun,
    MetricResult,
)
from youtube_niche_mcp.analysis.numerics import json_numbers
from youtube_niche_mcp.analysis.outcomes import resolve
from youtube_niche_mcp.analysis.provider_history import diagnostics
from youtube_niche_mcp.analysis.repository import AnalysisRepository
from youtube_niche_mcp.domain.foundation import timestamp, valid_id
from youtube_niche_mcp.services.safety import identity


def measurement(options, *, cutoff=None, panel=None):
    return AnalysisOptions(
        cutoff=panel.cutoff if panel else cutoff or options.cutoff,
        age_days=panel.age_days if panel else options.age_days,
        tolerance_seconds=panel.tolerance_seconds if panel else options.tolerance_seconds,
        goal=panel.goal if panel else options.goal,
        low_threshold=0,
        own_minimum=1,
        peer_video_minimum=1,
        peer_channel_minimum=1,
        pooling_k=10,
        breadth_k=1,
        classification_minimum=1,
        exposure_days=90,
        first_k=options.first_k,
    )


class HistoricalService:
    def __init__(self, history):
        self.history = history
        self.repository = AnalysisRepository(history)

    def analyze(self, cohort_id, options, *, video_cohort_id=None, persist=True):
        options = HistoricalOptions.model_validate(options.model_dump(mode="json"))
        now = self.history.clock()
        definitions = {
            r["cohort_id"]: json.loads(r["definition_json"])
            for r in self.history.connection.execute("SELECT * FROM cohort_definitions")
        }
        from collections import defaultdict

        claims = defaultdict(list)
        for row in self.history.connection.execute(
            "SELECT * FROM classification_claims WHERE field='publication_at'"
        ):
            claims[row["entity_id"]].append(row)
        frames, idset, expiries = [], set(), []

        def load(cid, vcid=None, opt=None):
            f = self.repository.load(cid, vcid, opt or measurement(options))
            # Optional independently supplied chronology; expired API metadata is never rescued.
            # Annotation format is explicit and must have been known at the frozen landmark.
            videos, additional_ids = [], set()
            for v in f.videos:
                candidates = []
                for r in claims[v.video_id]:
                    if r["entity_id"] != v.video_id or r["available_at"] > timestamp(
                        f.video_freeze_at
                    ):
                        continue
                    if r["expires_at"] and r["expires_at"] <= timestamp(now):
                        continue
                    body = json.loads(r["claim_json"])
                    value = body["value"]
                    if (
                        body["data_origin"] == "independent_annotation"
                        and body["permission_state"] == "permitted"
                        and isinstance(value, dict)
                        and valid_id("channel", value.get("channel_id", ""))
                    ):
                        try:
                            pub = datetime.fromisoformat(value["publication_at"])
                        except (ValueError, KeyError, TypeError):
                            continue
                        if pub.tzinfo is not None and pub <= f.video_freeze_at:
                            candidates.append(
                                (pub, value["channel_id"], r["evidence_id"], r["expires_at"])
                            )
                identities = {(p, c) for p, c, _, _ in candidates}
                if candidates and v.publication_at is None:
                    p, c, _, _ = candidates[0]
                    v = v.model_copy(
                        update={
                            "publication_at": p,
                            "channel_id": c,
                            "identity_conflict": len(identities) > 1 or v.identity_conflict,
                        }
                    )
                    additional_ids.update(eid for _, _, eid, _ in candidates)
                    expiries.extend(e for _, _, _, e in candidates if e)
                elif candidates and identities != {(v.publication_at, v.channel_id)}:
                    v = v.model_copy(update={"identity_conflict": True})
                    additional_ids.update(eid for _, _, eid, _ in candidates)
                if v.publication_at and v.publication_at > f.video_freeze_at:
                    v = v.model_copy(update={"identity_conflict": True})
                videos.append(v)
            f = f.model_copy(
                update={
                    "videos": tuple(videos),
                    "input_ids": tuple(sorted(set(f.input_ids) | additional_ids)),
                    "input_hash": identity(
                        [
                            f.input_hash,
                            [v.model_dump(mode="json") for v in videos],
                            sorted(additional_ids),
                        ],
                        self.history.secrets,
                    ),
                }
            )
            idset.update(f.input_ids)
            if f.expires_at:
                expiries.append(timestamp(f.expires_at))
            frames.append(f)
            return f

        frame = load(cohort_id, video_cohort_id)
        outcomes = tuple(
            sorted(
                (resolve(v, measurement(options), now) for v in frame.videos),
                key=lambda o: o.video_id,
            )
        )
        panels, panel_outcomes, summaries = [], [], []
        for p in (options.older, options.newer):
            f = load(p.cohort_id, p.video_cohort_id, measurement(options, panel=p)) if p else None
            oo = (
                tuple(resolve(v, measurement(options, panel=p), now) for v in f.videos) if f else ()
            )
            panels.append(f)
            panel_outcomes.append(oo)
            summaries.append(panel_summary(f, oo, p) if f else None)
        protocols = read_protocols(
            self.history.connection, (options.older, options.newer), now, definitions
        )
        frozen_discovery = [item for pr in protocols if pr for item in pr["evidence_manifests"]]
        options = options.model_copy(
            update={"annotation": {**options.annotation, "frozen_discovery": frozen_discovery}}
        )
        for p in protocols:
            if p:
                idset.update(p["input_ids"])
                expiries.extend(p["expiries"])

        def signature(f, p):
            d = definitions[f.video_cohort_id]
            return {
                "boundary": d["boundary"],
                "rules": {
                    k: d[k]
                    for k in (
                        "long_form_rule",
                        "format_rule",
                        "live_rule",
                        "language_rule",
                        "faceless_rule",
                        "allow_archived_live",
                        "include_uncertain",
                    )
                },
                "age": p.age_days,
                "tolerance": p.tolerance_seconds,
                "group_version": p.creator_group_version,
            }

        comparable = bool(all(panels)) and signature(panels[0], options.older) == signature(
            panels[1], options.newer
        )

        def frame_rules(f):
            d = definitions[f.video_cohort_id]
            return {
                k: d[k]
                for k in (
                    "boundary",
                    "long_form_rule",
                    "format_rule",
                    "live_rule",
                    "language_rule",
                    "faceless_rule",
                    "allow_archived_live",
                    "include_uncertain",
                )
            }

        def outcome_definitions(f, oo):
            selected_ids = {o.observation_id for o in oo if o.state == "available"}
            return {
                s.metric_definition
                for v in f.videos
                for s in v.snapshots
                if s.observation_id in selected_ids
            }

        panel_ids = [
            digest(
                {
                    "signature": signature(f, p),
                    "window": p.publication.model_dump(mode="json"),
                    "protocol": pr["hash"] if pr else None,
                    "version": HISTORY_VERSION,
                }
            )
            if f
            else None
            for f, p, pr in zip(panels, (options.older, options.newer), protocols, strict=True)
        ]
        data = {}
        if options.observation_window:
            provider_records, provider_ids, provider_expiries = (
                diagnostics(
                    self.history.connection,
                    {v.video_id for v in frame.videos}
                    | {v.channel_id for v in frame.videos}
                    | {m.subject.entity_id for m in frame.members},
                    options.cutoff,
                    now,
                    options.observation_window,
                )
                if options.provider_history_policy == "separate_auxiliary"
                else ([], set(), [])
            )
            idset.update(provider_ids)
            expiries.extend(provider_expiries)
            own = [
                velocity(v, options.cutoff, now, options.observation_window) for v in frame.videos
            ]
            auxiliary = (
                [
                    velocity(v, options.cutoff, now, options.observation_window, provider=True)
                    for v in frame.videos
                ]
                if options.provider_history_policy == "separate_auxiliary"
                else []
            )
            state = availability(
                [r["state"] for r in own],
                provider_only=any(r["state"] == "available" for r in provider_records)
                or any(
                    velocity(v, options.cutoff, now, options.observation_window, provider=True)[
                        "state"
                    ]
                    == "available"
                    for v in frame.videos
                ),
            )
            data["F10"] = result(
                state,
                own_history=own,
                provider_history=auxiliary + provider_records,
                quantity="views",
                rate_unit="views/hour",
                acceleration_unit="views/hour",
            )
        else:
            data["F10"] = result(reason="Explicit observation interval required")
        data["F11"] = momentum(*summaries) if comparable else result("insufficient_panel_history")
        protocol_state = comparable_protocol(*protocols)
        if not comparable or (
            options.older
            and options.newer
            and options.older.publication.seconds != options.newer.publication.seconds
        ):
            protocol_state = "insufficient_panel_history"
        supply_summaries = [
            supply(f, p, pr) if f and pr else None
            for f, p, pr in zip(panels, (options.older, options.newer), protocols, strict=True)
        ]
        data["F12"] = supply_change(*supply_summaries, protocol_state)
        initial = (
            load(
                options.catalog_start_cohort,
                opt=measurement(options, cutoff=options.catalog_window.start),
            )
            if options.catalog_window
            else None
        )
        if initial and frame_rules(initial) != frame_rules(frame):
            data["F13"] = result("insufficient_panel_history")
        else:
            data["F13"] = catalog(initial, frame, options, now)
        pre = (
            load(options.pre_anchor_cohort, opt=measurement(options, cutoff=options.anchor_at))
            if options.anchor_at
            else None
        )
        pre_outcomes = (
            tuple(
                resolve(v, measurement(options, cutoff=options.anchor_at), now) for v in pre.videos
            )
            if pre
            else ()
        )
        if (
            pre
            and frame_rules(pre) != frame_rules(frame)
            or (
                pre
                and pre_outcomes
                and any(o.state == "available" for o in outcomes)
                and (outcome_definitions(pre, pre_outcomes) != outcome_definitions(frame, outcomes))
            )
        ):
            data["F20"] = result("insufficient_panel_history")
        else:
            data["F20"] = post_hit(pre, frame, pre_outcomes, outcomes, options)
        winner_sets = [
            winners(f, oo, p, options.recent_entry) if f else None
            for f, oo, p in zip(panels, panel_outcomes, (options.older, options.newer), strict=True)
        ]
        if (
            options.older
            and options.newer
            and options.older.goal != options.newer.goal
            or summaries[0]
            and summaries[1]
            and summaries[0]["measurement_definitions"] != summaries[1]["measurement_definitions"]
        ):
            data["F21"] = result("insufficient_panel_history")
        else:
            data["F21"] = winner_change(*winner_sets, protocol_state)
        self.repository.validate_dependencies(tuple(idset))
        input_hash = identity(
            {
                "frames": [f.input_hash for f in frames],
                "protocols": [
                    json_numbers({k: sorted(v) if isinstance(v, set) else v for k, v in pr.items()})
                    if pr
                    else None
                    for pr in protocols
                ],
                "ids": sorted(idset),
            },
            self.history.secrets,
        )
        run_id = identity(
            {
                "version": HISTORY_VERSION,
                "software": __version__,
                "inputs": input_hash,
                "options": options.model_dump(mode="json"),
            },
            self.history.secrets,
        )
        run = AnalysisRun(
            run_id=run_id,
            formula_version=HISTORY_VERSION,
            formula_set=HISTORY_FORMULAS,
            cohort_id=cohort_id,
            video_cohort_id=frame.video_cohort_id,
            boundary=frame.boundary,
            options=options,
            input_ids=tuple(sorted(idset)),
            input_hash=input_hash,
            software_version=__version__,
            created_at=now,
            expires_at=min(expiries) if expiries else None,
        )
        known = sum(o.state == "available" for o in outcomes)
        pending = sum(o.state == "pending_maturity" for o in outcomes)
        excluded = sum(o.state == "excluded_format" for o in outcomes)
        metrics = []
        for fid, r in sorted(data.items()):
            metrics.append(
                MetricResult(
                    formula_id=fid,
                    formula_version=HISTORY_VERSION,
                    analysis_run_id=run_id,
                    cohort_id=cohort_id,
                    boundary=frame.boundary,
                    cutoff=options.cutoff,
                    age_days=options.age_days,
                    tolerance_seconds=options.tolerance_seconds,
                    goal=options.goal,
                    sample_unit="historical_panel" if fid != "F10" else "video_interval",
                    included=len(outcomes) - excluded,
                    mature=known,
                    pending=pending,
                    unknown=len(outcomes) - excluded - known - pending,
                    excluded=excluded,
                    independent_units=len(
                        {
                            m.independence_unit
                            for m in frame.members
                            if m.independence_state == "documented_group"
                        }
                    ),
                    unresolved_ownership_channels=len(
                        {
                            v.channel_id
                            for v in frame.videos
                            if v.membership.independence_state == "unknown"
                        }
                    ),
                    value=r["value"],
                    numerator=r["numerator"],
                    denominator=r["denominator"],
                    unit={
                        "F10": "views/hour",
                        "F11": "times",
                        "F12": "relative_change",
                        "F13": "fraction",
                        "F20": "times",
                        "F21": "separate_fractions",
                    }[fid],
                    state=r["state"],
                    warnings=(
                        "Descriptive selected frame; no forecasting or causal identification",
                        "Sparse samples and unknown ownership do not establish confidence",
                    ),
                    input_manifest_hash=input_hash,
                    details=json_numbers(
                        {
                            **r["details"],
                            "panel_ids": panel_ids,
                            "discovery_protocol_ids": [p["hash"] if p else None for p in protocols],
                        }
                    ),
                )
            )
        bundle = AnalysisBundle(run=run, outcomes=outcomes, metrics=tuple(metrics))
        return self.repository.store(bundle) if persist else bundle

    def inspect(self, run_id):
        return self.repository.read(run_id)
