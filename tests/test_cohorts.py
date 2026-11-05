import json
import sqlite3
from datetime import timedelta

import httpx
import pytest
from phase2_helpers import candidate, definition, seed
from pydantic import SecretStr

from youtube_niche_mcp.api.client import YouTubeClient
from youtube_niche_mcp.collectors.discovery import DiscoveryService
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.eligibility.cohorts import CohortBuilder
from youtube_niche_mcp.eligibility.models import (
    Claim,
    ClassificationState,
    NicheMembership,
    TaxonomyNode,
)


@pytest.mark.parametrize(
    "uploads,views,subscribers,days",
    [(1, 0, 0, 1), (3, 4, 8, 2), (1, 0, 1, 150), (3, 20, 100, 120)],
)
def test_weak_low_output_stopped_entrants_retained_no_future_k(
    repository, observation_factory, now, uploads, views, subscribers, days
):
    e, channel, _, at = seed(
        repository,
        observation_factory,
        now,
        uploads=uploads,
        views=views,
        subscribers=subscribers,
        publication=now - timedelta(days=days),
    )
    builder = CohortBuilder(e)
    d = definition(now)
    frame = builder.freeze(d, (candidate(channel, at),))
    assert len(frame) == 1 and frame[0].state.value == "included_with_uncertainty"
    assert "Earlier hidden/deleted/private niche participation unknown" in frame[0].uncertainties
    assert frame[0].entry_status["first_observed_niche_entry"]
    assert builder.read(d.cohort_id) == frame
    # Growth, a new hit, or revised classifiers cannot update the frozen frame.
    repository.append(
        observation_factory(500000, kind="channel", entity_id=channel.entity_id, at=now)
    )
    assert builder.freeze(d, (candidate(channel, at), candidate(channel, at))) == frame
    with pytest.raises(ValueError, match="redefined"):
        builder.freeze(
            d.model_copy(update={"small_rule": "current_small_v1_100k"}), (candidate(channel, at),)
        )
    with pytest.raises(sqlite3.IntegrityError, match="Append-only"):
        repository.connection.execute("UPDATE cohort_memberships SET state='excluded'")


def test_hidden_size_retained_with_uncertainty(repository, observation_factory, now):
    e, channel, _, at = seed(repository, observation_factory, now, hidden=True)
    frame = CohortBuilder(e).freeze(definition(now, "small_channel"), (candidate(channel),))
    assert frame[0].state.value == "included_with_uncertainty"
    assert "Current subscriber size hidden" in frame[0].uncertainties
    assert (
        repository.publication_size(channel.entity_id, now - timedelta(days=40)).state.value
        == "insufficient_history"
    )


@pytest.mark.parametrize(
    "label,allow,state",
    [
        ("archived_live", False, "excluded"),
        ("archived_live", True, "included"),
        ("currently_live", False, "excluded"),
        ("scheduled_live", False, "excluded"),
        ("unknown", False, "pending_classification"),
    ],
)
def test_live_cohort_filter_preserves_candidates(
    repository, observation_factory, now, label, allow, state
):
    e, _, videos, _ = seed(repository, observation_factory, now)
    d = definition(now, "eligible_long_form").model_copy(update={"allow_archived_live": allow})
    # Evaluate a new source-free unknown, or replace the same-source claim at a later capture.
    if label == "unknown":
        decision = e.latest(videos[0], "live_status_v1", now)[1]
        decision = decision.model_copy(
            update={
                "label": "unknown",
                "state": ClassificationState.UNKNOWN,
                "confidence": "unknown",
                "evidence_ids": (),
                "decided_at": now,
            }
        )
        e.record_decision(decision)
    else:
        c = Claim(
            subject=videos[0],
            field="live_status",
            value=label,
            basis="official_metadata",
            source="fixture:official_metadata",
            source_version="v1",
            observed_at=now,
            available_at=now,
            reason="Later status evidence",
            data_origin="independent_annotation",
            permission_state="permitted",
        )
        e.append_claim(c)
        # The prior ordinary claim is a historical state, not a simultaneous disagreement.
        from youtube_niche_mcp.eligibility.rules import classify

        e.record_decision(classify(videos[0], "live_status_v1", (c,), decided_at=now))
    frame = CohortBuilder(e).freeze(d, (candidate(videos[0]),))
    assert frame[0].state.value == state
    assert frame[0].decision_ids
    if state == "excluded":
        assert frame[0].exclusion_reason
        assert repository.latest("video", videos[0].entity_id, now)


