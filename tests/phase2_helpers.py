from datetime import timedelta

from youtube_niche_mcp.eligibility.models import (
    Boundary,
    Candidate,
    Claim,
    CohortDefinition,
    NicheMembership,
    Subject,
    TaxonomyNode,
)
from youtube_niche_mcp.eligibility.repository import EligibilityRepository


def seed(
    repository,
    observation_factory,
    now,
    *,
    uploads=1,
    char="a",
    views=0,
    subscribers=8,
    publication=None,
    hidden=False,
    account_created=None,
):
    e = EligibilityRepository(repository)
    at = now - timedelta(minutes=10)
    channel = Subject(entity_kind="channel", entity_id="UC" + char * 22)
    capture = observation_factory(subscribers, kind="channel", entity_id=channel.entity_id, at=at)
    if account_created:
        capture = capture.model_copy(
            update={
                "metadata": capture.metadata.model_copy(
                    update={"account_created_at": account_created}
                )
            }
        )
    repository.append(capture)
    node = TaxonomyNode(
        node_id="industrial",
        taxonomy_version="topics-v1",
        label="Industrial history",
        level="niche",
        available_at=at,
    )
    e.add_node(node)
    videos = []
    for i in range(uploads):
        vid = Subject(entity_kind="video", entity_id=char * 10 + str(i))
        pub = publication or now - timedelta(days=1 + i)
        capture = observation_factory(views, entity_id=vid.entity_id, at=at, publication=pub)
        capture = capture.model_copy(
            update={
                "metadata": capture.metadata.model_copy(
                    update={"channel_id": channel.entity_id, "duration": "PT8M"}
                )
            }
        )
        repository.append(capture)
        for field, value, basis, rule in (
            ("duration_seconds", 480, "official_metadata", "long_form_v1_8m"),
            ("surface_format", "standard_vod_confirmed", "official_surface", "surface_format_v1"),
            ("live_status", "ordinary_vod", "official_metadata", "live_status_v1"),
            ("spoken_language", "en", "human_review", "spoken_language_v1"),
            ("faceless", "faceless", "human_review", "faceless_v1"),
        ):
            c = Claim(
                subject=vid,
                field=field,
                value=value,
                basis=basis,
                source="fixture:" + basis,
                source_version="v1",
                observed_at=at,
                available_at=at,
                reason="Offline fixture",
                complete_review=True,
                data_origin="independent_annotation",
                permission_state="permitted",
            )
            e.append_claim(c)
            e.evaluate(vid, rule, at=at)
        c = Claim(
            subject=vid,
            field="niche_membership",
            value={"node_id": "industrial", "state": "included"},
            basis="human_review",
            source="fixture:taxonomy",
            source_version="v1",
            observed_at=at,
            available_at=at,
            reason="Offline subject evidence",
            data_origin="independent_annotation",
            permission_state="permitted",
        )
        eid = e.append_claim(c)
        e.assign_niche(
            NicheMembership(
                subject=vid,
                node_id="industrial",
                taxonomy_version="topics-v1",
                state="included",
                confidence="high",
                evidence_ids=(eid,),
                rule_version="subject-v1",
                source=c.source,
                decided_at=at,
                available_at=at,
                reason="Industrial subject",
                semantic_layers={
                    "subject_entity": ("machines",),
                    "viewer_promise": ("explain history",),
                },
            )
        )
        videos.append(vid)
    size = Claim(
        subject=channel,
        field="subscriber_count",
        value={"count": None if hidden else subscribers, "hidden": hidden},
        basis="official_metadata",
        source="fixture:size",
        source_version="v1",
        observed_at=at,
        available_at=at,
        reason="Observed size",
        data_origin="independent_annotation",
        permission_state="permitted",
    )
    e.append_claim(size)
    e.evaluate(channel, "current_small_v1_50k", at=at)
    return e, channel, tuple(videos), at


def definition(now, kind="entrant", cohort_id="fixture-frame"):
    return CohortDefinition(
        cohort_id=cohort_id,
        kind=kind,
        created_at=now,
        known_at=now,
        research_run="offline-fixture-run",
        boundary=Boundary(
            boundary_id="mid-industrial-v1",
            taxonomy_version="topics-v1",
            node_ids=("industrial",),
            classifier_version="subject-v1",
            semantic_scope={"subject_entity": ["industrial history"], "spoken_language": ["en"]},
        ),
        publication_start=now - timedelta(days=400),
        publication_end=now,
        entry_start=now - timedelta(days=180),
        entry_end=now,
    )


def candidate(subject, at=None):
    return Candidate(subject=subject, entry_known_at=at)
