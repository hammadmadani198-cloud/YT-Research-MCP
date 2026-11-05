"""Rubric tests exercise ambiguity, coverage and evidence clocks, not model internals."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from youtube_niche_mcp.eligibility.models import Claim, Subject
from youtube_niche_mcp.eligibility.rules import (
    activity_state,
    add_months,
    age_band,
    classify,
    duration_seconds,
)

VIDEO = Subject(entity_kind="video", entity_id="aaaaaaaaaaa")
CHANNEL = Subject(entity_kind="channel", entity_id="UC" + "a" * 22)


def claim(now, field, value, basis="human_review", subject=VIDEO, **extra):
    return Claim(
        subject=subject,
        field=field,
        value=value,
        basis=basis,
        source="fixture:" + basis,
        source_version="fixture-v1",
        observed_at=now,
        available_at=now,
        reason="Synthetic evidence; no live source",
        data_origin="independent_annotation",
        permission_state="permitted",
        **extra,
    )


@pytest.mark.parametrize(
    "seconds,rule,label,band",
    [
        (480, "long_form_v1_8m", "duration_eligible", "8–15m"),
        (479, "long_form_v1_8m", "below_threshold", "6–8m"),
        (360, "long_form_v1_6m", "duration_eligible", "6–8m"),
        (599, "long_form_v1_10m", "below_threshold", "8–15m"),
        (600, "long_form_v1_10m", "duration_eligible", "8–15m"),
        (900, "long_form_v1_8m", "duration_eligible", "15–30m"),
        (1800, "long_form_v1_8m", "duration_eligible", "30–60m"),
        (3600, "long_form_v1_8m", "duration_eligible", "60m+"),
    ],
)
def test_duration_boundaries(now, seconds, rule, label, band):
    d = classify(VIDEO, rule, (claim(now, "duration_seconds", seconds),), decided_at=now)
    assert d.label == label and d.details["duration_band"] == band
    assert not d.details["platform_definition"]
    assert d.evidence_ids and d.rule_version == rule


@pytest.mark.parametrize("value", [None, "PT8M", "PT1H30M", "P1DT1S", "PT0S", "PT", "junk"])
def test_duration_parser(now, value):
    assert (
        duration_seconds(value)
        == {
            None: None,
            "PT8M": 480,
            "PT1H30M": 5400,
            "P1DT1S": 86401,
            "PT0S": 0,
            "PT": None,
            "junk": None,
        }[value]
    )


@pytest.mark.parametrize("value", [None, True, -1, "480"])
def test_missing_malformed_duration_unknown(now, value):
    d = classify(VIDEO, "long_form_v1_8m", (claim(now, "duration_seconds", value),), decided_at=now)
    assert d.state.value == "unknown"


def test_provider_duration_is_a_likely_lead(now):
    d = classify(
        VIDEO,
        "long_form_v1_8m",
        (claim(now, "duration_seconds", 480, "provider_label"),),
        decided_at=now,
    )
    assert d.label == "duration_eligible" and d.state.value == "likely"


@pytest.mark.parametrize(
    "value,basis,expected",
    [
        ("standard_vod_confirmed", "official_surface", "standard_vod_confirmed"),
        ("short_form_confirmed", "official_surface", "short_form_confirmed"),
        ("short_form_confirmed", "provider_label", "probable_short"),
        ("probable_vod", "provider_label", "probable_vod"),
    ],
)
def test_format_surface_and_provider_scope(now, value, basis, expected):
    d = classify(
        VIDEO, "surface_format_v1", (claim(now, "surface_format", value, basis),), decided_at=now
    )
    assert d.label == expected


@pytest.mark.parametrize("seconds", [30, 60, 180, 480, 3600])
def test_duration_alone_does_not_claim_shorts_or_vod(now, seconds):
    d = classify(
        VIDEO, "surface_format_v1", (claim(now, "duration_seconds", seconds),), decided_at=now
    )
    assert d.label == "unknown"


@pytest.mark.parametrize(
    "label", ["currently_live", "scheduled_live", "archived_live", "ordinary_vod", "unknown"]
)
def test_live_states(now, label):
    d = classify(
        VIDEO,
        "live_status_v1",
        (claim(now, "live_status", label, "official_metadata"),),
        decided_at=now,
    )
    assert d.label == label


@pytest.mark.parametrize(
    "value,basis,complete,label",
    [
        ("en-US", "default_audio_language", False, "likely_english"),
        ("en", "default_language", False, "unknown"),
        ("en", "text_language", False, "unknown"),
        ("en", "region", False, "unknown"),
        ("en", "caption_metadata", False, "likely_english"),
        ("en", "human_review", True, "verified_english"),
        ("en", "transcript_review", False, "likely_english"),
        ("mixed", "human_review", True, "mixed_language"),
        ("hi", "human_review", True, "non_english"),
    ],
)
def test_language_evidence_not_title_heuristic(now, value, basis, complete, label):
    d = classify(
        VIDEO,
        "spoken_language_v1",
        (claim(now, "spoken_language", value, basis, complete_review=complete),),
        decided_at=now,
    )
    assert d.label == label


def test_language_conflict_preserves_claims_and_preferred_review(now):
    claims = (
        claim(now, "spoken_language", "en", "provider_label"),
        claim(now, "spoken_language", "hi", "human_review", complete_review=True),
    )
    d = classify(VIDEO, "spoken_language_v1", claims, decided_at=now)
    assert d.label == "non_english" and d.state.value == "conflicting"
    assert len(d.conflicts) == len(d.evidence_ids) == 2


@pytest.mark.parametrize(
    "value,basis,complete,label",
    [
        ("faceless", "provider_label", False, "unknown"),
        ("faceless", "thumbnail", True, "unknown"),
        ("faceless", "production_style", True, "unknown"),
        ("faceless", "sample_review", False, "unknown"),
        ("faceless", "human_review", True, "verified_faceless"),
        ("hybrid", "human_review", True, "hybrid"),
        ("host_central", "human_review", True, "host_central"),
        ("face_appearance", "sample_review", False, "unknown"),
    ],
)
def test_faceless_host_centrality_not_production_shortcuts(now, value, basis, complete, label):
    d = classify(
        VIDEO,
        "faceless_v1",
        (claim(now, "faceless", value, basis, complete_review=complete),),
        decided_at=now,
    )
    assert d.label == label


@pytest.mark.parametrize(
    "count,total,complete,label",
    [
        (1, 10, False, "unknown"),
        (2, 10, True, "likely_faceless"),
        (2, 2, True, "verified_faceless"),
    ],
)
def test_channel_review_coverage(now, count, total, complete, label):
    ids = tuple(chr(97 + i) * 11 for i in range(count))
    c = claim(
        now,
        "faceless",
        "faceless",
        subject=CHANNEL,
        complete_review=complete,
        reviewed_video_ids=ids,
        eligible_video_count=total,
    )
    d = classify(CHANNEL, "faceless_v1", (c,), decided_at=now)
    assert d.label == label
    assert d.details["reviewed_eligible_video_count"] == count
    assert d.details["coverage"] == count / total


def test_provider_faceless_human_hybrid_conflict(now):
    claims = (
        claim(now, "faceless", "faceless", "provider_label"),
        claim(now, "faceless", "hybrid", "human_review", complete_review=True),
    )
    d = classify(VIDEO, "faceless_v1", claims, decided_at=now)
    assert d.label == "hybrid" and d.state.value == "conflicting" and len(d.conflicts) == 2


def test_provider_boolean_retained_as_claim_not_truth(now):
    provider = claim(now, "faceless", True, "provider_label")
    assert classify(VIDEO, "faceless_v1", (provider,), decided_at=now).label == "unknown"
    human = claim(now, "faceless", "hybrid", "human_review", complete_review=True)
    d = classify(VIDEO, "faceless_v1", (provider, human), decided_at=now)
    assert d.label == "hybrid" and d.state.value == "conflicting" and len(d.conflicts) == 2


def test_equivalent_english_tags_do_not_create_false_conflict(now):
    claims = (
        claim(now, "spoken_language", "en_US", "default_audio_language"),
        claim(now, "spoken_language", "English", "human_review", complete_review=True),
    )
    d = classify(VIDEO, "spoken_language_v1", claims, decided_at=now)
    assert d.label == "verified_english" and d.state.value == "verified" and not d.conflicts


@pytest.mark.parametrize(
    "value,rule,label,band",
    [
        ({"count": 0}, "current_small_v1_50k", "known_small", "0–999"),
        ({"count": 1000}, "current_small_v1_50k", "known_small", "1k–9,999"),
        ({"count": 10000}, "current_small_v1_50k", "known_small", "10k–49,999"),
        ({"count": 50000}, "current_small_v1_50k", "known_not_small", "50k–99,999"),
        ({"count": 99999}, "current_small_v1_100k", "known_small", "50k–99,999"),
        ({"count": 100000}, "current_small_v1_100k", "known_not_small", "100k+"),
        ({"hidden": True, "count": None}, "current_small_v1_50k", "hidden", None),
        ({"count": None}, "current_small_v1_50k", "unknown", None),
        (
            {"count": 49900, "upper_bound": 50100},
            "current_small_v1_50k",
            "threshold_uncertain",
            "10k–49,999",
        ),
    ],
)
def test_current_small_intervals_hidden_not_zero(now, value, rule, label, band):
    d = classify(
        CHANNEL, rule, (claim(now, "subscriber_count", value, subject=CHANNEL),), decided_at=now
    )
    assert d.label == label
    assert d.details.get("size_band") == band
    if band:
        assert d.details["historical_size"] == "insufficient_history"


@pytest.mark.parametrize(
    "months,band",
    [
        (0, "0–6 months"),
        (6, "6–12 months"),
        (12, "12–24 months"),
        (24, "24–36 months"),
        (37, ">36 months"),
    ],
)
def test_calendar_entry_age(now, months, band):
    assert age_band(now, add_months(now, months)) == band
    assert age_band(None, now) == "unknown"
    jan = datetime(2024, 1, 31, tzinfo=UTC)
    assert add_months(jan, 1).day == 29


@pytest.mark.parametrize(
    "indicators,label",
    [
        (["old_account_recent_niche"], "possible_pivot"),
        (["abrupt_subject_change", "unrelated_historic_uploads"], "likely_pivot"),
        (["observed_subject_continuity"], "continuity_consistent"),
        (["ownership_transfer_guessed"], "continuity_unknown"),
    ],
)
def test_continuity_never_claims_ownership(now, indicators, label):
    d = classify(
        CHANNEL,
        "continuity_v1",
        (claim(now, "continuity", indicators, subject=CHANNEL),),
        decided_at=now,
    )
    assert d.label == label and d.details["ownership_transfer"] == "unknown"


@pytest.mark.parametrize(
    "days,count,state",
    [
        (3, 1, "insufficient_followup"),
        (100, 0, "currently_inactive_observed"),
        (100, 1, "low_output"),
        (100, 3, "low_output"),
        (100, 4, "active_observed"),
    ],
)
def test_activity_descriptors_not_permanent_exit(now, days, count, state):
    dates = tuple(now - timedelta(days=i + 1) for i in range(count))
    assert activity_state(dates, first_observed=now - timedelta(days=days), at=now) == state
    assert activity_state((), first_observed=None, at=now) == "status_unknown"


def test_future_claim_and_bad_coverage_rejected(now):
    with pytest.raises(ValueError, match="Future"):
        classify(
            VIDEO,
            "long_form_v1_8m",
            (claim(now + timedelta(days=1), "duration_seconds", 480),),
            decided_at=now,
        )
    with pytest.raises(ValidationError, match="coverage"):
        claim(
            now,
            "faceless",
            "faceless",
            subject=CHANNEL,
            reviewed_video_ids=("a" * 11,),
            eligible_video_count=0,
        )
