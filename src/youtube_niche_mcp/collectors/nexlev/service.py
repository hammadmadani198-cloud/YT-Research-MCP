"""Explicit acquisition and official verification; no metric/recommendation engine."""

import re
from datetime import datetime

from youtube_niche_mcp.collectors.nexlev.models import (
    DiscoveryContext,
    EvidenceBatch,
    FieldClaim,
    ProviderRecord,
    plain_data,
)
from youtube_niche_mcp.collectors.normalize import normalize
from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.eligibility.adapters import metadata_claims
from youtube_niche_mcp.eligibility.models import Subject
from youtube_niche_mcp.services.cache import LiveCache
from youtube_niche_mcp.services.safety import identity

ALIASES = {
    "title": ("title", "channelName"),
    "view_count": ("viewCount",),
    "subscriber_count": ("subscriberCount", "subscriptionCount"),
    "video_count": ("videoCount", "videosCount"),
    "duration_seconds": ("lengthSeconds",),
    "publication_at": ("publishedAt", "publishDate"),
    "account_created_at": ("joinedDate",),
    "audio_language": ("defaultAudioLanguage",),
    "spoken_language": ("language",),
    "faceless": ("isFaceless", "faceless"),
    "isAiChannel": ("isAiChannel",),
    "quality": ("quality",),
    "isQualified": ("isQualified",),
    "category": ("category",),
    "format": ("format",),
    "outlier_score": ("outlierScore",),
    "vph": ("vph",),
    "semantic_similarity": ("similarity_score", "similarityScore"),
    "format_similarity": ("format_score",),
    "thumbnail_similarity": ("similarity",),
    "rpm": ("rpm",),
    "rpm_range": ("rpmRange",),
    "estimated_earnings": ("estimatedEarnings",),
    "monthly_revenue": ("month_revenue", "monthlyRevenue"),
    "yearly_revenue": ("yearlyRevenue",),
    "monetized": ("isMonetized",),
    "geography": ("viewership_country",),
    "demographics": ("demographics",),
    "average_views": ("avgViews", "averageViews"),
    "median_views": ("medianViews",),
    "upload_frequency": ("uploadFrequency",),
}


def instant(value):
    if not isinstance(value, str):
        return None
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return at if at.tzinfo is not None else None


def rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for name in ("data", "results", "items"):
            if isinstance(payload.get(name), list):
                return payload[name]
        return [payload]
    return []


def projected_claims(item, route):
    from youtube_niche_mcp.collectors.nexlev.models import COUNT_FIELDS, FIELD_TRUST

    result = []
    for field, aliases in ALIASES.items():
        value = next((item[k] for k in aliases if k in item), None)
        if value is None:
            continue
        if field in COUNT_FIELDS:
            if isinstance(value, str) and re.fullmatch(r"\d+", value):
                value = int(value)
            if type(value) is not int or value < 0:
                continue  # formatted/rounded text remains in short-lived raw cache only
        if field == "semantic_similarity" and route == "nexlev.similar_thumbnails":
            continue
        result.append(
            FieldClaim(
                field=field,
                value=value,
                trust_class=FIELD_TRUST[field],
                state="approximate",
                raw_precision="unknown",
            )
        )
    return tuple(result)


