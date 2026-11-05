"""Small deterministic rubrics. Thresholds are research conventions, not scores."""

import calendar
import re
from datetime import datetime, timedelta

from youtube_niche_mcp.eligibility.models import (
    Claim,
    Classification,
    ClassificationState,
    Rule,
    Subject,
)
from youtube_niche_mcp.services.safety import identity

S = ClassificationState
RULES = (
    *(
        Rule(
            rule_id=f"long_form_v1_{minutes}m",
            decision_type="long_form",
            description="Duration convention, independent of Shorts/live eligibility",
            parameters={"threshold_seconds": minutes * 60},
        )
        for minutes in (6, 8, 10)
    ),
    Rule(
        rule_id="surface_format_v1",
        decision_type="surface_format",
        description="Official surface confirms; duration alone does not identify Shorts",
    ),
    Rule(
        rule_id="live_status_v1",
        decision_type="live_status",
        description="Distinguish scheduled, current, archived live and ordinary VOD",
    ),
    Rule(
        rule_id="spoken_language_v1",
        decision_type="spoken_language",
        description="Default audio and sampled speech are leads; text and region are not audio",
    ),
    Rule(
        rule_id="faceless_v1",
        decision_type="faceless",
        description="Recurring human host is not central; verification is coverage scoped",
    ),
    *(
        Rule(
            rule_id=f"current_small_v1_{limit // 1000}k",
            decision_type="current_small",
            description="Current observed size, never historical size or success",
            parameters={"exclusive_limit": limit},
        )
        for limit in (50000, 100000)
    ),
    Rule(
        rule_id="niche_entry_v1",
        decision_type="niche_entry",
        description="First observed qualifying participation; earlier hidden uploads unknown",
    ),
    Rule(
        rule_id="continuity_v1",
        decision_type="continuity",
        description="Documented pivot indicators; no ownership-transfer inference",
    ),
    Rule(
        rule_id="activity_v1",
        decision_type="activity",
        description="Window-specific observed activity, never permanent abandonment",
    ),
    Rule(
        rule_id="creator_independence_v1",
        decision_type="creator_independence",
        description="Only documented disclosure/company/network relation permits grouping",
    ),
)
REGISTRY = {rule.rule_id: rule for rule in RULES}


def add_months(value: datetime, months: int) -> datetime:
    year, month0 = divmod(value.year * 12 + value.month - 1 + months, 12)
    return value.replace(
        year=year, month=month0 + 1, day=min(value.day, calendar.monthrange(year, month0 + 1)[1])
    )


def claim_id(claim: Claim) -> str:
    return identity(claim.model_dump(mode="json"))


