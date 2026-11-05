# Database and prospective history

Schema version **5** appends core_analytics after frozen v1–v4. Frozen v1 checksum:
`df4ead10f9d64ecd7950b0c37717976e475bd2dd6e0a6ca1d047554509f12177`.
Migration metadata records version, name, SHA-256 SQL checksum and UTC applied time. Clean initialization installs [1,2,3,4,5]; v1/v2/v3/v4 append remaining migrations. Frozen v2 checksum: c44e9bcca6a67d4007c209e306958ed31d02ef60f25aeeac01bb0bfae34a89c9. Pending batches use BEGIN IMMEDIATE and roll back completely on failure. Future versions, gaps, altered checksums and nonempty unversioned databases remain refused.

| Tables | Purpose |
| --- | --- |
| schema_migrations, app_metadata | Frozen bootstrap and migration bookkeeping |
| channels, videos | Canonical IDs and earliest availability/first-seen time only |
| source_records | Source kind/version/precision, request/observed/available clocks, provenance and expiry |
| channel_observations, video_observations | Counts, typed per-metric evidence, versioned metadata, outcomes/details, metric definition and immutable capture hash |
| source_conflicts | Both observation/source identities, field, explicit preferred source/version and detection/availability clocks |
| discovery_runs, discovery_pages, discovery_results | Exact manifest, page tokens and failed/empty pages, every ordered occurrence |
| eligibility_decisions | Reused for generic evidence-state decisions and versioned Phase 2 classification headers; classification_details preserves the full typed result |
| snapshot_jobs, snapshot_targets | Explicit capture identity, known targets, per-ID outcome/HTTP reason and capture clocks |
| live_cache | Independent expiring current metadata |
| derived_cache | Empty foundation carrying input/version/permission identity |
| quota_requests | Endpoint, attempts, assumed cost, bucket, UTC timestamp and contract version |

Public metrics are never timeless columns on canonical entities. Current/historical metadata comes from an observation's metadata_json, including versioned channel membership and publication semantics. Counts also have numeric columns for retrieval; evidence_json preserves missing state, reason, precision and source per metric. No watchlist table is necessary: explicit snapshot targets suffice without scheduling.

Appending uses (capture_id, entity_kind, entity_id, source) identity. An identical replay returns the same observation; changed contents under that identity are refused. A new capture appends a new row even when counts remain unchanged. UPDATE triggers protect source/capture/decision/conflict/page/result evidence. Explicit policy deletion is the collection invariant's exception, not a refresh overwrite.

Known-at-time queries filter observed_at <= T, available_at <= T and entity first_seen <= T; UTC microsecond strings normalize offsets and preserve exact boundaries. Decisions also require decided_at <= T. There is no canonical latest-title shortcut. publication_size accepts only prior, available subscriber observations within an explicit bounded near-publication window (default one day, at most seven). With no such evidence it returns insufficient_history, never today's subscriber count.

Both official and provider observations may coexist. Explicit conflict records preserve disagreement and the official-detail preference; callers can request a source explicitly. Preference is not a license to delete the conflicting evidence.

Indexes support entity/time observations, first-seen frames, discovery run/page/rank, subject/time conflicts and decisions, source expiry and quota bucket/time. These match implemented retrieval/maintenance paths; no speculative analytic indexes are added.

Base retention is 30 days from observation (not import availability). Cache refresh does not extend the lifetime of an older capture. Reads exclude expired evidence; history purge-expired explicitly deletes expired sources/captures/conflicts, manifests/results/pages, decisions, caches, old jobs and obsolete orphan identities. Run maintenance before storing/serving data past the permitted horizon. No automatic write occurs during startup or verification. A source-scoped acceptance record can enable a separate statistics-only archive; no such record exists by default. Text cannot gain extended life. Independent annotations and internal configuration are exempt from a blanket API-data deletion rule, subject to their own declared expiry.