def test_entry_landmark_and_earlier_entry_window_not_recruit_by_later_upload(
    repository, observation_factory, now
):
    e, channel, _, at = seed(
        repository, observation_factory, now, uploads=1, publication=now - timedelta(days=200)
    )
    builder = CohortBuilder(e)
    frame = builder.freeze(definition(now), (candidate(channel, at),))
    assert frame[0].state.value == "excluded"
    assert "outside declared entry window" in frame[0].reason
    no_landmark = builder.freeze(definition(now, cohort_id="no-landmark"), (candidate(channel),))
    assert no_landmark[0].state.value == "pending_classification"


def test_future_eligibility_cannot_enter_earlier_landmark(repository, observation_factory, now):
    e, channel, _, at = seed(repository, observation_factory, now)
    frame = CohortBuilder(e).freeze(
        definition(now), (candidate(channel, at - timedelta(minutes=1)),)
    )
    assert frame[0].state.value == "insufficient_evidence"


@pytest.mark.parametrize("old_account", [True, False])
def test_five_clocks_old_or_recent_account_are_not_niche_entry(
    repository, observation_factory, now, old_account
):
    birth = now - timedelta(days=3650 if old_account else 10)
    e, channel, _, _ = seed(repository, observation_factory, now, account_created=birth)
    clocks = e.clocks(channel.entity_id, "topics-v1", {"industrial"}, now)
    assert clocks["account_created_at"].startswith(birth.date().isoformat())
    assert clocks["first_observed_niche_entry"] != clocks["account_created_at"]
    assert clocks["first_visible_upload"] == clocks["first_observed_eligible_long_form"]
    assert clocks["niche_entry_age_band"] == "0–6 months"
    assert clocks["earlier_history"] == "unknown_hidden_deleted_private"


def test_multilabel_hierarchy_versions_and_conflicting_classifiers(
    repository, observation_factory, now
):
    e, _, videos, at = seed(repository, observation_factory, now)
    e.add_node(
        TaxonomyNode(
            node_id="machines",
            taxonomy_version="topics-v1",
            label="Machines",
            level="topic_family",
            parent_id="industrial",
            available_at=at,
        )
    )

    def assign(node, state, source):
        c = Claim(
            subject=videos[0],
            field="niche_membership",
            value={"node_id": node, "state": state},
            basis="human_review",
            source=source,
            source_version="v1",
            observed_at=at,
            available_at=at,
            reason="Subject annotation",
            data_origin="independent_annotation",
            permission_state="permitted",
        )
        eid = e.append_claim(c)
        return e.assign_niche(
            NicheMembership(
                subject=videos[0],
                node_id=node,
                taxonomy_version="topics-v1",
                state=state,
                confidence="high",
                evidence_ids=(eid,),
                rule_version="subject-v1",
                source=source,
                decided_at=at,
                available_at=at,
                reason="Versioned assignment",
            )
        )

    assign("machines", "included", "human:second-label")
    assert {m.node_id for _, m in e.memberships(videos[0], "topics-v1", now)} == {
        "industrial",
        "machines",
    }
    assign("industrial", "excluded", "provider:conflicting")
    frame = CohortBuilder(e).freeze(definition(now, "eligible_long_form"), (candidate(videos[0]),))
    assert frame[0].state.value == "source_conflict"
    assert len(e.memberships(videos[0], "topics-v1", now)) == 3
    with pytest.raises(ValueError, match="new version"):
        e.add_node(
            TaxonomyNode(
                node_id="industrial",
                taxonomy_version="topics-v1",
                label="Renamed",
                level="niche",
                available_at=at,
            )
        )
    e.add_node(
        TaxonomyNode(
            node_id="industrial",
            taxonomy_version="topics-v2",
            label="Renamed",
            level="niche",
            available_at=now,
        )
    )
    assert not e.memberships(videos[0], "topics-v2", now)
    with pytest.raises(ValueError, match="higher-level"):
        e.add_node(
            TaxonomyNode(
                node_id="bad-parent",
                taxonomy_version="topics-v1",
                label="Bad",
                level="category",
                parent_id="machines",
                available_at=now,
            )
        )


