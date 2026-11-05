# Provider trust and field firewall

NexLev discovers/enriches; official YouTube verifies material public facts; the
local Phase 2 engine owns classifications and frozen cohorts. F1–F23 remain absent.

| Class | Examples | Admitted use |
| --- | --- | --- |
| T0 identifier | Valid channel/video IDs | Resolution and dedup; existence still requires hydration |
| T1 public fact candidate | Title, current counts, duration, publication/join time | Explicit official hydration; provider value remains preserved |
| T2 auxiliary observation | Provider index/daily series, transcript metadata | Source/route/clocks, text hashes and anomaly flags |
| T3 provider classification | Faceless, audio/language, AI, quality, qualified, taxonomy | Evidence claim; no verified flag, policy violation or membership shortcut |
| T4 provider derived | Outlier, semantic/format/thumbnail similarity, averages/VPH | Discovery and descriptive provider context; no local opportunity score |
| T5 provider estimate/claim | RPM/range, modeled income, monetization, geography | Labeled estimates only; excluded from eligibility/canonical facts/core scoring |
| T6 owner private | Retention, own revenue/traffic | Reserved, ingestion prohibited |
| T7 workflow | Swipefile | Excluded, ingestion prohibited |

FieldClaim validates the field-to-trust map. EvidenceBatch forbids extra fields,
unknown/reserved routes, incorrect IDs, invalid clocks, arbitrary HTML/executable
content, raw transcript text, self-attested REST acquisition and canonical verification.
The repository revalidates models and suppresses input-bearing validation errors.
Secrets are rejected in evidence/cache/manifests/quota, including camelCase credential
fields. Serialized Settings omit both API keys; diagnostics show presence only.

Every route observation preserves provider record identity, provider creation/update/
capture clocks, local fetch/observation/availability, per-field precision/state, and
normalization version. Immutable replay is idempotent; changed replay is rejected.
Cross-route differing non-null claims generate existing source_conflicts records.
Count changes at different capture times are separate snapshots, not contradictions.
Material publication/duration disagreement remains a conflict even when official
hydration selects its captured public value. Neither side is silently overwritten.

Provider faceless=True/confidence=0.98 cannot verify eligibility. Independent sampled
presenter evidence in Bridged can supply hybrid/conflicting/unknown, with further
channel coverage required. English query/title/englishOnly filters do not create
language claims. Original audio evidence differs from generated or translated
subtitle tracks; unknown track origin remains unknown. No subtitle URL is fetched.

Provider daily rows remain auxiliary in provider_evidence, never channel_observations
or approved statistical_history. Negative/rebounding counts, gaps, partial windows,
all-zero video fields, implausible counts, stale series and timestamp disagreement
are flagged without repair. Current provider counts cannot backfill publication size
or V(30). Own prospective official captures retain the Phase 1/2 history contract.

Discovery manifests retain query/mode/filters/version/rank/limit/coverage/has_more/
result ceiling and selected-provider totals. Neither zero results nor totalResults
establishes population size or demand. Viral feeds cannot become F19 denominators.
Suggested low-view/zero-subscriber records remain candidates requiring hydration.
Similarity seed/depth/rank/scores persist; canonical IDs dedup across seeds. Similarity
is neither audience overlap nor measured causal performance, impressions or CTR.

Separate policy classes: raw response 900s; transcript/comment text 3600s; normalized
public/provider-history/provider-annotation evidence 86400s; independent supplied
reviews follow Phase 2 annotation rules; input-dependent derived records retain the
existing permission/expiry gate; private/restricted classes remain disabled.
All NexLev permission states are contract_review_required. These conservative local
TTLs do not grant storage rights; extended NexLev history is not enabled. Text cache
expiry leaves permitted observation metadata/hash until its own expiry. Explicit
history purge removes expired provider runs/evidence/sources and dependent conflicts.
Startup never runs retention maintenance or migrations.
