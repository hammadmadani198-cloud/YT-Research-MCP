"""Prospective synthetic histories; no downloaded data or retrospective interpolation."""

from datetime import timedelta

from phase3_helpers import channel, frozen

from youtube_niche_mcp.domain.foundation import Metadata, timestamp
from youtube_niche_mcp.eligibility.models import (
    Boundary,
    Claim,
    CohortDefinition,
    CohortMember,
    Subject,
)
from youtube_niche_mcp.eligibility.repository import EligibilityRepository
from youtube_niche_mcp.history.retention import RetentionRepository, StoragePermission
from youtube_niche_mcp.services.safety import safe_json


def make_frame(
    repo,
    factory,
    now,
    name,
    rows,
    freeze,
    *,
    roster=(1, 2, 3),
    entries=None,
    state="included",
    boundary=None,
    group_shared=False,
):
    e = EligibilityRepository(repo)
    RetentionRepository(repo).record_permission(
        StoragePermission(
            source="youtube:videos.list",
            approval_reference="synthetic",
            verified_by="test",
            verified_at=now - timedelta(days=1000),
            expires_at=now + timedelta(days=200),
            statistical_months=36,
        )
    )
    boundary = boundary or Boundary(
        boundary_id="history", taxonomy_version="v1", node_ids=("niche",), classifier_version="v1"
    )
    cm = []
    for ci in roster:
        cid = channel(ci)
        group = "shared" if group_shared else "creator" + str(ci)
        eid = e.append_claim(
            Claim(
                subject=Subject(entity_kind="channel", entity_id=cid),
                field="creator_relation",
                value=group,
                basis="public_disclosure",
                source="fixture",
                source_version="v1",
                observed_at=freeze,
                available_at=freeze,
                reason="fixture",
                data_origin="independent_annotation",
                permission_state="permitted",
            )
        )
        e.group_channel(group, group, "creator", eid)
        entry = (entries or {}).get(ci, now - timedelta(days=200))
        cm.append(
            CohortMember(
                subject=Subject(entity_kind="channel", entity_id=cid),
                state="included",
                reason="frozen",
                evidence_ids=(eid,),
                independence_unit="group:" + group,
                independence_state="documented_group",
                entry_status={"first_observed_niche_entry": timestamp(entry)} if entry else {},
            )
        )
    vm = []
    for ci, vid, pub, points in rows:
        cid = channel(ci)
        claim_id = e.append_claim(
            Claim(
                subject=Subject(entity_kind="video", entity_id=vid),
                field="publication_at",
                value={"publication_at": timestamp(pub), "channel_id": cid},
                basis="documented_source",
                source="independently supplied synthetic chronology",
                source_version="v1",
                observed_at=freeze,
                available_at=freeze,
                reason="Prospective fixture chronology, not current API metadata",
                data_origin="independent_annotation",
                permission_state="permitted",
            )
        )
        for at, value, source, available in points:
            obs = factory(
                value,
                at=at,
                available=available,
                entity_id=vid,
                source=source,
                capture_id=name + vid + timestamp(at) + str(value),
                publication=pub,
            )
            obs = obs.model_copy(update={"metadata": Metadata(channel_id=cid, publication_at=pub)})
            repo.append(obs)
        group = "shared" if group_shared else "creator" + str(ci)
        vm.append(
            CohortMember(
                subject=Subject(entity_kind="video", entity_id=vid),
                state=state,
                reason="Frozen eligible synthetic frame",
                evidence_ids=(claim_id,),
                independence_unit="group:" + group,
                independence_state="documented_group",
            )
        )
    common = dict(
        created_at=freeze,
        known_at=freeze,
        research_run="synthetic",
        boundary=boundary,
        publication_start=now - timedelta(days=1000),
        publication_end=now + timedelta(days=1),
    )
    vd = CohortDefinition(cohort_id=name + "-videos", kind="eligible_long_form", **common)
    cd = CohortDefinition(
        cohort_id=name + "-entrants",
        kind="entrant",
        entry_start=now - timedelta(days=1000),
        entry_end=now,
        **common,
    )
    frozen(repo.connection, vd, vm)
    frozen(repo.connection, cd, cm)
    return vd.cohort_id, cd.cohort_id


def point(at, value, source="youtube:videos.list", available=None):
    return at, value, source, available or at


def discovery(
    repo,
    rid,
    at,
    videos,
    *,
    query="niche",
    provider="youtube",
    filters=None,
    route="search.list",
    partial=False,
    version="v1",
):
    repo.connection.execute(
        "INSERT INTO discovery_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            rid,
            query,
            route,
            provider,
            "date",
            safe_json({"parameters": filters or {"type": "video"}, "max_pages": 2}),
            "US",
            "en",
            "search_discovery",
            50,
            timestamp(at),
            timestamp(at),
            "available",
            version,
            timestamp(at + timedelta(days=30)),
        ),
    )
    repo.connection.execute(
        "INSERT INTO discovery_pages VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            rid,
            1,
            None,
            "unfinished" if partial else None,
            timestamp(at),
            timestamp(at),
            timestamp(at),
            "available",
            200,
            "synthetic",
        ),
    )
    for i, vid in enumerate(videos, 1):
        repo.connection.execute(
            "INSERT INTO discovery_results VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                rid,
                i,
                1,
                i,
                vid,
                "video",
                "returned_identifier",
                "available",
                timestamp(at),
                timestamp(at),
            ),
        )
