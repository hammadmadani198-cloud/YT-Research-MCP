"""Source equations on already frozen evidence; descriptive, never predictive."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from youtube_niche_mcp.analysis.history_gate import availability, series
from youtube_niche_mcp.analysis.numerics import quantile, ratio


def result(state="insufficient_history", value=None, numerator=None, denominator=None, **details):
    return dict(
        state=state, value=value, numerator=numerator, denominator=denominator, details=details
    )


def velocity(video, cutoff, now, window, *, provider=False):
    points, state = series(video, cutoff, now, window, provider=provider)
    intervals, flags = [], []
    for left, right in zip(points, points[1:], strict=False):
        seconds = Decimal(str((right.observed_at - left.observed_at).total_seconds()))
        delta = right.value - left.value
        rate = ratio(delta * 3600, seconds)
        intervals.append(
            {
                "observation_ids": [left.observation_id, right.observation_id],
                "timestamps": [left.observed_at.isoformat(), right.observed_at.isoformat()],
                "available_at": [left.available_at.isoformat(), right.available_at.isoformat()],
                "ages_seconds": [
                    str((s.observed_at - video.publication_at).total_seconds())
                    for s in (left, right)
                ],
                "values": [left.value, right.value],
                "elapsed_seconds": seconds,
                "delta": delta,
                "rate": rate,
                "quantity": "views",
                "unit": "views/hour",
            }
        )
        if delta < 0:
            flags.append("negative_delta")
        if provider and seconds != 86400:
            flags.append("irregular_or_missing_dates")
    if provider:
        if any(
            points[i].value < points[i - 1].value and points[i + 1].value > points[i].value
            for i in range(1, len(points) - 1)
        ):
            flags.append("rebound")
        if any(s.value == 0 for s in points):
            flags.append("zero_count")
        if points and cutoff - points[-1].observed_at > timedelta(days=1):
            flags.append("stale_timestamps")
    changes = [
        {
            "first_rate": a["rate"],
            "second_rate": b["rate"],
            "change_in_velocity": b["rate"] - a["rate"],
            "durations_seconds": [a["elapsed_seconds"], b["elapsed_seconds"]],
            "unit": "views/hour",
        }
        for a, b in zip(intervals, intervals[1:], strict=False)
    ]
    return result(
        state,
        intervals[-1]["rate"] if intervals else None,
        intervals[-1]["delta"] if intervals else None,
        ratio(intervals[-1]["elapsed_seconds"], 3600) if intervals else None,
        video_id=video.video_id,
        history_class="PROVIDER_HISTORY" if provider else "OWN_HISTORY",
        observations=len(points),
        intervals=intervals,
        acceleration=changes,
        acceleration_state="available" if changes else "insufficient_history",
        flags=sorted(set(flags)),
    )


def panel_summary(frame, outcomes, panel):
    by_id = {v.video_id: v for v in frame.videos}
    selected = [
        o
        for o in outcomes
        if o.publication_at is None
        or panel.publication.start <= o.publication_at < panel.publication.end
    ]
    selected = [o for o in selected if o.state not in {"excluded_format", "outside_cohort"}]
    known = [o for o in selected if o.state == "available" and o.channel_id]
    channels = defaultdict(list)
    for o in known:
        channels[o.channel_id].append(o.value)
    medians = {c: quantile(v) for c, v in sorted(channels.items())}
    unit_ids = {
        by_id[o.video_id].membership.independence_unit
        for o in known
        if by_id[o.video_id].membership.independence_state == "documented_group"
    }
    definitions = {
        s.metric_definition
        for o in known
        for s in by_id[o.video_id].snapshots
        if s.observation_id == o.observation_id
    }
    return {
        "aggregate": quantile(medians.values()),
        "channel_medians": medians,
        "video_weighted_median": quantile(o.value for o in known),
        "videos": len(selected),
        "mature": len(known),
        "channels": len(channels),
        "independent_units": len(unit_ids),
        "pending": sum(o.state == "pending_maturity" for o in selected),
        "unknown": sum(o.state not in {"available", "pending_maturity"} for o in selected),
        "classification_coverage": ratio(
            sum(by_id[o.video_id].membership.state.value == "included" for o in selected),
            len(selected),
        ),
        "measurement_definitions": sorted(definitions),
        "state": availability([o.state for o in selected], missing="insufficient_same_age_history"),
    }


def momentum(old, new):
    if not old or not new:
        return result("insufficient_same_age_history")
    a, b = old["aggregate"], new["aggregate"]
    state = availability([old["state"], new["state"]], missing="insufficient_same_age_history")
    if a is None or b is None:
        return result("insufficient_same_age_history", older=old, newer=new)
    if old["measurement_definitions"] != new["measurement_definitions"]:
        return result("insufficient_panel_history", older=old, newer=new)
    r = ratio(b, a)
    shared = set(old["channel_medians"]) & set(new["channel_medians"])
    matched_a = quantile(old["channel_medians"][c] for c in shared)
    matched_b = quantile(new["channel_medians"][c] for c in shared)
    return result(
        state,
        r,
        b,
        a,
        older=old,
        newer=new,
        absolute_change=b - a,
        relative_change=r - 1 if r is not None else None,
        matched_channels=sorted(shared),
        matched_ratio=ratio(matched_b, matched_a) if matched_a is not None else None,
    )


def entry_bucket(members, window):
    if not window:
        return "unknown"
    entries = []
    for m in members:
        at = m.entry_status.get("first_observed_niche_entry")
        if not at or m.state.value not in {"included", "included_with_uncertainty"}:
            return "unknown"
        try:
            entries.append(datetime.fromisoformat(at))
        except (ValueError, TypeError):
            return "unknown"
    if not entries or any(t.tzinfo is None for t in entries):
        return "unknown"
    first = min(entries)
    return (
        "verified_entrant"
        if window.start <= first < window.end
        else ("incumbent" if first < window.start else "unknown")
    )


def supply(frame, panel, protocol):
    selected = [
        v
        for v in frame.videos
        if v.video_id in protocol["found"]
        and v.publication_at
        and panel.publication.start <= v.publication_at < panel.publication.end
        and v.membership.state.value == "included"
        and v.channel_id
        and not v.identity_conflict
    ]
    counts = Counter(v.channel_id for v in selected)
    cm = {m.subject.entity_id: m for m in frame.members if m.subject.entity_kind == "channel"}
    entrants = [
        c
        for c in counts
        if c in cm and entry_bucket([cm[c]], panel.publication) == "verified_entrant"
    ]
    unresolved = [
        v.video_id
        for v in frame.videos
        if v.video_id in protocol["found"]
        and (v.publication_at is None or v.membership.state.value not in {"included", "excluded"})
    ]
    return {
        "eligible_videos": len(selected),
        "active_channels": len(counts),
        "verified_entrants": len(entrants),
        "entrant_ids": sorted(entrants),
        "unknown_entry_channels": sum(
            c not in cm or entry_bucket([cm[c]], panel.publication) == "unknown" for c in counts
        ),
        "per_channel_uploads_per_day": {
            c: ratio(n * 86400, Decimal(str(panel.publication.seconds)))
            for c, n in sorted(counts.items())
        },
        "video_ids": sorted(v.video_id for v in selected),
        "unresolved_video_ids": unresolved,
    }


def supply_change(old, new, state):
    if state not in {"available", "partial_coverage"}:
        return result(state)
    changes = {
        name: {
            "older": old[name],
            "newer": new[name],
            "delta": new[name] - old[name],
            "relative_change": ratio(new[name] - old[name], old[name]),
        }
        for name in ("eligible_videos", "active_channels", "verified_entrants")
    }
    c = changes["active_channels"]
    if old["unresolved_video_ids"] or new["unresolved_video_ids"]:
        state = "partial_coverage"
    return result(
        state,
        c["relative_change"],
        c["delta"],
        c["older"],
        older=old,
        newer=new,
        changes=changes,
        census=False,
    )


def catalog(start_frame, end_frame, options, now):
    window = options.catalog_window
    if not window or not start_frame:
        return result()
    initial = {v.video_id: v for v in start_frame.videos if v.membership.state.value != "excluded"}
    final = {v.video_id: v for v in end_frame.videos}
    scoped = dict(initial)
    scoped.update(
        {
            v.video_id: v
            for v in end_frame.videos
            if v.publication_at
            and window.start < v.publication_at <= window.end
            and v.membership.state.value != "excluded"
        }
    )
    sums = Counter(old=0, preexisting_younger=0, new_release=0)
    rows, states, partial = [], [], False
    for vid, v in sorted(scoped.items()):
        old = vid in initial
        current = final.get(vid)
        # Use start-frame identity/classification for pre-existing catalog; later valid counts only.
        if old and current:
            v = v.model_copy(
                update={"snapshots": current.snapshots, "policy_blocked": current.policy_blocked}
            )
        points, state = series(v, options.cutoff, now, window)
        left = (
            next((s for s in points if s.observed_at == window.start), None)
            if old
            else (points[0] if points else None)
        )
        right = next((s for s in points if s.observed_at == window.end), None)
        bucket = (
            "old"
            if old
            and v.publication_at
            and v.publication_at <= window.start - timedelta(days=options.old_age_days)
            else ("preexisting_younger" if old else "new_release")
        )
        if not left or not right or left.observed_at >= right.observed_at:
            state = state if state != "available" else "insufficient_history"
            states.append(state)
            rows.append({"video_id": vid, "bucket": bucket, "state": state})
            continue
        delta = right.value - left.value
        state = "available" if delta >= 0 else "source_conflict"
        states.append(state)
        partial |= not old and left.observed_at > window.start
        sums[bucket] += delta
        rows.append(
            {
                "video_id": vid,
                "channel_id": v.channel_id,
                "bucket": bucket,
                "state": state,
                "observation_ids": [left.observation_id, right.observation_id],
                "timestamps": [left.observed_at.isoformat(), right.observed_at.isoformat()],
                "values": [left.value, right.value],
                "delta": delta,
            }
        )
    state = availability(states)
    if partial and state == "available":
        state = "partial_coverage"
    total = sum(sums.values())
    share = ratio(sums["old"], total) if state in {"available", "partial_coverage"} else None
    return result(
        state,
        share,
        sums["old"],
        total,
        increments=dict(sums),
        shares={k: ratio(v, total) if share is not None else None for k, v in sums.items()},
        bucket_video_counts=dict(Counter(r["bucket"] for r in rows)),
        channels=len({r.get("channel_id") for r in rows if r.get("channel_id")}),
        missing_intervals=sum(s != "available" for s in states),
        observed_intervals=sum(s == "available" for s in states),
        observation_coverage=ratio(sum(s == "available" for s in states), len(states)),
        new_release_exposure_partial=partial,
        interval=window.model_dump(mode="json"),
        old_age_days=options.old_age_days,
        videos=rows,
    )


def post_hit(pre_frame, post_frame, pre_outcomes, post_outcomes, options):
    if not pre_frame or not options.anchor_at:
        return result()
    known_hits = [
        o
        for o in pre_outcomes
        if o.state == "available"
        and o.value >= options.goal
        and (not options.anchor_channel_id or o.channel_id == options.anchor_channel_id)
    ]
    anchor = (
        next((o for o in known_hits if o.video_id == options.anchor_id), None)
        if options.anchor_id
        else (min(known_hits, key=lambda o: (o.available_at, o.video_id)) if known_hits else None)
    )
    if not anchor:
        return result(reason="No verified known age-matched anchor at landmark")
    pre = sorted(
        [
            o
            for o in pre_outcomes
            if o.channel_id == anchor.channel_id
            and o.video_id != anchor.video_id
            and o.publication_at
            and o.publication_at < anchor.publication_at
            and o.state == "available"
            and o.available_at <= options.anchor_at
        ],
        key=lambda o: (o.publication_at, o.video_id),
    )[-options.first_k :]
    post = sorted(
        [
            o
            for o in post_outcomes
            if o.channel_id == anchor.channel_id
            and o.video_id != anchor.video_id
            and o.publication_at
            and o.publication_at > options.anchor_at
            and o.state != "excluded_format"
        ],
        key=lambda o: (o.publication_at, o.video_id),
    )[: options.first_k]
    unknown_positions = sum(
        o.channel_id in {anchor.channel_id, None} and o.publication_at is None
        for o in post_outcomes
    )
    prevalues = [o.value for o in pre]
    postvalues = [o.value for o in post if o.state == "available"]
    a, b = quantile(prevalues), quantile(postvalues)
    detail = {
        "anchor_id": anchor.video_id,
        "anchor_available_at": anchor.available_at.isoformat(),
        "anchor_selection": "explicit_verified" if options.anchor_id else "first_known_goal_hit",
        "landmark": options.anchor_at.isoformat(),
        "pre_median": a,
        "post_median": b,
        "pre_count": len(prevalues),
        "post_count": len(postvalues),
        "first_k": options.first_k,
        "pending": sum(o.state == "pending_maturity" for o in post),
        "unknown": sum(o.state not in {"available", "pending_maturity"} for o in post),
        "unknown_positions": unknown_positions,
        "not_yet_observed_uploads": options.first_k - len(post),
        "pre_sequence": [o.model_dump(mode="json") for o in pre],
        "post_sequence": [o.model_dump(mode="json") for o in post],
        "post_Q25": quantile(postvalues, Decimal("0.25")),
        "pre_Q25": quantile(prevalues, Decimal("0.25")),
        "pre_hits": sum(v >= options.goal for v in prevalues),
        "pre_goal_fraction": ratio(sum(v >= options.goal for v in prevalues), len(prevalues)),
        "post_goal_fraction": ratio(sum(v >= options.goal for v in postvalues), len(postvalues)),
        "post_hits": sum(v >= options.goal for v in postvalues),
        "interpretation": (
            "Non-causal temporal association in observed ordinary floor/follow-up; "
            "no audience-transfer inference"
        ),
    }
    if a is None or b is None or unknown_positions:
        return result("insufficient_history", **detail)
    state = (
        "available" if len(prevalues) == len(postvalues) == options.first_k else "partial_coverage"
    )
    return result(state, ratio(b + 1, a + 1), b + 1, a + 1, absolute_change=b - a, **detail)


def winners(frame, outcomes, panel, recent_entry):
    channel_members = {
        m.subject.entity_id: m for m in frame.members if m.subject.entity_kind == "channel"
    }
    channels, known, unknown, winnerset = defaultdict(list), set(), set(), set()
    unit_members = defaultdict(list)
    by_id = {v.video_id: v for v in frame.videos}
    for o in outcomes:
        if (
            not o.publication_at
            or not panel.publication.start <= o.publication_at < panel.publication.end
        ):
            if o.publication_at is None:
                unknown.add(by_id[o.video_id].membership.independence_unit)
            continue
        m = by_id[o.video_id].membership
        if m.state.value == "excluded":
            continue
        unit = m.independence_unit
        channels[unit].append(o.channel_id)
        if o.channel_id in channel_members:
            unit_members[unit].append(channel_members[o.channel_id])
        else:
            unit_members[unit].append(m)
        if o.state == "available":
            known.add(unit)
            if o.value >= panel.goal:
                winnerset.add(unit)
        else:
            unknown.add(unit)
    unknown -= winnerset
    return {
        "winners": winnerset,
        "unknown_outcome_units": unknown,
        "roster": {m.independence_unit for m in frame.members if m.subject.entity_kind == "channel"}
        or set(channels),
        "entry": {u: entry_bucket(ms, recent_entry) for u, ms in unit_members.items()},
        "known_units": known,
    }


def winner_change(old, new, state):
    if not old or not new:
        return result("insufficient_panel_history")
    if state not in {"available", "partial_coverage"}:
        return result(state)
    if old["roster"] != new["roster"]:
        return result(
            "coverage_not_comparable",
            older_roster=sorted(old["roster"]),
            newer_roster=sorted(new["roster"]),
        )
    a, b = old["winners"], new["winners"]
    shared, replacing = a & b, b - a
    entrants = {u for u in b if new["entry"].get(u) == "verified_entrant"}
    incumbents = {u for u in b if new["entry"].get(u) == "incumbent"}
    ambiguous = b - entrants - incumbents
    if old["unknown_outcome_units"] or new["unknown_outcome_units"]:
        state = "partial_coverage" if a or b else "insufficient_panel_history"
    fractions = {
        "replacement_share": ratio(len(replacing), len(b)),
        "incumbent_persistence": ratio(len(shared), len(a)),
        "verified_entrant_share": ratio(len(entrants), len(b)),
    }
    return result(
        state,
        **fractions,
        counts={
            "prior_winners": len(a),
            "later_winners": len(b),
            "retained": len(shared),
            "replacing": len(replacing),
            "verified_entrants": len(entrants),
            "incumbents": len(incumbents),
            "unknown_entry": len(ambiguous),
        },
        fractions={
            "replacement_share": {"numerator": len(replacing), "denominator": len(b)},
            "incumbent_persistence": {"numerator": len(shared), "denominator": len(a)},
            "verified_entrant_share": {"numerator": len(entrants), "denominator": len(b)},
        },
        entrant_bounds=[
            ratio(len(entrants), len(b)),
            ratio(len(entrants) + len(ambiguous), len(b)),
        ],
        older_winners=sorted(a),
        newer_winners=sorted(b),
        known_only=state == "partial_coverage",
        prior_unknown_outcomes=sorted(old["unknown_outcome_units"]),
        later_unknown_outcomes=sorted(new["unknown_outcome_units"]),
        panel_coverage=state,
    )