class NexLevService:
    def __init__(self, client, repository):
        self.client, self.repository = client, repository
        repository.secrets = tuple(set(repository.secrets + client.secret_values()))
        self.raw_cache = LiveCache(
            repository.connection,
            ttl_seconds=900,
            stale_seconds=0,
            clock=repository.history.clock,
            secrets=client.secret_values(),
        )
        self.text_cache = LiveCache(
            repository.connection,
            ttl_seconds=3600,
            stale_seconds=0,
            clock=repository.history.clock,
            secrets=client.secret_values(),
        )

    async def acquire(self, run_id, route, parameters, *, context=None, deep_mode=False):
        """Single explicit REST acquisition; paginate explicitly via acquire_pages when needed."""
        response = await self.client.request(route, parameters, deep_mode=deep_mode)
        if context is None and response.route in {
            "nexlev.similar_channels",
            "nexlev.similar_videos",
            "nexlev.similar_thumbnails",
            "nexlev.youtube_search",
            "nexlev.channel_videos",
        }:
            context = DiscoveryContext(
                query=parameters.get("query", parameters.get("text", "")),
                mode="similarity" if "similar" in response.route else "catalog",
                filters={k: v for k, v in parameters.items() if k != "token"},
                seed_id=parameters.get("channelId", parameters.get("videoId")),
                depth=parameters.get("level", 1)
                if response.route == "nexlev.similar_channels"
                else None,
                requested_channel_type=parameters.get("channelType", "all")
                if response.route == "nexlev.similar_channels"
                else None,
            )
        return self.store_response(run_id, response, parameters, context=context)

    def store_response(self, run_id, response, parameters, *, context=None):
        route, payload = response.route, response.payload
        cache_params = {("continuation" if k == "token" else k): v for k, v in parameters.items()}
        cache_params = response.request_parameters or cache_params
        plain_data(payload)
        text_route = route in {"nexlev.transcript", "nexlev.comments", "nexlev.subtitle"}
        cache = self.text_cache if text_route else self.raw_cache
        # cache never promotes provider responses to historical truth
        cache.put(
            "nexlev:text" if text_route else "nexlev:raw",
            route,
            cache_params,
            {"response": payload},
        )
        records = []
        for rank, raw in enumerate(rows(payload) or ([{}] if text_route else []), 1):
            if not isinstance(raw, dict):
                continue
            item = {**raw, **raw.get("about", {})} if isinstance(raw.get("about"), dict) else raw
            if isinstance(raw.get("videoData"), dict):
                item = {**raw["videoData"], **raw}
            if isinstance(raw.get("revenue"), dict):
                item = {**raw, **raw["revenue"]}
            if isinstance(raw.get("prediction"), dict):
                item = {**item, **raw["prediction"]}
                if "rpmMin" in item or "rpmMax" in item:
                    item["rpmRange"] = {"min": item.get("rpmMin"), "max": item.get("rpmMax")}
            channel_route = route in {
                "nexlev.channel_about",
                "nexlev.channel_analytics",
                "nexlev.similar_channels",
                "nexlev.short_vs_long",
                "nexlev.geography_revenue_estimate",
                "nexlev.niche_overview",
            }
            kind = "channel" if channel_route or item.get("type") == "channel" else "video"
            candidate = (
                item.get("channelId") if kind == "channel" else item.get("videoId", item.get("id"))
            )
            if candidate is None and route not in {
                "nexlev.similar_channels",
                "nexlev.similar_videos",
                "nexlev.similar_thumbnails",
                "nexlev.channel_videos",
                "nexlev.youtube_search",
            }:
                candidate = (
                    parameters.get("channelId", parameters.get("id"))
                    if kind == "channel"
                    else (parameters.get("videoId"))
                )
            if text_route:
                candidate = parameters["videoId"]
            from youtube_niche_mcp.domain.foundation import valid_id

            if not isinstance(candidate, str) or not valid_id(kind, candidate):
                continue
            claims = projected_claims(item, route)
            if text_route:
                selected = item.get("selected", {})
                language = selected.get("title") if isinstance(selected, dict) else None
                metadata = {
                    "content_hash": identity(item),
                    "selected_language": language,
                    "auto_generated": "auto-generated" in language.lower()
                    if isinstance(language, str)
                    else None,
                    "original": item.get("original")
                    if type(item.get("original")) is bool
                    else None,
                    "translated": item.get("translated")
                    if type(item.get("translated")) is bool
                    else None,
                    "available": bool(item.get("transcript"))
                    if route == "nexlev.transcript"
                    else bool(item),
                    "retention_state": "contract_review_required",
                    "track_languages": [
                        track.get("title")
                        for track in item.get("languageMenu", [])
                        if isinstance(track, dict) and isinstance(track.get("title"), str)
                    ],
                }
                if route == "nexlev.comments":
                    metadata.update(
                        ordering="provider_order_unknown",
                        disabled=item.get("disabled")
                        if type(item.get("disabled")) is bool
                        else None,
                        reply_relationship_state="preserved_in_text_cache_only",
                    )
                claims = (
                    FieldClaim(
                        field="comment_metadata"
                        if route == "nexlev.comments"
                        else "transcript_metadata",
                        value=metadata,
                        trust_class="T2",
                    ),
                )
            records.append(
                ProviderRecord(
                    route=route,
                    subject=Subject(entity_kind=kind, entity_id=candidate),
                    provider_record_id=str(item.get("recordId", candidate)),
                    provider_created_at=instant(item.get("created_at", item.get("createdAt"))),
                    provider_updated_at=instant(item.get("updated_at", item.get("updatedAt"))),
                    provider_capture_at=instant(item.get("dataFetchedAt")),
                    fetch_at=response.fetched_at,
                    observed_at=response.available_at,
                    available_at=response.available_at,
                    claims=claims,
                    rank=rank if context else None,
                    page_number=int(context.filters.get("page_number", 1)) if context else 1,
                )
            )
        return self.repository.ingest(
            EvidenceBatch(
                batch_id=run_id,
                route=route,
                fetch_at=response.fetched_at,
                records=tuple(records),
                discovery=context,
                access_mode="documented_rest",
            ),
            rest_verified=True,
        )

    async def hydrate(self, youtube, subject: Subject, *, capture_id):
        """Uses Phase 1 hydration/normalizer and Phase 2 adapters, with no provider fallback."""
        results = []
        for entity in await youtube.hydrate(subject.entity_kind, [subject.entity_id]):
            observation = normalize(entity, subject.entity_kind, capture_id)
            with atomic(self.repository.connection):
                oid = self.repository.history.append(observation)
                for claim in metadata_claims(observation):
                    self.repository.eligibility.append_claim(claim)
                result = self.repository.compare_official(oid, observation)
            result.update(
                outcome=observation.outcome.value,
                hidden_subscriber_state=observation.metadata.subscriber_hidden,
            )
            results.append(result)
        return results

    def map_taxonomy(self, subject, provider_label, internal_nodes, *, at):
        """Internal reviewed many-to-many alias annotation; never an automatic niche assignment."""
        for node_id, version in internal_nodes:
            row = self.repository.connection.execute(
                "SELECT 1 FROM taxonomy_nodes WHERE node_id=? AND taxonomy_version=?",
                (node_id, version),
            ).fetchone()
            if not row:
                raise ValueError("Existing internal taxonomy node/version required")
        annotation = {
            "subject": subject.model_dump(),
            "provider": "nexlev",
            "provider_label": provider_label,
            "internal_aliases": [list(node) for node in internal_nodes],
            "reviewed_at": at.isoformat(),
            "membership_assignment": False,
        }
        record = ProviderRecord(
            route="nexlev.faceless_classifier",
            subject=subject,
            provider_record_id=identity(annotation),
            fetch_at=at,
            observed_at=at,
            available_at=at,
            claims=(FieldClaim(field="taxonomy_labels", value=annotation, trust_class="T3"),),
        )
        self.repository.ingest(
            EvidenceBatch(
                batch_id=identity(annotation), route=record.route, fetch_at=at, records=(record,)
            )
        )
        return annotation

    async def acquire_pages(self, run_id, route, parameters, *, max_pages=10):
        pages = []
        async for number, response in self.client.pages(route, parameters, max_pages=max_pages):
            payload = response.payload
            context = DiscoveryContext(
                query=parameters.get("query", ""),
                mode="catalog",
                filters={
                    **{k: v for k, v in parameters.items() if k != "token"},
                    "page_number": number,
                },
                has_more=bool(payload.get("continuation")) if isinstance(payload, dict) else None,
                coverage_limitations=("Bounded page acquisition; terminal page is not a census",),
            )
            pages.append(
                self.store_response(
                    f"{run_id}:page:{number}", response, parameters, context=context
                )
            )
        return {
            "pages": pages,
            "coverage_state": "partial_coverage",
            "canonical_candidates": sorted(
                {tuple(candidate) for page in pages for candidate in page["canonical_candidates"]}
            ),
        }
