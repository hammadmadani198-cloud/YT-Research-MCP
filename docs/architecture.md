# Phase 7 public interface

The modular tools namespace contains typed requests, registration, shared-service orchestration, bounded public views, competitor descriptors, explicit acquisition and local watch persistence. PublicMCPServer sanitizes SDK validation failures; PublicSurface opens existing SQLite storage and never migrates. Reads are read-only; research and explicit refresh append frozen runs/captures through existing services. A per-request context cache reuses validated runs and bulk frame loads. Schema v7 adds only research_watches; 36 tables. No formula module, recommendation meaning or provider firewall changed. Declared country uses existing short-lived live_cache solely for display. Watches have optimistic revisions, owner namespaces and expiry, with no executor. Startup/status/verify do not contact providers. See the Phase 7 tool contract/reference/workflows.

## Archived Phase 0–6 implementation notes

# Phase 3 architecture

The Phase 0 package and SDK v2 stdio transport remain. server.py exposes one operational status resource; cli.py provides offline inspection and explicit migration/retention maintenance. Zero research tools are registered. Server creation does not read or write the database; a status-resource read may inspect an existing database using a read-only connection. Neither path contacts YouTube.

api/contracts.py is the single replaceable endpoint/quota contract. api/client.py uses httpx asynchronously with bounded timeout/retries, no redirects, public-part allowlists, sanitized failures, deterministic injectable clock/transport/sleep and per-ID hydration. api/quota.py records each real attempt and can persist its ledger through a repository sink. It does not estimate a project's remaining remote quota.

collectors/normalize.py maps current public facts to typed captures. Metric-specific precision distinguishes rounded subscribers from public counts. Publication, account creation, upload, playlist addition and provider index clocks have separate fields. collectors/discovery.py retains complete ordered occurrences and page outcomes; duplicate canonical IDs do not remove ranks. Uploads enumeration uses the uploads playlist route. collectors/provider.py retains optional protocols; the Phase 2.5 NexLev modules below provide acquisition/evidence.

services/snapshots.py captures provided known IDs explicitly, preserving per-target failures and clocks. A finished job replay produces its saved outcome without another request. Different measurements require new job IDs. Interrupted jobs resume targets whose atomic outcome has not been committed; interrupted discovery requires a new run, preserving its earlier partial manifest. Nested SQLite savepoints keep observations and target outcomes atomic. No scheduler or retrospective backfill exists.

history/repository.py owns append-only observations, external decision storage, source-conflict records, permitted-history reads and explicit retention purge. Historical reads require observed_at, available_at and first_seen_at at or before the requested time. Decisions additionally require decided_at. Metadata lives in capture versions, so canonical identity cannot leak a newer title or channel assignment. Source preference is explicit (latest(..., source=...)); conflict records identify the preferred preserved source and version without removing the alternative.

The three storage concepts remain distinct:

1. live_cache: expiring source/route/parameter-keyed metadata, freshness metadata, optional bounded stale fallback only for display following transient errors.
2. Observation/source tables: independently appended evidence. Snapshot collection never reads the live cache. Historical queries cannot use cache data.
3. derived_cache: reserved empty schema; DerivedIdentity carries input, analysis version and permission identity. No calculations or analysis cache writers exist.

Capabilities expose missing key/provider/history, policy-unknown and owner-authorization states. API-key presence indicates configuration only. Internal frozen-frame analytics are implemented; input-specific permissions and extended retention remain gated. Public captures expire after 30 days; historical query results exclude expired evidence. Purge is explicit and removes dependent rows by cascade. A verified source-scoped administrative acceptance record can archive statistics-only evidence for at most 36 calendar months. No acceptance is configured. Raw metadata remains bounded; independent annotations and configuration have separate retention semantics.

Secrets are excluded from configuration repr/serialization, sent in an API-key header, and rejected in cache/manifests/captures when identified. Known credential-bearing field names are rejected. Error text never includes a raw response or request URL. The normal test suite blocks live HTTP and uses checked-in synthetic fixtures.

The analysis/ namespace implements offline F1–F9, failure floor, F19 and F22, without scoring, clustering or recommendation logic.

## Phase 2 modules

eligibility/models.py separates immutable evidence claims, adjudicated classifications, taxonomy versions, semantic boundaries and cohort frames. rules.py contains 13 deterministic versioned rubrics; adapters.py maps captured audio/live/duration/subscriber metadata into evidence without fabricating a Shorts flag or full visual/audio review. repository.py reuses eligibility_decisions through classification_details, stores conflicting source claims, validates evidence clocks/expiry, aggregates observed video reviews and computes five distinct identity clocks. Later same-source observations are revisions; simultaneous independent disagreement stays explicit.