def test_known_creator_group_unknown_style_and_overlapping_groups(
    repository, observation_factory, now
):
    e, a, _, at = seed(repository, observation_factory, now, char="a")
    _, b, _, _ = seed(repository, observation_factory, now, char="b")
    assert e.independence(a.entity_id, now)["state"] == "unknown"
    for channel in (a, b):
        c = Claim(
            subject=channel,
            field="creator_relation",
            value="shared-studio",
            basis="public_disclosure",
            source="human:disclosed-company",
            source_version="v1",
            observed_at=at,
            available_at=at,
            reason="Synthetic public company disclosure",
            data_origin="independent_annotation",
            permission_state="permitted",
        )
        e.group_channel("shared-studio", "Shared Studio", "studio", e.append_claim(c))
    assert e.independence(a.entity_id, now)["unit"] == e.independence(b.entity_id, now)["unit"]
    weak = c.model_copy(update={"value": "style-group", "basis": "production_style"})
    with pytest.raises(ValueError, match="Style similarity"):
        e.group_channel("style-group", "Similar", "studio", e.append_claim(weak))
    frame = CohortBuilder(e).freeze(
        definition(now), (candidate(a, at), candidate(b, at), candidate(a, at))
    )
    assert len(frame) == 2 and len({m.independence_unit for m in frame}) == 1


@pytest.mark.anyio
async def test_discovery_duplicates_all_routes_preserved_not_independent_creators(
    repository, observation_factory, now
):
    e, channel, videos, at = seed(repository, observation_factory, now)
    payload = {"items": [{"id": {"kind": "youtube#channel", "channelId": channel.entity_id}}] * 2}
    async with YouTubeClient(
        Settings(youtube_api_key=SecretStr("fixture-secret")),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
        clock=lambda: at,
    ) as client:
        service = DiscoveryService(client, repository)
        for run, query in (("recent", "recent industrial"), ("weak", "adjacent machinery")):
            await service.collect(run, query=query, filters={"order": "date"}, page_size=2)
    frame = CohortBuilder(e).freeze(definition(now), (candidate(channel, at),) * 5)
    assert len(frame) == 1 and len(frame[0].discovery_occurrences) == 4
    assert {r["run_id"] for r in frame[0].discovery_occurrences} == {"weak", "recent"}
    assert {r["rank"] for r in frame[0].discovery_occurrences} == {1, 2}
    assert frame[0].independence_state == "unknown"


def test_duration_rule_versions_append_no_overwrite(repository, observation_factory, now):
    e, _, videos, at = seed(repository, observation_factory, now)
    original = e.latest(videos[0], "long_form_v1_8m", now)
    new_id, new = e.evaluate(videos[0], "long_form_v1_10m", at=at)
    assert new.label == "below_threshold" and new_id != original[0]
    assert e.latest(videos[0], "long_form_v1_8m", now) == original
    with pytest.raises(sqlite3.IntegrityError, match="Append-only"):
        repository.connection.execute("UPDATE classification_claims SET source='changed'")
    with pytest.raises(ValueError):
        e.append_claim(
            Claim(
                subject=videos[0],
                field="faceless",
                value="fixture-secret",
                basis="human_review",
                source="fixture",
                source_version="v1",
                observed_at=at,
                available_at=at,
                reason="Sensitive payload",
            )
        )


def test_frozen_member_does_not_store_lifetime_counts(repository, observation_factory, now):
    e, channel, _, at = seed(repository, observation_factory, now, views=1234567)
    frame = CohortBuilder(e).freeze(definition(now), (candidate(channel, at),))
    assert "1234567" not in json.dumps([m.model_dump(mode="json") for m in frame])
