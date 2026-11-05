"""Synthetic frozen artifacts, with real history/permission/taxonomy repositories."""

from datetime import timedelta
from decimal import Decimal

from youtube_niche_mcp.analysis.models import AnalysisOptions, CatalogCoverage
from youtube_niche_mcp.domain.foundation import Metadata, timestamp
from youtube_niche_mcp.eligibility.models import (
    Boundary,
    Claim,
    CohortDefinition,
    CohortMember,
    NicheMembership,
    Subject,
    TaxonomyNode,
)
from youtube_niche_mcp.eligibility.repository import EligibilityRepository
from youtube_niche_mcp.history.retention import RetentionRepository, StoragePermission
from youtube_niche_mcp.services.safety import identity, safe_json


def channel(i):
    return f"UC{i:022d}"


def video(i):
    return f"v{i:010d}"


def options(now, **changes):
    body = dict(
        cutoff=now,
        age_days=30,
        tolerance_seconds=0,
        goal=10000,
        low_threshold=500,
        own_minimum=5,
        peer_video_minimum=1,
        peer_channel_minimum=1,
        pooling_k=10,
        breadth_k=1,
        classification_minimum=Decimal("1"),
        exposure_days=90,
        first_k=10,
        finite_frame_reference="synthetic enumerated research panel",
    )
    body.update(changes)
    return AnalysisOptions(**body)


def frozen(connection, definition, members):
    connection.execute(
        "INSERT INTO cohort_definitions VALUES(?,?,?,?,?,?,?)",
        (
            definition.cohort_id,
            timestamp(definition.created_at),
            timestamp(definition.known_at),
            "synthetic",
            safe_json(definition.model_dump(mode="json")),
            identity([m.model_dump(mode="json") for m in members]),
            None,
        ),
    )
    for m in members:
        connection.execute(
            "INSERT INTO cohort_memberships VALUES(?,?,?,?,?)",
            (
                definition.cohort_id,
                m.subject.entity_kind,
                m.subject.entity_id,
                m.state.value,
                safe_json(m.model_dump(mode="json")),
            ),
        )


def seed(
    repository,
    observation_factory,
    now,
    channels,
    *,
    topics=None,
    shared=False,
    known_groups=True,
    permissions=True,
    entry_days=200,
    spacing=1,
    prefix="panel",
    publication_days=None,
    member_state="included",
):
    freeze = now - timedelta(days=2)
    e = EligibilityRepository(repository)
    if permissions:
        RetentionRepository(repository).record_permission(
            StoragePermission(
                source="youtube:videos.list",
                approval_reference="synthetic scoped permission fixture",
                verified_by="test administrative input",
                verified_at=now - timedelta(days=1000),
                expires_at=now + timedelta(days=200),
                statistical_months=36,
            )
        )
    boundary = Boundary(
        boundary_id="boundary-v1",
        taxonomy_version="topics-v1",
        node_ids=("niche",),
        classifier_version="topic-v1",
    )
    e.add_node(
        TaxonomyNode(
            node_id="niche",
            taxonomy_version="topics-v1",
            label="Synthetic",
            level="niche",
            available_at=now - timedelta(days=1000),
        )
    )
    for topic in sorted(set(topics or ["a"])):
        e.add_node(
            TaxonomyNode(
                node_id=topic,
                taxonomy_version="topics-v1",
                label=topic,
                level="topic_family",
                parent_id="niche",
                available_at=now - timedelta(days=1000),
            )
        )
    vm, cm, ids, covered = [], [], [], []
    index = 0
    for ci, values in enumerate(channels):
        cid = channel(ci + 1)
        subject = Subject(entity_kind="channel", entity_id=cid)
        group = "shared" if shared else f"creator-{ci}"
        if known_groups:
            claim = Claim(
                subject=subject,
                field="creator_relation",
                value=group,
                basis="public_disclosure",
                source="synthetic independent annotation",
                source_version="v1",
                observed_at=freeze,
                available_at=freeze,
                reason="Synthetic documented identity",
                data_origin="independent_annotation",
                permission_state="permitted",
            )
            evidence = e.append_claim(claim)
            e.group_channel(group, group, "creator", evidence)
        unit = f"group:{group}" if known_groups else f"channel:{cid}"
        state = "documented_group" if known_groups else "unknown"
        entry = now - timedelta(days=entry_days)
        cm.append(
            CohortMember(
                subject=subject,
                state="included",
                reason="Frozen synthetic entrant",
                entry_status={"first_observed_niche_entry": timestamp(entry)},
                independence_unit=unit,
                independence_state=state,
            )
        )
        covered.append(
            CatalogCoverage(
                channel_id=cid,
                through=min(entry + timedelta(days=90), freeze),
                available_at=freeze,
                evidence_reference="reviewed synthetic catalog",
            )
        )
        for j, value in enumerate(values):
            index += 1
            vid = video(index)
            ids.append(vid)
            pub = (
                now - timedelta(days=publication_days)
                if publication_days is not None
                else entry + timedelta(days=j * spacing)
            )
            capture = observation_factory(999999, entity_id=vid, at=freeze, publication=pub)
            capture = capture.model_copy(
                update={"metadata": Metadata(channel_id=cid, publication_at=pub)}
            )
            mid = repository.append(capture)
            if value is not None:
                at = pub + timedelta(days=30)
                outcome = observation_factory(value, entity_id=vid, at=at, publication=pub)
                outcome = outcome.model_copy(
                    update={"metadata": Metadata(channel_id=cid, publication_at=pub)}
                )
                repository.append(outcome)
            m = CohortMember(
                subject=Subject(entity_kind="video", entity_id=vid),
                state=member_state,
                reason="Frozen synthetic long-form eligibility",
                evidence_ids=(mid,),
                independence_unit=unit,
                independence_state=state,
            )
            vm.append(m)
            if topics:
                topic = topics[ci]
                s = m.subject
                c = Claim(
                    subject=s,
                    field="niche_membership",
                    value={"node_id": topic, "state": "included"},
                    basis="human_review",
                    source="fixture topic",
                    source_version="v1",
                    observed_at=freeze,
                    available_at=freeze,
                    reason="Reviewed synthetic topic",
                    data_origin="independent_annotation",
                    permission_state="permitted",
                )
                eid = e.append_claim(c)
                e.assign_niche(
                    NicheMembership(
                        subject=s,
                        node_id=topic,
                        taxonomy_version="topics-v1",
                        state="included",
                        confidence="high",
                        evidence_ids=(eid,),
                        rule_version="topic-v1",
                        source="fixture topic",
                        decided_at=freeze,
                        available_at=freeze,
                        reason="Reviewed synthetic topic",
                    )
                )
    common = dict(
        created_at=freeze,
        known_at=freeze,
        research_run="synthetic",
        boundary=boundary,
        publication_start=now - timedelta(days=1000),
        publication_end=now,
    )
    vd = CohortDefinition(cohort_id=prefix + "-videos", kind="eligible_long_form", **common)
    cd = CohortDefinition(
        cohort_id=prefix + "-entrants",
        kind="entrant",
        entry_start=now - timedelta(days=1000),
        entry_end=now,
        **common,
    )
    frozen(repository.connection, vd, vm)
    frozen(repository.connection, cd, cm)
    return vd.cohort_id, cd.cohort_id, tuple(ids), options(now, coverage=tuple(covered))


def metrics(bundle):
    return {m.formula_id: m for m in bundle.metrics}