eligibility/cohorts.py constructs eligible-video, current-small-channel and entrant frames from known classifications. Candidates are canonicalized but every discovery occurrence is retained. Entrants require a declared eligibility landmark and first observed qualifying participation, not account birth or future-K completion. Freeze is atomic and immutable, preserves excluded/pending/conflicting cases, and does not read future views/success. Ownership grouping uses documented relations only; connected studio/network groups share a provisional independence unit.

history/retention.py separates scoped statistical archives from raw capture/text and caches. db/phase2.py appends v3 only; both prior migrations remain checksum-identical. New diagnostic commands and phase-2 status are offline. All external-data decisions expose policy_required until applicable permission is established; independent supplied annotations can be marked permitted. No hosted deployment, ML stack, provider integration or public research tools were added.

## Phase 2.5 optional provider evidence

collectors/nexlev contracts/client/models/repository/service implement documented
REST acquisition and narrow external EvidenceBatch ingestion through capability
routing. Official YouTube hydrates known IDs with existing normalizers and stores
canonical public captures; provider originals and field conflicts remain preserved.
Three v4 extension tables reuse existing sources/discovery/conflicts/claims/cache/quota.
Raw text is cached briefly, normalized provider history is separate from prospective
statistical history, and finance/proprietary scores stay outside eligibility/scoring.
No network/startup migration or fifteen research tools were added in Phase 2.5. Core formulas are added by Phase 3 below. Detailed provider lifecycle: provider-architecture.md,
nexlev-integration.md, nexlev-api-contract.md and nexlev-trust-model.md.

## Phase 3 shared outcomes and runs

analysis/ bulk reads frozen video/entrant frames with identical Boundary objects, retained official captures/scoped statistics, and frozen topic/group evidence. outcomes.py owns maturity/history/source gates; numerics.py owns Decimal and type-7 conventions; separate baseline/floor/repeatability/breadth/concentration/exposure/bounds primitives feed service.py. Schema v5 adds three append-only, input-expiring analysis tables. Saved reads recheck retained dependencies; no derived cache or network dependency. Metrics carry sample units, raw numerator/denominator, run/input identity and named coverage states. See phase-3-formula-contract.md and phase-3-analytics.md. No F10–F18/F20–F21/F23 or public research tools.

## Phase 4 current implementation (supersedes earlier deferrals)

Version 0.5.0 adds offline F10–F13/F20/F21 only. Schema v5/34 tables and migrations v1–v5 remain unchanged. HistoricalOptions are embedded in the existing analysis_runs manifest; analysis_metric_results/outcomes are reused. Bulk reads and the shared history gate preserve actual observation/availability clocks, explicit windows, ages, retained permissions and immutable replay. Stable discovery hashes include query/routes/provider/filters/locale/order/budgets/eligibility/boundary/capability versions; expansion and protocol changes block comparable supply/winner claims. Current snapshots cannot replace history. Provider T2 series remain separate diagnostics. F20 uses all first-k post-t0 uploads and is non-causal. F21 keeps replacement/persistence/entrant fractions separate under a stable creator panel. No reconstructed history, HTTP, confidence/recommendation model or public tools. See phase-4-formula-contract.md, phase-4-historical-analytics.md and phase-4-verification.md. F14–F18/F23 and Phase 5 remain unimplemented.


## Phase 5 current implementation (supersedes earlier deferrals)

Version 0.6.0 adds F14 public same-capture interactions, F15 validated distinct-premise
yield, F16 task burden/optional creator compatibility and optional F23 declared pilot
loss/time/evidence runway. Content gaps, saturation, packaging, continuation, faceless
paths, checked source diversity and separate rights/platform/factual axes remain
descriptive. Quantitative equations are unchanged. Schema v6 adds only immutable
qualitative_annotations; runs/results, permissions, taxonomy and sources are reused.
All input ancestry, known clocks and expiry are checked; sampled reviews retain bounded
seeded manifests. No raw transcript/comment/media archive or heavy ML. Current official
policy URLs, scope/version/refresh are documented separately. F17/F18, final ranking,
recommendation and public research tools remain absent. See phase-5-qualitative-contract.md,
phase-5-content-gaps.md, phase-5-production-risk.md and phase-5-verification.md. STOP before Phase 6.


## Phase 6 current implementation

Version 0.7.0 adds decision/models, evidence, synthesis, confidence, sorting,
sensitivity and service modules. Schema v6/35 tables is reused unchanged. Shared
AnalysisRun accepts typed Phase 6 manifests; replay checks retained ancestry,
permissions and frozen discovery fingerprints. Sensitivities are immutable derived
runs, bounded to 8/24/48 one-at-a-time checks. The engine reads stored evidence only.
F17 executes after generic synthesis and F18, with no path back into either.
Creator compatibility is a separate receipt. Public tool registration remains 0/15.
See phase-6-decision-synthesis.md and phase-6-sensitivity.md.