Connections preserve WAL, foreign keys, full synchronization and busy timeout. db integrity combines integrity_check and foreign_key_check. Read-only inspection does not create directories or migrate; SQLite can manage WAL/SHM sidecars. Source backups exclude SQLite data. Any separate data backup must share retention/deletion handling and use SQLite's consistent backup API, as described in backup docs.

Historical metrics only become strong after prospective observation accumulates. The local default database currently has no collected research history.

## Schema v3: 28 total tables, 11 added

| New table | Purpose |
| --- | --- |
| eligibility_rules | Stable immutable IDs, parameters and descriptions |
| classification_claims | Separate source claims, observed/available clocks, permission/origin and expiry |
| classification_details | FK extension of existing eligibility_decisions; label, evidence/conflict IDs, coverage, provenance |
| taxonomy_nodes | Stable ID plus taxonomy version, flexible level, validated higher-level parent |
| niche_memberships | Append-only multilabel assignments by subject/node/version/source/rule; evidence and semantic layers |
| creator_groups, creator_group_memberships | Documented creator/studio/network relations; evidence-backed channel grouping |
| cohort_definitions, cohort_memberships | Immutable boundary/rule/frame identity and every candidate outcome, frozen atomically |
| retention_permissions | Source-scoped acceptance reference, verifier, validity and statistical-month cap |
| statistical_history | Statistical evidence only, available-at gate and acceptance-bounded expiry; no raw metadata/text |

No existing table columns or v1/v2 statements changed. v3 updates schema_scope only. New claim/niche/statistical indexes match retrieval paths; UPDATE triggers protect every new table. Foreign keys protect node parents, rule extensions, group evidence, cohort members and accepted archives. Explicit purge cascades expired dependencies. Configuration, independently annotated evidence and valid statistics remain when a cache or raw-text capture expires; canonical identities referenced by valid evidence/frames are preserved. Derived decisions/cohort content cannot outlive restricted inputs. Definitions or taxonomy changes require new IDs/versions. Expired frozen frames cannot be replayed as valid evidence.

## Phase 2.5 v4 extension: 31 total tables

Frozen v3 checksum: 7296eb9bec26ba21ea8caa0f6be50895e7944fd987d06106b08e873ee588ae7d.
v4 checksum: 384125aba24302812cedd74d6dd9aeb088a2e40ba37b4540a82ad003beac391d.
provider_runs stores immutable ingestion/discovery manifests and bounded async job
provenance. provider_evidence extends existing source records with route-specific
fields/trust/provider clocks/normalization/anomalies. provider_quota_details extends
existing quota rows with provider/mode, nullable documented/charged cost, cached/free
state, HTTP outcome and unknown plan. All three have immutable UPDATE triggers.
No duplicated canonical public observation, discovery, cache or classification table.
Provider daily rows are auxiliary in provider_evidence, outside channel/video captures
and statistical_history; publication_size cannot read them. Transcript text lives only
in existing short-lived live_cache, with hash/track provenance in normalized evidence.
Explicit purge handles provider expiry and cascading sources/conflicts, independently
of cache expiry. Present permission status is contract_review_required, not permanent.

## Schema v5 / retained derivatives

34 tables total. New analysis_runs, analysis_metric_results and analysis_outcomes reuse immutable cohort IDs and source/input identities, with UPDATE triggers and cohort/run DELETE cascades. v5 checksum cf8f065640223bf1192b54f44ecef9acde06f738f3624cfec21ba55afec61383. v1–v4 statements/checksums unchanged. Manifest identity includes software/formula versions, frozen input hash, explicit options/cutoff/age/tolerance/goal/boundary/independence/missing policies; created_at is audit metadata. Raw numerators/denominators and Decimal outputs are retained, not just rounded percentages. Expiry is the earliest relevant input/permission expiry; revocation or dependency deletion blocks saved reads. Explicit purge deletes analysis_runs and cascades children. No duplicate history/source/cache tables or raw text archive. Configured DB was explicitly upgraded [5]; startup/verify do not migrate or analyze.

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
