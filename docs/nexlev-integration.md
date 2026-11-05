# Optional NexLev acquisition integration — Phase 2.5

Version 0.3.5, schema v4, zero public research tools. The local Python stdio server
continues to initialize, verify and report status offline without either API key.

Mode A: documented REST with optional NEXLEV_API_KEY (SecretStr, process-only).
collectors/nexlev/contracts.py contains the closed allowlist and route/capability
registry; client.py uses httpx and the existing QuotaLedger architecture. GET retries
are bounded, excluding job creation; expensive POSTs and quota failures are not
retried. Redirects/environment proxies are disabled. Similar channels is synchronous;
similar thumbnails requires Deep mode. Documented async channel analysis persists
job events through provider_runs and polls within explicit bounds. No background task.

Mode B: NexLevRepository.ingest(EvidenceBatch) accepts narrow external/orchestrated
NexLev evidence. An external orchestrator owns its authenticated NexLev session.
The local server neither accesses that session nor implements remote MCP OAuth.
REST-absent semantic/outlier/viral/suggested/latest feeds remain orchestrator_only.
Daily history/faceless classifier/monetization claim routes are also externally supplied.

Internal library wiring, after explicit migration:

```python
from youtube_niche_mcp.collectors.nexlev.client import NexLevClient, ProviderQuotaLedger
from youtube_niche_mcp.collectors.nexlev.repository import NexLevRepository
from youtube_niche_mcp.collectors.nexlev.service import NexLevService

provider = NexLevRepository(history_repository, settings)
client = NexLevClient(
    settings,
    quota=ProviderQuotaLedger(sink=provider.record_quota),
    event_sink=provider.record_job_event,
)
service = NexLevService(client, provider)
# await service.acquire(run_id, "channel_about", {"id": canonical_channel_id})
# provider.ingest(validated_external_batch)
# await service.hydrate(existing_youtube_client, subject, capture_id=explicit_id)
# await client.aclose()
```

These commented calls are explicit collection operations, never invoked by CLI status,
verify/startup or ordinary tests. Service hydration uses the existing YouTubeClient,
normalizer, HistoryRepository, metadata claim adapter and eligibility engine. It returns
official captured values/outcome/hidden state and preserves all provider records/conflicts.
No unavailable official fact falls back to a provider value marked canonical.

acquire_pages is bounded, retaining page run manifests, continuation context and
cross-page canonical candidate dedup. Similarity acquisition preserves seed/depth/
channelType/rank in discovery context and separate T4 scores, without overlap/causal
claims. Provider taxonomy aliases can map many labels to many existing versioned
internal nodes; stored T3 annotations do not assign canonical niche memberships.

Schema v4 adds only provider_runs, provider_evidence and provider_quota_details.
source_records, source_conflicts, discovery_runs/pages/results, classification_claims,
live_cache, quota_requests and canonical entities are reused. Provider evidence lacks
the canonical-observation semantics required by OWN_HISTORY and thus remains separate.
Runs contain ingestion manifests or bounded job provenance; evidence extends routes/
field trust/provider clocks/anomalies. UPDATE triggers preserve append-only evidence.

Quota requests use existing quota_requests with a provider extension for nullable
documented/charged cost, cached/free status, access mode, HTTP status and plan state.
For an external unknown cost, the old mandatory assumed_cost slot is a compatibility
zero placeholder only: provider_quota_details NULL is authoritative, never a known
free charge. REST failures are documented free, transport/malformed reachability can
remain unknown. REST and external MCP plan buckets differ from YouTube buckets.
Hourly/minute caps are checked locally; account plan/balance remain unknown. Local
ledger safeguards do not claim to know another process's account usage.

Operational CLI (offline/read-only): provider status, capabilities, quota, contract,
cache-status. Status resource exposes capability records; configured availability
does not assert account entitlement or network reachability. Explicit client calls
record runtime auth/plan/quota/transient outcomes independently by route.

Retention/trust: see nexlev-trust-model.md. Raw/text use existing LiveCache with short
TTLs; text provenance/hash/track distinctions remain normalized without raw text.
Original/translated/generated fields stay unknown unless response evidence supports
them. Comments preserve ordering uncertainty and reply relationships in text cache.
Derived annotation extension is the existing independent Claim/DerivedIdentity layer;
no transcript or comment analytics are implemented here.

CMS ownership/network, promotions, private owner analytics, remote OAuth, Swipefile,
thumbnail generation, undocumented endpoints and bulk convenience APIs are deferred.
The five requested NexLev audit files were absent. Tests use synthetic diagnostic
fixtures, not claims that these channels currently exhibit those observations.
No live YouTube API requests; optional NexLev smoke skipped because key absent.
F1–F23, opportunity/confidence scores and the fifteen public tools remain unimplemented.