def duration_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", value)
    if not match or not any(match.groups()):
        return None
    days, hours, minutes, seconds = (float(n or 0) for n in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def duration_band(seconds: float) -> str:
    for threshold, band in (
        (360, "below_6m"),
        (480, "6–8m"),
        (900, "8–15m"),
        (1800, "15–30m"),
        (3600, "30–60m"),
    ):
        if seconds < threshold:
            return band
    return "60m+"


def size_band(count: int) -> str:
    for limit, band in (
        (1000, "0–999"),
        (10000, "1k–9,999"),
        (50000, "10k–49,999"),
        (100000, "50k–99,999"),
    ):
        if count < limit:
            return band
    return "100k+"


def age_band(entry: datetime | None, at: datetime) -> str:
    if entry is None or entry > at:
        return "unknown"
    for months, band in (
        (6, "0–6 months"),
        (12, "6–12 months"),
        (24, "12–24 months"),
        (36, "24–36 months"),
    ):
        if at < add_months(entry, months):
            return band
    return ">36 months"


def strength(claim: Claim) -> tuple[int, bool, str]:
    rank = {
        "human_review": 5,
        "public_disclosure": 5,
        "shared_company": 5,
        "explicit_network": 5,
        "documented_source": 5,
        "official_surface": 4,
        "official_metadata": 4,
        "transcript_review": 4,
        "default_audio_language": 3,
        "sample_review": 2,
        "caption_metadata": 2,
        "provider_label": 1,
    }.get(claim.basis, 0)
    return rank, claim.complete_review, claim.available_at.isoformat()


def language_family(value: str) -> str:
    value = value.lower().replace("_", "-")
    if value == "english" or value.split("-")[0] == "en":
        return "en"
    return "mixed" if value in {"mixed", "mixed_language"} else value


def faceless_value(claim: Claim):
    if claim.basis == "provider_label" and isinstance(claim.value, bool):
        return "faceless" if claim.value else "not_faceless"
    return claim.value


def classify(
    subject: Subject, rule_id: str, claims: tuple[Claim, ...], *, decided_at: datetime
) -> Classification:
    rule = REGISTRY[rule_id]
    field = {
        "long_form": "duration_seconds",
        "current_small": "subscriber_count",
        "creator_independence": "creator_relation",
    }.get(rule.decision_type, rule.decision_type)
    relevant = []
    for claim in claims:
        if claim.subject != subject:
            raise ValueError("Cannot classify a different subject's evidence")
        if claim.available_at > decided_at or claim.observed_at > decided_at:
            raise ValueError("Future evidence cannot enter a decision")
        expiry = claim.expires_at
        if expiry is None and claim.data_origin != "independent_annotation":
            expiry = claim.observed_at + timedelta(days=30)
        if expiry is not None and expiry <= decided_at:
            raise ValueError("Expired evidence cannot enter a decision")
        if claim.field == field:
            relevant.append(claim)
    relevant.sort(key=strength, reverse=True)
    ids = tuple(claim_id(c) for c in relevant)
    label, state, reason, details, alternatives = (
        "unknown",
        S.UNKNOWN,
        "No sufficient evidence",
        {},
        [],
    )
    if rule.decision_type == "long_form":
        valid = [
            c
            for c in relevant
            if isinstance(c.value, int | float) and not isinstance(c.value, bool) and c.value >= 0
        ]
        if valid:
            seconds = valid[0].value
            threshold = rule.parameters["threshold_seconds"]
            label = "duration_eligible" if seconds >= threshold else "below_threshold"
            verified_duration = valid[0].basis in {"official_metadata", "human_review"}
            state = (
                (S.VERIFIED if label == "duration_eligible" else S.EXCLUDED)
                if verified_duration
                else S.LIKELY
            )
            reason = "Observed duration compared with declared research convention"
            details = {
                "duration_seconds": seconds,
                "threshold_seconds": threshold,
                "duration_band": duration_band(seconds),
                "platform_definition": False,
            }
            alternatives = [(c, c.value >= threshold) for c in valid]
    elif rule.decision_type == "surface_format":
        labels = {
            "short_form_confirmed",
            "standard_vod_confirmed",
            "probable_short",
            "probable_vod",
        }
        valid = [c for c in relevant if isinstance(c.value, str) and c.value in labels]
        if valid:
            preferred = valid[0]
            label = preferred.value
            if label.endswith("confirmed") and preferred.basis != "official_surface":
                label = "probable_short" if label == "short_form_confirmed" else "probable_vod"
            state = S.VERIFIED if label.endswith("confirmed") else S.LIKELY
            reason = (
                "Observed surface claim; metadata/duration cannot confer confirmed Shorts status"
            )
            alternatives = [(c, "short" if "short" in c.value else "vod") for c in valid]
    elif rule.decision_type == "live_status":
        labels = {"currently_live", "scheduled_live", "archived_live", "ordinary_vod"}
        valid = [c for c in relevant if isinstance(c.value, str) and c.value in labels]
        if valid:
            label = valid[0].value
            state = (
                S.VERIFIED
                if valid[0].basis in {"official_metadata", "human_review", "official_surface"}
                else S.LIKELY
            )
            reason = "Explicit live-status evidence; omitted live part is unknown"
            alternatives = [(c, c.value) for c in valid]
    elif rule.decision_type == "spoken_language":
        valid = [
            c
            for c in relevant
            if c.basis
            in {
                "default_audio_language",
                "transcript_review",
                "human_review",
                "sample_review",
                "caption_metadata",
                "provider_label",
            }
            and isinstance(c.value, str)
            and c.value
        ]
        if valid:
            c = valid[0]
            lang = c.value.lower().replace("_", "-")
            english = lang == "english" or lang.split("-")[0] == "en"
            mixed = lang in {"mixed", "mixed_language"}
            verified = c.complete_review and c.basis in {"human_review", "transcript_review"}
            label = (
                "mixed_language"
                if mixed
                else (
                    "verified_english"
                    if english and verified
                    else "likely_english"
                    if english
                    else "non_english"
                )
            )
            state = S.VERIFIED if verified else S.LIKELY
            reason = "Spoken-content evidence; metadata/provider/caption labels remain leads"
            details = {
                "spoken_language": "mixed" if mixed else "en" if english else lang,
                "language_confidence": "high" if verified else "medium",
                "complete_review": c.complete_review,
            }
            alternatives = [
                (
                    c,
                    language_family(c.value),
                )
                for c in valid
            ]
    elif rule.decision_type == "faceless":
        valid = [
            c
            for c in relevant
            if c.basis in {"human_review", "sample_review", "provider_label"}
            and faceless_value(c) in ("faceless", "hybrid", "host_central", "not_faceless")
        ]
        if valid:
            c = valid[0]
            count = len(c.reviewed_video_ids)
            denominator = c.eligible_video_count
            covered = subject.entity_kind == "video" or (
                denominator is not None and denominator >= 2 and count == denominator
            )
            verified = c.basis == "human_review" and c.complete_review and covered
            if faceless_value(c) == "faceless":
                label = (
                    "verified_faceless"
                    if verified
                    else (
                        "likely_faceless"
                        if c.basis != "provider_label"
                        and (c.complete_review or (subject.entity_kind == "channel" and count >= 2))
                        else "unknown"
                    )
                )
            else:
                label = "unknown" if faceless_value(c) == "not_faceless" else faceless_value(c)
            state = S.VERIFIED if verified else S.UNKNOWN if label == "unknown" else S.UNCERTAIN
            reason = "Host centrality rubric; provider boolean/one opening cannot verify a channel"
            details = {
                "reviewed_eligible_video_count": count,
                "eligible_video_count": denominator,
                "coverage": count / denominator if denominator else None,
                "complete_review": c.complete_review,
                "verification_scope": "reviewed observed catalog"
                if subject.entity_kind == "channel"
                else "video",
                "supporting_decision_ids": list(c.supporting_decision_ids),
            }
            alternatives = [(c, faceless_value(c)) for c in valid]
    elif rule.decision_type == "current_small":
        valid = [c for c in relevant if isinstance(c.value, dict)]
        if valid:
            c = valid[0]
            payload = c.value
            count = payload.get("count")
            if payload.get("hidden") is True:
                label, state, reason = (
                    "hidden",
                    S.UNKNOWN,
                    "Hidden is unknown, never zero or automatic exclusion",
                )
            elif isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                upper = payload.get("upper_bound", count)
                if not isinstance(upper, int) or isinstance(upper, bool) or upper < count:
                    raise ValueError("Invalid rounded-size interval")
                limit = rule.parameters["exclusive_limit"]
                label = (
                    "known_small"
                    if upper < limit
                    else "known_not_small"
                    if count >= limit
                    else "threshold_uncertain"
                )
                state = (
                    S.VERIFIED
                    if label == "known_small"
                    else S.EXCLUDED
                    if label == "known_not_small"
                    else S.UNCERTAIN
                )
                reason = "Observed current count interval, not size at entry/publication"
                details = {
                    "count": count,
                    "upper_bound": upper,
                    "size_band": size_band(count),
                    "exclusive_limit": limit,
                    "historical_size": "insufficient_history",
                }
            alternatives = [(c, c.value) for c in valid]
    elif rule.decision_type == "niche_entry":
        valid = [c for c in relevant if isinstance(c.value, dict)]
        if valid:
            payload = valid[0].value
            entry = payload.get("first_observed_niche_entry")
            if entry:
                entry_at = datetime.fromisoformat(entry)
                if entry_at.tzinfo is None or entry_at > decided_at:
                    raise ValueError("Entry requires a known timezone-aware participation clock")
                label, state = "first_observed_niche_entry", S.UNCERTAIN
                reason = "First observed qualifying participation; earlier history remains unknown"
                details = {
                    **payload,
                    "niche_entry_age_band": age_band(entry_at, decided_at),
                    "earlier_history": "unknown_hidden_deleted_private",
                }
    elif rule.decision_type == "activity":
        valid = [c for c in relevant if isinstance(c.value, dict)]
        if valid:
            payload = valid[0].value
            pubs = tuple(datetime.fromisoformat(p) for p in payload.get("publications", []))
            first = payload.get("first_observed")
            label = activity_state(
                pubs,
                first_observed=datetime.fromisoformat(first) if first else None,
                at=decided_at,
                followup_days=payload.get("followup_days", 90),
            )
            state = S.UNKNOWN if label == "status_unknown" else S.LIKELY
            reason = "Observed window; public inactivity does not establish permanent failure"
            details = {
                "followup_days": payload.get("followup_days", 90),
                "permanent_exit": "unknown",
            }
    elif rule.decision_type == "creator_independence":
        valid = [
            c
            for c in relevant
            if c.basis
            in {"public_disclosure", "shared_company", "explicit_network", "documented_source"}
            and isinstance(c.value, str)
            and c.value
        ]
        if valid:
            label, state = "documented_group", S.VERIFIED
            reason = "Documented grouping only; unknown relations are never asserted independent"
            details = {"group_ids": sorted({c.value for c in valid})}
    elif rule.decision_type == "continuity":
        valid = [c for c in relevant if isinstance(c.value, list)]
        if valid:
            indicators = set(x for c in valid for x in c.value if isinstance(x, str))
            strong = indicators & {
                "abrupt_subject_change",
                "unrelated_historic_uploads",
                "observed_name_change",
                "pre_entry_subscriber_base",
            }
            label = (
                "likely_pivot"
                if len(strong) >= 2
                else "possible_pivot"
                if strong or "old_account_recent_niche" in indicators
                else (
                    "continuity_consistent"
                    if "observed_subject_continuity" in indicators
                    else "continuity_unknown"
                )
            )
            state = S.LIKELY if label != "continuity_unknown" else S.UNKNOWN
            reason = "Continuity indicators; no ownership-transfer claim or automatic exclusion"
            details = {"indicators": sorted(indicators), "ownership_transfer": "unknown"}
    conflicts = ()
    if alternatives and any(value != alternatives[0][1] for _, value in alternatives):
        state = S.CONFLICTING
        conflicts = tuple(claim_id(c) for c, _ in alternatives)
        reason += "; competing source claims preserved; stronger evidence supplies preferred label"
    observed = max((c.observed_at for c in relevant), default=decided_at)
    available = max((c.available_at for c in relevant), default=decided_at)
    expiries = [
        c.expires_at
        or (
            c.observed_at + timedelta(days=30)
            if c.data_origin != "independent_annotation"
            else None
        )
        for c in relevant
    ]
    expiry = min((e for e in expiries if e is not None), default=None)
    permitted = bool(relevant) and all(c.permission_state == "permitted" for c in relevant)
    return Classification(
        subject=subject,
        decision_type=rule.decision_type,
        label=label,
        state=state,
        confidence="high" if state == S.VERIFIED else "unknown" if state == S.UNKNOWN else "medium",
        rule_version=rule_id,
        evidence_ids=ids,
        source="deterministic:" + rule_id,
        observed_at=observed,
        available_at=available,
        decided_at=decided_at,
        reason=reason,
        conflicts=conflicts,
        details=details,
        permission_state="permitted" if permitted else "policy_required",
        expires_at=expiry,
    )


def activity_state(
    publications: tuple[datetime, ...],
    *,
    first_observed: datetime | None,
    at: datetime,
    followup_days: int = 90,
) -> str:
    """A declared 90-day observation window is a heuristic, not a failure model."""
    if followup_days <= 0 or any(p > at for p in publications):
        raise ValueError("Invalid observation window or future publication")
    if first_observed is None:
        return "status_unknown"
    if at - first_observed < timedelta(days=followup_days):
        return "insufficient_followup"
    recent = [p for p in publications if p > at - timedelta(days=followup_days)]
    return (
        "currently_inactive_observed"
        if not recent
        else "low_output"
        if len(recent) <= 3
        else "active_observed"
    )
