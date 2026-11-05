# Phase 8 release-candidate handoff - 2026-10-03

Project: C:/Users/hp/Documents/ChatGPT/Develpment/YouTubeNicheFinderMCP. Branch: codex/phase-8. Phases 0-7 remain preserved verbatim below this handoff. Phase 8 is integration/release hardening only; no research methodology or migration was introduced.

## Release identity and stop boundary

- Verified starting SHA: 61305079c14f3196e1b28a517079f9bad7e29820, phase-7-verified, version 0.8.0.
- Phase 8 implementation checkpoint: 1b16a50af0ddc52e2f85105bc7f4cee91701139e.
- Candidate version: 0.9.0, retaining the minor-per-phase convention; this is not stable 1.0.0. Schema v7, 36 tables, 15 registered/planned public tools.
- Final source SHA: resolve immutable phase-8-verified; exact final_head/tag_sha are recorded in C:/Users/hp/Documents/ChatGPT/Develpment/YouTubeNicheFinderMCP-phase8-backup-manifest.json. A file cannot contain the SHA of its own containing commit; the external manifest is authoritative.
- Bundle: C:/Users/hp/Documents/ChatGPT/Develpment/YouTubeNicheFinderMCP-phase8.bundle. External manifest records its exact byte count, SHA-256, Git/bundle checks, isolated cold path and test totals.
- Classification: release_candidate_with_live_provider_gap, conditional on that final manifest recording complete=true and ok=true. Missing credentials are an unverified-live gap, not an authentication failure or a fabricated live pass.
- Global MCP host installation: NOT INSTALLED. Scheduler, automatic startup/collection and remote deployment: ABSENT. Watches store intent and do not execute recurring work. Phase 8 stops after the verified release backup.

## Integrity and validation evidence

Before edits: clean exact Phase 7 HEAD/tag, 18 captured preflight checks, 818 full tests, Ruff/imports/schema/integrity/CLI/in-memory/stdio and previous bundle checks. The release contract was written before implementation. Ordered gates: offline acceptance, internal local security/privacy review, official provider/policy refresh, skipped controlled live gate, real-query stored diagnostic, post-validation regression and backup.

Offline Phase 8 acceptance: 48 checks pass; full suite 859 passed (818 previous + 41 Phase 8); three stdio tests include actual calls to all 15 tools. Clean migration and every v1-v6 to v7, repeat migration, model examples, package health and frozen guards pass. Subsequent post-validation: 139 affected provider/security/release tests and 121 public/envelope tests pass; those counts overlap and are not added to the full-suite count. Ten final readiness checks pass after runtime recovery. Exact final tagged source receives another full suite and 21 cold-backup checks; trust the external complete/ok receipt rather than assuming an incomplete restore passed. First-attempt failures/diagnostic corrections remain captured, not erased.

C01-C93, F1-F23, F17 sorting-only, F18 robustness/confidence, cohorts/eligibility/known-at-time/trust and recommendation states are frozen. Phase 8 guard verifies 178 original files, exact seven original research-file bytes, all original DB/migration source and historical reports/tests, nine prior tags and nine previous bundles. Existing Phase 7 guard also passes (147 files). Only three old test assertions change phase metadata from seven to eight. No formula change was used to make a fixture pass.

## Current external contracts and live gap

Official Google/YouTube API, quota, subscriber/view/publication/catalog/Shorts/live semantics and terms/storage/derived/monetization/disclosure sources were checked on 2026-10-03 after the offline/security gates. Eight implemented read routes remain valid; no cost/runtime change was required. Accepted analytics amendments and source-specific permission remain separate from keys; app acceptance was not established. Meaningful realistic synthetic/altered content and main-focus generated music are current production-review context, not an automatic eligibility verdict. Source URLs, exposed revision dates and prior/current/impact tables are in youtube-api-contract-release.md and youtube-policy-contract-release.md.

NexLev official REST/auth/quota/content/search/similarity/analytics/niche-analysis and MCP-context pages were refreshed. Seventeen implemented entries remain valid; zero newly enabled/deprecated implemented routes or observed cost changes. Former semantic/filter/faceless/viral/latest/suggested/daily/classifier/monetization routes retain orchestrator_only/external-context status; incomplete catalog search remains contract_unknown. Additional documented operations remain outside the narrow allowlist. No reverse engineering or remote MCP OAuth. Details: nexlev-api-contract-release.md.

Both process keys were absent. YouTube: skipped_not_configured, zero live requests, zero documented/locally charged quota. NexLev: same. Account remaining quotas are unknown. No .env/alternate secrets, OAuth or source permission was loaded/created. phase-8-live-call-receipt.json contains calls=[] and distinguishes synthetic mocks from real requests.

Real neutral query: industrial history documentary, requested Quick, no refresh. Actual stored discover/research returned insufficient_evidence; observed/eligible channels=0, videos=0, reviews=0, mature historical observations=0, research_id=null. Target 15-25 channels/100-250 videos was not fabricated. Dependent focused/history/compare/competitor calls and new watch creation could not run without real IDs/targets; watch lists were empty. Full live end-to-end niche validation remains unverified. Default immutable evidence/watch/quota counts stayed zero and integrity/FKs passed. Synthetic four-channel/24-video all-15 integration and 25-channel/250-video ceiling tests are separate evidence.

## Integration fixes, UX and performance

- Both provider keys and authorization/token strings redact in JSON stderr logs; exceptions emit type only, not raw payload/private traceback. Stdout remains MCP protocol.
- Generic query/boundary lookup excludes capacity-specific runs; public output omits creator capacity IDs/hours/budget/skills/team. Explicit trusted local profile fit stays separate from canonical niche evidence.
- Oversized responses compact details first, retain primary IDs/states/F18, and declare omissions. Actual SDK text carries a short summary, with structured output authoritative. PublicResult budget is 116000 UTF-8 bytes, reserving room within the 120000-byte MCP/JSON-RPC ceiling.
- All-15 final stdio result sizes were 1623-66750 bytes. Ten-run comparison retained ten IDs/F18 (74094 bytes); ten-competitor comparison retained every target (29989 bytes); outlier pages were disjoint 20+4. Watch projection/lifecycle/reopen retains all 100 permitted targets and disables release-test watches.
- Fixed actionable busy/unavailable storage errors, future-migration exception ordering and pre-SDK input limit (128000 bytes). Historical Phase 3 formula CLI retains public_tools=0 with explicit internal scope and registered_public_tools=15.

Measured synthetic ordinary projections: 0.006-1.28 seconds; Standard synthesis about 5.15 seconds, Quick about 1.30; ten-run compare about 2.40. The 25/250 ceiling took about 9.56 seconds fixture+synthesis and 6.58 projection, 47176 bytes, 16026 validation/read SQL statements. Load varies; these are not live/universal guarantees. Future batching is deferred; Deep production scale/live latency remain unverified. Exact timing/query/byte rows: phase-8-performance.json. Tool UX findings and parameter/description/default reviews: phase-8-ux-review.md and all-15 schema-validated examples.

## Security, retention and recovery

Internal release security review only, not a formal external audit. All 15 strict tool inputs receive bounded adversarial tests (225 malformed cases), query/prompt/SQL-like data remains data, and public inputs offer no arbitrary file/SQL/shell execution. Fixed allowlisted HTTP routes, header secrets, disabled redirects/proxy inheritance and bounded retries remain. Both-provider 401/403/429/503/timeout/network drills preserve retained research identity, correct missing evidence/state, sanitized warnings and local attempted quota. Existing partial-hydration/conflict/private/hidden/history/permission tests remain.

A/B watch lookup/update/disable isolation passes, including reopen. owner_context is a trusted local namespace, not authentication; explicit research IDs and DB access assume one trusted owner. Use separate DB/process per owner and filesystem protection for private data/backups. Generic capacity details do not leak into canonical results.

Frozen retention: source-scoped approvals/clocks/dependent expiry; YouTube default <=30 days, accepted statistics/derived archives <=36 calendar months, raw metadata/text under short permission rules; NexLev raw 15 minutes/text one hour/normalized history 24 hours with contract_review_required. Raw comments/transcripts never become permanent analysis text or public output. Existing expiry/purge/revocation tests pass. Maintenance is manual via history purge-expired for every selected DB and applicable backup. Backups do not extend rights. No off-device backup or automatic purge/collection.

SQLite administrative backup uses read-only source and exclusive new destination, consistent WAL snapshot, explicit connection closure, integrity/FKs and 36 tables. Scratch restore preserves representative analyses/annotations/watches; rollback/checksum/future-schema/busy/query-only/corrupt/pending tests preserve source. Source Git bundle excludes databases/secrets/runtime; research DB requires separate protected backup. Cold restore proves imports from new checkout, exact HEAD/tag, all tests/all-15 stdio, Ruff/guards/docs, migrations/CLI/schema/fsck/clean tree; dependencies are reused locally, not freshly fetched.

44 locked distributions match; pip check passes. Targeted official maintainer review compared 14 advisories; installed pins include selected fixes; no package upgrades. Not an exhaustive CVE/SBOM audit. Current docs/examples/profiles pass strict UTF-8; repaired typography-only mojibake in three current docs, preserved five frozen Phase 7 report occurrences. The app-bundled Python/shell vanished during finalization; a publisher-checksummed same-version Python 3.12.14 restored only ignored .venv/runtime/python, retaining all pins. Evidence: phase-8-runtime-recovery.json. No global runtime install.

## Explicit installation readiness and limitations

README/release-installation.md describe local venv/lock installation, optional process keys, migration, offline verify, stdio start and all-15 discovery/research examples. mcp-config.release.example.json supplies schema-checked stored_only/official_youtube/hybrid absolute-path profiles with placeholders; none was installed. release-recovery.md covers missing/damaged/wrong-schema DB, key/quota/provider/watch/migration failures, protected DB backup, source bundle recovery and prior-tag rollback. Authoritative limitations are in phase-8-verification.md.

Research evidence is not guaranteed success; thresholds are conventions, search is not census, historical coverage may be immature, public/private metrics differ, NexLev is optional/provider-derived and policies may change. Other OS/Python/fresh network installations, formal external security audit, off-device backup and live providers are unverified. An empty DB needs compatible reviewed evidence and advanced measurement/frame/rubric/source-permission inputs; installation alone does not create research evidence.

Once the final manifest passes, the candidate is ready for an explicit user-authorized trusted local stored-only host installation. Required next instruction: name the intended MCP host and select stored_only, official_youtube or hybrid; for live profiles supply keys through process-secret configuration and establish actual source permissions, then perform controlled smoke before live research. No host change or collection begins until that separate request. Phase 8 ends here.

---

# YouTubeNicheFinderMCP — Phase 7 handoff

Phase 7 public surface is functionally complete locally: package 0.8.0, schema v7, 36 tables, exactly 15 registered/15 planned tools. Starting verified SHA: 8ce01aa05b1c56be93305fc57672d8fb792e35be (phase-6-verified). All frozen Phase 0–6 methodology, equations, retention/firewall, recommendation states and source documents remain preserved.

Contracts: docs/phase-7-tool-contract.md (defined before registration), docs/phase-7-schemas.json, docs/phase-7-tool-reference.md (all fields/provider/errors/examples/limits), docs/phase-7-workflows.md (all 15 chaining examples). Inputs use a typed request envelope. Outputs retain immutable run IDs, canonical dimensions, recommendation states, F18 scope/components/agreement, supports/concerns/unknowns, quota/capabilities/provenance. Default F17 is disabled; explicit sorting cannot change recommendations/confidence. Creator fit is separate. Focused history displays canonical availability and never reconstructs past counts.

Tools: youtube_niche_research, youtube_niche_discover, youtube_niche_compare, youtube_niche_outliers, youtube_niche_content_gaps, youtube_niche_packaging, youtube_niche_audience_demand, youtube_niche_sustainability, youtube_niche_risk, youtube_niche_geo_language, youtube_niche_watchlist, youtube_niche_history, youtube_competitor_analyze, youtube_competitor_compare, youtube_competitor_watch.

Research can reuse stored decisions or orchestrate eligibility/cohort/core/history/qualitative/decision services with explicit advanced profiles. Quick/Standard/Deep ceilings: 25/250, 50/800, 100/3000 channels/videos; approximate lower targets 15/100, 30/300, 60/1000. Search pages 2/6/20, reviews 25/100/500, sensitivity 8/24/48, similarity depth 1/1/2. Mode does not change formula meaning or guarantee statistical confidence. New retained candidates are sampled deterministically without using outcomes. Missing/weak/excluded candidates are preserved by the frozen constructor. Taxonomy/speech/rights review and permissions are not automatically invented.

Default stored-only calls use existing permitted evidence. Read projections open the DB read-only; tools/startup/status never initialize or migrate. Research/discover/competitor-analyze can explicitly refresh bounded IDs/search/similarity, requiring keys and valid administrative source permissions. No unsupported NexLev semantic REST substitution, private metrics or provider financial scoring. HTTP failures preserve usable stored evidence and recorded quota. YouTube actual charge is unknown; documented assumptions and attempts are reported. NexLev documented/known charged cost is distinct. Automated acceptance/live YouTube/NexLev calls and quota remain 0/0 each.

Schema decision: prior 35 tables could not represent mutable watch preferences without altering immutable evidence. Migration v7 adds only research_watches, owner/type index, timestamps, expiry, enabled flag and optimistic revision. Earlier six checksums are unchanged. Watches manage niche boundaries versus canonical competitor targets; immutable subject identity, local owner namespace (not authentication), default 365-day expiry. No scheduler, last_checked_at null, execution intent_only. Declared country uses existing live_cache for 24-hour permission-checked display context only, never history or audience geography.

Workflows: discover→boundary→research→research_id→focused gaps/history/risk→compare; competitor-analyze/compare shares one optional frozen context; create/read/update/disable watches persists intent only. Host example documents isolated stdio command/cwd/optional env and no-key behavior; no global settings/install/deployment changes.

Acceptance: scripts/acceptance_phase7.py records exact commands/outputs in docs/phase-7-results.json. docs/phase-7-verification.md records totals; scripts/verify_phase7_frozen.py verifies frozen files, prior reports, source bytes and v1–v6 checksums. Full pytest includes every previous regression and Phase 7 synthetic edge fixtures, exact schemas/list, real stdio research/compare/competitor/watch, migrations clean and every prior schema, Ruff/import/CLI/status/DB checks. Synthetic quota tests use MockTransport; no manual live smoke.

Git/backup: branch codex/phase-7; verified tag phase-7-verified identifies final handoff. Implementation SHA and final HEAD/tag SHA, bundle size/SHA-256, cold-restore checks and prior bundle preservation are recorded exactly in ../YouTubeNicheFinderMCP-phase7-backup-manifest.json. Bundle: ../YouTubeNicheFinderMCP-phase7.bundle. The external manifest avoids an impossible self-referential tracked commit hash. Earlier bundles remain preserved.

Remaining scope requires a new request: final integration/live smoke/release hardening only. Current policy/API contracts, controlled YouTube and optional NexLev smoke, quota verification, end-to-end real niche research, tool UX/performance, failure/recovery drill, privacy/security, production config, optional host installation and release candidate backup. STOP after Phase 7; none of that scope is started here.

Implementation checkpoint: `ad174f832683fc2e312e8ef335f08d70b1699b28` (feat: expose fifteen Phase 7 research MCP tools). The final verification/handoff commit is identified by the external manifest and verified tag.

Final offline acceptance: 818/818 tests pass (738 previous + 80 Phase 7); all 63 acceptance checks pass; isolated public suite 80/80; Ruff check/format, 103 imports, 42 schemas, real stdio four calls, all prior migration paths and SQLite integrity pass. Frozen guard verifies 147 prior files and six unchanged migration checksums. Exact evidence: docs/phase-7-results.json and docs/phase-7-verification.md.

## Preserved standalone Phase 0–6 state (original Git bytes follow)

# YouTubeNicheFinderMCP — standalone Phase 6 handoff

Updated 2026-10-03 (Asia/Karachi). Phase 6 COMPLETE AND VERIFIED after the checks
recorded below. STOP before Phase 7. This current section supersedes the earlier
phase deferrals/stop statements; the complete original Phase 0–5 archive follows
without changes.

Repository: C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP.
Branch: codex/phase-6. Package 0.7.0; schema v6, 35 tables, no new migration/table.
Implemented internally: F1–F23 and failure floor, with optional F17 sorting only,
F18 robustness/confidence and separate multi-axis research synthesis.
Public research tools: 0 registered / 15 planned. No global installation/deployment.
Live YouTube calls/quota: 0/0. Live NexLev calls/quota: 0/0.

## Checkpoints and preserved contracts

Starting HEAD and phase-5-verified: 99c90d6dec642b74ce4942130d1e4fe18ec35009.
Initial tree clean on codex/phase-5; preflight verified 647 tests, Ruff, CLI/DB,
in-memory/real stdio MCP, Git fsck and prior bundle before tracked changes.
Exact evidence: docs/phase-6-preflight.json. The Phase 6 contract was written before
production implementation. All seven authoritative specifications were re-read,
with the latest third-pass sorting-only override applied; C01–C93/F1–F23 equations
are unaltered. research_specs remains byte-identical.

scripts/verify_phase6_frozen.py checks research bytes, all Phase 3/4 equations,
all qualitative modules, migration SQL/checksums v1–v6 and earlier reports/contracts/
runners against the verified Phase 5 checkpoint. Shared analysis models/repository
only add typed Phase 6 run manifests and retained replay integration.
Version 0.7.0 follows the established minor feature increment; dependencies are unchanged.

Implementation checkpoint: cce8950805906d960278524beec59b3105102740.
Final documentation checkpoint/tag: phase-6-verified, resolving to final HEAD;
exact final SHA is in the external backup manifest (avoids a self-referential commit).
Parent backup: YouTubeNicheFinderMCP-phase6.bundle and
YouTubeNicheFinderMCP-phase6-backup-manifest.json. Earlier bundles are preserved.
The manifest records final/tag/implementation SHA, size/SHA-256 and exact cold-restore
checks. Source-only backup; no database, credentials, venv or off-device copy claimed.

## F18, evidence quality and separate coverage

F18 = consistent comparable predeclared specifications / comparable specifications,
with planned/unavailable/omitted specifications and flips exposed. No denominator
means null. The separate high/medium/low rubric follows coverage, classifications,
source agreement, history maturity, independence, route diversity, policy freshness,
critical reviews and sensitivity. Neither output is success probability,
a statistical confidence interval, calibrated model confidence or a forecast.
Reliable negative conclusions can have high confidence.

Coverage counts scoped unique channel/video/topic subjects and declared review
populations, never raw rows. Coverage, quality and agreement remain separate.
Faceless/language/live/membership/continuity/ownership claims retain verified,
provider-only and conflicted subjects/provenance. Audio metadata is a language lead,
not verified speech. Production/source/rights/policy/factual/premise/comment reviews
retain sample manifests, material/source types and scoped-video intersections.
One reviewed asset/case cannot imply complete video/channel coverage. Comments retain
videos, counts per capture, route/order/date and overlap limitations.
History exposes mature/pending/unknown age outcomes, required states and underlying
F10–F13/F20/F21 panel/interval details. Provider history cannot fabricate observations.
Field-level official/provider/human/model/creator disagreements stay visible;
financial/monetization/proprietary values are excluded, never averaged into decisions.
Policy snapshots carry version/scope/retrieval/refresh; absent/stale =>
policy_refresh_required. Clock receipts cannot revive expired content. No live browse.

## Robustness and immutable sensitivities

Quick <=8, standard <=24, deep <=48, predeclared one-at-a-time runs; no Cartesian
explosion. Saved variants retain parent/base, changed family/option, input identity,
source context, comparison version, frozen discovery fingerprints and bounded expiry.
Base runs/cohorts remain immutable. Cached reads recheck retained ancestry,
permissions, revocation and discovery integrity. Replay is deterministic.

Families: all/official/NexLev/winner-excluded/weak-excluded/semantic-excluded routes
and deep individual routes; T1–T3/classification/similarity provider ablations;
6/8/10m, 50/100k and supplied goal variants; broad/practical/narrow boundaries;
F22 finite-frame missingness; documented versus provisional ownership; alternate
seed/reduced/expanded qualitative samples. Route overlap never multiplies entities;
weak cases, omissions, page/cap scope and winner bias remain visible. Provider
ablation removes dependent qualitative reviews; inadequate replacement evidence is
insufficient_without_provider. Missing alternative cohorts stay explicit.
Alternative recruitment/context must be compatible and frozen before declared time.
Known-group F21 winner-set diagnostics preserve unknown per-winner entrant evidence;
canonical historical metrics stay unchanged. Qualitative samples retain manifests.
Material shifts use declared rule flips/tolerances or axis/state changes. No unknown
views, ownership, failed outcomes or classifications are imputed.
The matrix reports every declared family's tested/stable/sensitive/unavailable state,
with each axis, history and source dimension separately visible.

## F17 sorting firewall and synthesis

F17 disabled by default; explicit versioned weights and external low/high benchmarks
normalize allowed canonical numeric values, clamp to [0,1], invert lower-is-better,
and compute 100 times the disclosed included weighted mean. Raw/norm/clipping/
weights/directions/missingness remain exposed. Missing essentials =>
insufficient_dimensions; caller-approved optional omissions => partial_index;
complete => sorting_index_available. No RPM/revenue/monetization/opaque T4 input.
F17 executes after synthesis/confidence and cannot approve/reject or override either.

Separate axes: performance, ordinary floor, repeatability, entrant accessibility,
breadth, concentration, momentum/history, differentiation, depth, production,
sources, rights, platform policy, factual burden and pilot downside.
Caller-versioned goal rules supply numeric judgments; ungraded/unknown stays explicit.
States: supported, supported_with_caveats, mixed_evidence, weak_under_goal,
insufficient_evidence, high_execution_burden, high_rights_or_policy_dependency,
history_immature. Critical unknown axes/classifications gate support. Rights/policy/
factual risks block unqualified positivity and preserve underlying insufficiency.
Immature history remains distinct. CreatorCapacity compatibility is a separate
creator_fit receipt and never changes canonical metrics, generic state or F18.
Evidence supports further consideration under tested assumptions, not creator success.

## Verification and internal interfaces

738 tests passed; 91 Phase 6 adversarial tests.
65/65 acceptance checks passed, including final quality rechecks;
exact commands/exits/stdout/stderr are in docs/phase-6-results.json.
R1–R15 include weak coverage, robust positive/negative evidence, weak-route/threshold/
boundary/missingness sensitivity, immature history, source conflicts, production/
rights burdens, separate creator fits, sorting firewall and stale policy.
Cross-phase analytics/history/qualitative/NexLev/permission/retention regressions,
clean/every-prior-schema migration, integrity, imports, Ruff check/format, in-memory
and real stdio MCP, no-network and deterministic replay pass.
Cold restore runs the full final tests, Ruff, imports proved under restored src,
CLI/MCP, frozen artifacts, tag/HEAD/fsck and clean tree checks; exact results are
retained externally in the backup manifest. Previous bundle hashes are preserved.

Internal CLI: decision run --options <JSON>, decision inspect <run-id>,
decision f17-config; comparisons are included in inspect. Strict DecisionOptions
requires base, cutoff/age/tolerance/goal, caller rubric and sensitivity plan;
retained history/qualitative IDs, policy inputs, creator and F17 are optional.
Status/verify reports Phase 6 and 33 validated schemas, with 0 research tools.
Guides: docs/phase-6-decision-contract.md, phase-6-robustness.md,
phase-6-sensitivity.md, phase-6-decision-synthesis.md, phase-6-analytics.md,
phase-6-qualitative.md and phase-6-verification.md.

## Exact Phase 7 scope — not implemented here

Implement/register these 15 public research tools using the verified internal engines:

1. youtube_niche_research
2. youtube_niche_discover
3. youtube_niche_compare
4. youtube_niche_outliers
5. youtube_niche_content_gaps
6. youtube_niche_packaging
7. youtube_niche_audience_demand
8. youtube_niche_sustainability
9. youtube_niche_risk
10. youtube_niche_geo_language
11. youtube_niche_watchlist
12. youtube_niche_history
13. youtube_competitor_analyze
14. youtube_competitor_compare
15. youtube_competitor_watch

Do not continue Phase 7 or deploy globally without a new user request.

---

## Preserved complete Phase 0–5 standalone handoff

# YouTubeNicheFinderMCP — standalone Phase 5 handoff

Updated 2026-10-02 (Asia/Karachi). **Phase 5 COMPLETE AND VERIFIED. STOP before Phase 6.**
Version **0.6.0**, schema **6**, **35 tables**, **13 frozen eligibility rules**,
**647 tests**, **128 Phase-5 tests**, **58/58 acceptance checks** (54 runner checks
plus four final permission-clock/full-suite/Ruff rechecks), **0 research tools / 15 planned**.
Repository: C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP.
Branch: **codex/phase-5**. Local Python stdio MCP. No host/global install or publishing.
Implemented internally: **F1–F16, failure floor, F19–F23**.
**F17, F18, final ranking/recommendation/confidence and public research tools remain absent.**
The complete Phase 0–4 handoffs follow this current section without loss of substance;
this Phase-5 section supersedes their current-status, deferral and stop statements.

## Verified checkpoint and authoritative research

Starting HEAD / phase-4-verified: **b53e5bfacf33ce581f3f7ba7e5eaeaee990f5486**.
Initial codex/phase-4 tree clean; fsck, Phase-4 bundle presence, all 519 tests,
Ruff check/format, CLI verify, schema5 DB status/integrity, in-memory and real stdio
passed before modification. Exact outputs: docs/phase-5-preflight.json.
All seven authoritative research documents were re-read for F14–F16, C36/C37,
content gaps, packaging/series, production/source/rights/factual burden and C93/F23.
Research original byte hashes remain unchanged in docs/research-files-read.json.
The qualitative contract was written before production implementation.

Frozen research, all prior phase reports/contracts/runners, Phase-3/4 equation modules
and v1–v5 SQL/checksums pass scripts/verify_phase5_frozen.py. Analysis models/repository
only gain Phase-5 option/retention integration; frozen equations are untouched.
Version 0.6.0 follows the established minor feature increment from 0.5.0.
Schema v6 adds only **qualitative_annotations**, with an UPDATE prohibition and expiry
index. Checksum **80c2b3747e424560ade285b19375634144e1510b1a2e8295c28f86aee2ed7d50**.
No duplicate content-gap, production or pilot tables. Existing sources/provider records,
permissions, taxonomy, analysis_runs/results/outcomes are reused. Configured DB explicitly
upgraded with migration [6]. Startup/inspection/verify never migrate.

## Phase 5 calculations and evidence axes

**F14:** same-capture official exact public likes/comments per 1,000 observed views,
selected at the shared publication-age/window gate. Missing fields and zero denominator
remain unknown; contemporaneous numerator/denominator/provenance stay visible.
Per-channel medians and preferred 20-video coverage flag are descriptive. Comment themes
retain video/route/order/pages/sample/retrieval/reply/deleted/disabled/source provenance,
never representative sentiment/satisfaction/demand percentages or raw comment bodies.

**F15:** validated distinct premises / generated candidates. A human-reviewed viable
premise has entity, promise, mechanism, long-form treatment, checked credible accessible
sources, production path and known in-boundary taxonomy family/premise nodes. Canonical
same/near duplicates merge, not title rewrites. Uncertain/conflicting relations suppress
precise values. Distinct topic/mechanism relations, source support, unsupported inventory,
classification coverage, finite/recurring entities and continuation depth are explicit.
Ten human reviews and every finalist are exposed research review targets; 30 candidates
is an example budget. Completely unreviewed inventory is unknown, not zero.

**Content gaps:** positive demand + inadequate reviewed supply + differentiated feasible
sourced production are required for supported_gap. Comments-only/model/provider evidence
can support possible_gap, never confirmation alone. Served supply is saturated; absent
or missing demand/supply/differentiation produces explicit insufficient states. Content,
packaging and production gap scopes are distinct; no final opportunity judgment.

**Saturation/packaging:** canonical similar premise pairs and publication chronology can
link to retained prior observed outcomes, each with original age/cutoff/goal/source run.
No copying intent or causal imitation claim. Title mechanisms/length/promise and reviewed
thumbnail face/asset/text density/composition/emotional device remain public patterns.
Small title parser recognizes question punctuation and numeric text; other mechanisms
require review. T4 similarity is descriptive homogeneity, never CTR.

**Series:** series_continuation_structure uses reviewed compatible premise links,
entity/chronology/geography/category/how-it-worked/rise-fall/comparison/investigation paths,
finite/exhaustible concerns and finite graph depth. Iterative traversal supports the
maximum 500-item budget; cycles never imply infinite ideas. Playlists do not prove bingeing.

**F16:** task hours and cash are separate for research, sourcing/fact-check, script,
visuals, rights, editing/animation, narration, expertise, updates and revisions/overhead.
Every task has evidence, reason and local confidence. Timed pilot and three contrasting
estimates are preferred and coverage flagged. Cases/currencies are not silently averaged.
Optional creator capacity declares hours/week, monthly cash/currency/cadence, skills,
narration/animation/footage/team. Capacity = hours/week / hours/release before additional
overhead (24/12=2). Required capabilities/team/skills are checked. Monthly cadence cost
uses the explicit annualized 52/12 convention. Missing profile/constraints remain unknown.
Compatibility never changes burden and is not a niche go/no-go recommendation.

**Faceless/source:** reviewed maps, diagrams, archive, documents, stock, screen/data,
animation, original graphics and narration paths show host/field/interview constraints.
Feasibility stays separate from production expense and frozen Phase-2 eligibility.
Checked source accessibility/credibility/primary-secondary/category/freshness and shared
source-family dependence are visible. Fragility requires a declared review; one source
family alone does not assert fragility. Unchecked availability is unknown; pages are not
quality. Source-supported premise yield is distinct from quantitative performance.

**Risk:** rights/legal, platform-policy and factual/editorial axes are separate. Asset
clearance/dependency/verified license references yield low apparent dependency, moderate
clearance burden, high clearance dependency or uncertain. No safe duration or legal
conclusion. Current official YouTube monetization, GenAI disclosure, advertiser and
fair-use guidance was opened on 2026-10-02; docs/youtube-policy-contract-phase5.md records
URLs/version/scope/internal refresh. Policy snapshots expire, with review flags only,
never automatic approval/violation or revenue predictions. Factual evidence records
verification/dispute/source/correction/current-event burden, not allegations or safe niches.

**C93/F23:** optional declared setup + release task + evaluation/overhead hours and
setup + variable release + contracted overhead cash. No income, RPM/CPM/public-view ROI
conversion. Dated outflows (explicit cash dates, otherwise delayed publication) show peak
no-income deficit and cash/hour limits. First maturity >=first publication+age; complete K
>=last publication+age. Research example: 400 cash, 50 hours before monitoring/revisions,
300 budget exceeded, weekly five-release age30 gives day30 first/day58 complete.
F7 future five after anchor, F19 ten entrant attempts, F10–F13 repeated snapshots,
F20 pre/post history and F21 comparable windows remain explicit unresolved prerequisites.
Runway is neither a success forecast nor synthetic history.

## Annotation, reproducibility and lifecycle

Strict typed payloads separate deterministic parser/provider/model/image/human/creator
sources. Each immutable annotation has reviewer/system/rubric/model/prompt versions,
reviewed materials/sample/timestamps, known decision/availability, confidence, rationale,
limitations, boundary/taxonomy, input ancestry and finite expiry. No hidden chain of
thought or raw transcript/comment/media archive. Model review requires model/prompt
versions. Provider similarity stays T4; financial/monetization/quality/opaque fields are
rejected. contract_review_required text cannot be relabelled to evade the firewall;
permitted text derivations respect material TTL and source-specific verified permission.
Verification/availability clocks prevent later permission from entering a past review.

Seeded hash samples retain declared population/sample IDs, method, budget, seed,
cutoff/reason/coverage; declared human samples are separately attributed. Budget is
1–500 per run; inventories are bounded. No full media analysis for every video or heavy
ML dependency. Public comment/packaging reviews belong to the frozen video frame.
Prior Phase-3/4 runs are read-only, boundary/cutoff/retention checked (max20 references).
Immutable manifests/results reuse existing tables; dependency expiry bounds derivatives.
Revoked/deleted/expired inputs block both annotation and saved-run reads. Explicit purge
deletes expired reviews and runs; it is separate from cache expiry. Later evidence makes
new annotation IDs and run identities. Findings expose dimension/state/value/label,
evidence IDs, coverage, source types, annotation-specific confidence, warnings/limitations,
generation time, boundary/taxonomy and prior run IDs. No F18/global confidence model.

## Usage and exact verification

Use .venv/Scripts/python.exe -m youtube_niche_mcp analysis annotate --input annotation.json;
analysis qualitative --cohort ID --video-cohort ID --options options.json;
analysis inspect RUN_ID. Internal APIs: QualitativeService.annotate/analyze/inspect and
separate engagement/ideas/gaps/packaging/series/production/risk/pilot functions.
No public research tools are registered. MCP status exposes qualitative/production/risk
availability. Source/model/pilot examples: tests/phase5_helpers.py and qualitative tests.

Exact acceptance command/stdout/stderr/exit records: docs/phase-5-results.json;
summary: docs/phase-5-verification.md. Full647; Phase5=128; Phase3 analytics109;
Phase4 historical102; NexLev51; retention39; realstdio1. Ruff check and160-file format
check pass, import sweep80 modules and29 JSON schemas pass. Clean and every v1–v5-to-v6
migration, rollback, idempotence and integrity pass. Q1–Q15 are deterministic synthetic
fixtures, not platform findings. Normal tests block live HTTP and need no keys.
**Live YouTube calls/quota 0/0; live NexLev calls/quota 0/0.** Development browsing was
only current official policy documentation. No private competitor metric inference.
Corrections before checkpoint: SQLite row mapping after lint automation, iterative graph
traversal at maximum budget and explicit permission-known clocks/provider text gate.

## Git checkpoint and source backup

Implementation checkpoint: **105f8fb2295385aba9dab00f4fa520b48b709931** (filled after implementation commit).
Verified tag: **phase-5-verified**, on the final enclosing documentation commit.
Final HEAD is resolved by that tag and recorded exactly in the external manifest; a
file cannot contain the SHA/hash of its own enclosing commit/bundle without circularity.
New bundle: C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP-phase5.bundle.
External authoritative final SHA/tag/implementation SHA/size/SHA256/exact cold-restore
outputs: C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP-phase5-backup-manifest.json.
All earlier phase bundles/manifests remain untouched. This source backup includes no
keys, real DB, cache, retained raw text/media or venv. No off-device copy is claimed.
Final completion requires bundle verify, fsck, clean tree and cold restore; the external
manifest records the outcomes and restored source import location using the verified venv.

## Exact next phase — not started

Phase6 later: F18 robustness/confidence, evidence coverage, route/threshold/boundary/
missingness sensitivity, provider disagreement, history maturity, multi-axis decision
synthesis, optional F17 sorting-only index and recommendation confidence. F17/F18, final
recommendation layer and all15 public tools remain unimplemented here. STOP after Phase5.

---
# Preserved Phase 0-4 handoffs (historical; superseded current status)

# YouTubeNicheFinderMCP — standalone Phase 4 handoff

Updated 2026-10-02 (Asia/Karachi). **Phase 4 COMPLETE AND VERIFIED. STOP before Phase 5.**
Version **0.5.0**, schema **5**, **34 tables**, **13 frozen eligibility rules**,
**519 tests**, **102 historical tests**, **52/52 acceptance**,
**0 registered research tools / 15 planned**. Repository:
C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP;
branch **codex/phase-4**; local Python stdio MCP; no host/global installation.
Implemented **F1–F13, failure floor, F19–F22** internally.
**F14–F18 and F23 remain unimplemented**, as do final confidence, production,
content-gap/risk/recommendation engines and public research tools.
The complete Phase 0–3 handoffs follow this current section unchanged in substance;
this section supersedes their older current-status/deferral/stop statements.

## Verified start and frozen history

Starting HEAD and phase-3-verified tag:
**a1f50f3f442af4a2847a3beb72d6da3897993a2a**. Initial codex/phase-3 tree clean.
Preflight fsck exit0 (three existing harmless dangling blobs), Phase3 bundle present,
417 tests, Ruff, CLI verify, DB status/integrity, in-memory and realstdio all passed.
Exact outputs and frozen blob identities: docs/phase-4-preflight.json. No unexpected
work was discarded. The Phase4 branch was created after all preflight checks.

All seven authoritative research files were re-read for F10–F13, C26/C28/C29,
C71/C74/C76, C91/F20, C92/F21, known-time integrity and prospective history.
Their original hashes remain unchanged in docs/research-files-read.json and the
historical sections below. Phase3 reports/runners/contracts, v1–v5 migrations and
F1–F9/floor/F19/F22 equation files remain Git-blob-identical to phase-3-verified.
**docs/phase-4-formula-contract.md was written before production implementation.**

## Exact Phase 4 calculations

F10 uses successive actual exact official counts: delta views / actual elapsed
hours. Each video has point IDs, observed/available clocks, metric ages, values,
raw delta/duration, named views/hour unit and retained source semantics. Sort
out-of-order captures; collapse compatible timestamp duplicates; conflicting
counts/regimes return source_conflict. Negative corrections remain flagged.
Two points give velocity; three give acceleration **r_later−r_earlier**, in
views/hour; no second time division or inference from one interval. Irregular
intervals remain explicit; no current lifetime views / age proxy or interpolation.
Distinct video rates are not collapsed into a single unnamed velocity.

F11 is **median(channel medians V(a))_new / median(channel medians V(a))_old**
for explicit half-open publication windows at matched age/tolerance, boundary,
eligibility/topic/measurement definitions. Report both aggregates, absolute and
relative change, video-weighted companion, matched-repeat-channel companion,
videos/channels/documented independent groups, classification coverage, pending
and unknown. A prolific channel cannot dominate the channel-balanced aggregate.
It describes observed cohorts, not future niche growth.

F12 reports distinct **observed eligible videos, active channels, verified entrants
and per-channel upload/day distributions** separately. Each named change uses
(new-old)/old; the primary active-channel change follows Blueprint F12. Actual
stored discovery occurrences must be known by the historical cutoff. Search totals
are not denominators or censuses. Stable protocol hashes include route/provider,
query/filter sets, locale/language/order, page/result budgets, eligibility/boundary,
collection/source versions and capability mode; irrelevant timestamps/run IDs are
excluded. Changed protocol => unstable_discovery_protocol. Documented index or
coverage epoch expansion => coverage_not_comparable. Incomplete pages => disclosed
partial_coverage. A later discovery cannot be backdated from an old publication.

F13 freezes the pre-existing catalog at interval start, with explicit old threshold
**>=90 days** and **>=30 days actual tracking**. **Sum observed old-view increments /
sum all scoped observed increments**; preserve older/pre-existing-younger/new-release
increments/counts/shares and endpoint IDs. No lifetime totals or assumed zero at
publication. New releases use first actual capture to endpoint and disclose shorter
observed exposure as partial. Missing endpoints remain unknown. Negative corrections
remain raw but suppress contribution-share interpretation. Deleted content with
retained valid endpoints stays usable. Schema and metadata retention were not relaxed.

F20/C91 belongs to the floor/follow-up family: verified explicit anchor or first
known age-a goal hit, declared confirmed-hit t0, frozen last k=5/10 pre-anchor
references whose V(a) was already known at t0, and first k eligible publications
**after t0**. Exclude anchor, include all later hits. **(Bpost+1)/(Bpre+1)**, medians
of exact same-age outcomes; also absolute difference, sequences, Q25, goal counts,
pending/unknown and absent upload positions. Source illustration pre median2000,
post4000 => **4001/2001**, not hard-coded2. No valid side => insufficient_history.
Post-t0 publications are not silently substituted with Phase3's post-anchor sequence.
Interpretation is explicitly non-causal; no audience-transfer or algorithm claim.

F21/C92 is three separate creator-group fractions on a stable tracked panel:
**Replacement = |Wnew−Wold|/|Wnew|**;
**Persistence = |Wnew∩Wold|/|Wold|**;
**Verified entrant winner share = |Wnew∩recent observed entrants|/|Wnew|**.
Age/goal/format/boundary/measurement/eligibility/group versions, equal-duration
windows, discovery protocol and creator roster must remain comparable. Each fraction
has its own raw numerator/denominator; zero relevant denominator is undefined.
Source illustration later10/prior12/shared6/entrants3 => .4/.5/.3. Unknown outcome
units and known-only winner sets remain visible; unknown entry contributes bounds,
not an incumbent assumption. First observed niche entry follows frozen Phase2
clocks; an old account can be newly observed in this niche. Unknown ownership is
provisional, not established independence. Coverage/roster expansion cannot pose
as winner churn. Current counts, search rank and provider outlier scores cannot
reconstruct historical winner sets.

## History, retained identity and persistence

OWN_HISTORY, PROVIDER_HISTORY and CURRENT_SNAPSHOT stay distinct. No reconstructed
history. Every required observation and annotation must have been available by its
historical cutoff/freeze and still retained at calculation/replay. Later subscribers,
titles/classifications, index dates, publications and breakout knowledge cannot enter
earlier evidence. Expired raw API metadata is not recovered from statistical archives.
A retained independently supplied chronology Claim(publication_at) may provide an
explicit publication/channel envelope if known at the frozen landmark, with actual
source/evidence/permission provenance; copied API metadata cannot be relabeled as
independent. Conflicting identities stop calculation. Without valid chronology,
history remains unavailable. See docs/phase-4-historical-analytics.md for its exact
input schema and examples.

Provider T2 nexlev.daily_analytics supports only a separate auxiliary diagnostic:
views/hour, subscribers/hour and uploads/hour remain separately named, with gaps,
negative deltas, rebound, stale dates and zero video counts retained. No automatic
repair or canonical pooling. Evidence/source/run 24h expiry remains enforced.
Provider VPH/outlier/RPM/revenue/monetization/geography never substitute for formulas.
The optional explicit provider:nexlev.history snapshot diagnostic is also isolated;
arbitrary proprietary snapshot routes cannot define even this history view.

One history gate uses available, partial_coverage, insufficient_history,
insufficient_same_age_history, insufficient_panel_history, pending_maturity,
source_conflict, policy_permission_required, provider_history_only,
unstable_discovery_protocol and coverage_not_comparable. Pending is not miss;
unknown is not zero. Coverage metadata is not a confidence/recommendation model.

Schema remains **v5/34 tables**: **no new tables or migration**. Existing
analysis_runs, analysis_metric_results and analysis_outcomes store both phases.
HistoricalOptions embeds panels/windows, protocol/run IDs, outcome age/tolerance,
anchor/landmark, thresholds, creator-group version, auxiliary policy, final cutoff,
input observations/annotations and retained permission IDs. Deterministic panel
IDs include windows while invariant protocol signatures compare successive windows.
Discovery run/page/occurrence hashes are frozen in annotation.frozen_discovery;
replay detects later mutation in otherwise mutable discovery-run headers.
Append-only runs/results never rewrite old analyses; later data makes a new run.
Saved reads validate expiry, deletion and policy revocation, including provider and
discovery dependencies. Bulk frame/discovery/provider queries avoid N+1 reads.

## Interfaces and acceptance

Internal HistoricalService.analyze returns the existing AnalysisBundle. CLI:
analysis formulas (lists both versions), analysis historical --cohort ID
--video-cohort ID --options profile.json, analysis inspect RUN_ID. Old Phase3
manifests remain readable and formula results unchanged. No public tools added.

Synthetic H1–H12 histories are indexed in tests/fixtures/phase4_histories.json:
accelerating/decelerating video, positive/flat demand, rising stable supply,
coverage-driven fake supply, durable old catalog, post-hit lift/no lift,
winner replacement/persistence and ambiguous history. They use actual stored
synthetic captures, frozen cohorts, independently supplied chronology and explicit
synthetic administrative permissions, not empirical YouTube observations or actual
configured retention acceptance.

**scripts/acceptance_phase4.py: 52/52 PASS; zero failures.**
Full **519 passed in104.28s**, Phase4 **102 passed in22.34s**,
Phase3 analytics **109 passed in43.75s**, NexLev **51 passed in5.14s**,
retention/history/persistence **39 passed in3.93s**, realstdio **1 passed in3.83s**.
Ruff check/format passed; 138 files at acceptance;71 module
imports;23 JSON schemas; clean/v1/v2/v3/v4-to-v5 and already-v5 latest/idempotent
checks; DB integrity and in-memory MCP passed. Exact commands/outputs:
docs/phase-4-results.json. Known-time, permission/expiry/replay, provider firewall,
non-network and prior pending/unknown/sister-group regressions passed. A600-video
historical panel asserts <=60 SELECTs; the prior3,000-video test also passes.
No fragile timing gate. Version0.5.0 is the next minor feature release; runtime and
installed metadata align. **Live YouTube calls/quota0/0; NexLev calls/quota0/0.**

## Git and recoverable backup

Implementation checkpoint: **442d34010c90afe6af7e269f61279aef6459fd61**.
Final tag: **phase-4-verified**, on the subsequent finalized handoff commit.
New parent backup paths:
C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP-phase4.bundle
C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP-phase4-backup-manifest.json

The external manifest is authoritative for the final enclosing HEAD/tag,
implementation checkpoint, bundle byte size/SHA256, exact bundle/fsck/cold-restore
commands/results and prior bundle preservation. Embedding an enclosing SHA or its
bundle hash in this tracked file would create a circular hash. Cold restore must
prove restored-source imports, CLI verify, formulas and historical/prior formula
regressions, with no live network. Existing verified runtime may be reused; it must
load source from the restored checkout via PYTHONPATH. Earlier bundles/reports are
preserved. See docs/phase-4-verification.md for the acceptance/backup contract.

## Exact remaining Phase 5 scope — do not start now

F14 public engagement descriptors; F15 idea feasibility; F16 production burden/
capacity; C93/F23 pilot downside; content-gap analysis; packaging analysis;
series/binge structure; production/faceless feasibility; rights/policy/factual risk.
F17/F18, final confidence/robustness/recommendations and public research tools also
remain unimplemented in this Phase4 task. **STOP before Phase5.**

---

# Historical Phase 0–3 handoff (superseded current-status sections)

# YouTubeNicheFinderMCP — standalone Phase 3 handoff

Updated 2026-10-02 (Asia/Karachi). **Phase 3 COMPLETE AND VERIFIED. STOP before Phase 4.**
Version **0.4.0**, schema **5**, **34 tables**, **13 frozen eligibility rules**,
**417 tests**, **46/46 acceptance**, **0 registered research tools / 15 planned**.
Repository C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP;
branch codex/phase-3; local Python stdio MCP. No host/global plugin installation.
Implemented **F1–F9, failure floor, F19 and F22** as an internal offline metric bundle.
**F10–F18, F20–F21 and F23 remain unimplemented.** No ranking or recommendation.
The full Phase 0–2.5 handoff is preserved below; this current section supersedes
its phase/version/schema/provider/formula deferrals and stop boundaries.

## Exact starting checkpoint and frozen inputs

Starting HEAD/tag phase-2.5-verified: **5a0437d9621819f921bdd7788470530dca6de5a1**.
Preflight clean codex/phase-2-5, exact tag match, fsck exit0, Phase2.5 bundle present,
307 tests, Ruff check/format, CLI verify/schema4/31 tables/status/integrity and real
stdio passed. Exact commands/output: docs/phase-3-preflight.json. No unexpected
changes were discarded. A codex/phase-3 branch was created only after preflight.
Seven authoritative research specifications remain byte-identical; original hashes
and full historical decisions remain below and docs/research-files-read.json.
All frozen phase0/1/2/2.5 reports and acceptance runners remain unchanged.

Blueprint §28 F1–F9, its baseline/floor/follow-up sections, Matrix sample cautions,
C90+ F19/F22, Third Pass Gap Audit known-time/exposure modifications, both evidence
ledgers and the updated original research prompt were re-read. Formula contract
**docs/phase-3-formula-contract.md was written before analytics implementation**.
Latest C90/explicit Phase3 brief clarify F4 ever-hit/exposure over older repeated-hit
wording. The four peer-anchor raw median 1,750 is not substituted for F2 log shrinkage.
No research C01–C93/F1–F23 definitions are edited.

## Architecture / contract / exact formulas

analysis/models.py: explicit AnalysisOptions, frozen AnalysisFrame/VideoInput/Snapshot,
Outcome, AnalysisRun/MetricResult/Bundle. repository.py: constant-number bulk reads
of existing cohorts, official captures/scoped statistical history, topic/group evidence;
immutable run persistence and dependency/permission revalidation. outcomes.py: one
maturity/source/clock/retention resolver, no HTTP. numerics.py: integer raw counts,
Decimal28 ratios/log/exp and type-7 quantiles, no rounded-only percentage storage.
baselines.py/floor.py/repeatability.py/breadth.py/concentration.py/exposure.py/bounds.py
implement shared descriptive primitives; service.py orchestrates the internal bundle.
No new dependencies or alternate history/provider architecture. 0.4.0 is next minor
feature release after 0.3.5, documenting the new internal API/schema/formula version.

F1 L=(V+1)/(B+1), absolute V separate. Leave-one-out unique prior eligible same-boundary
age-matched references known by caller baseline landmark. Robust own B is exp(median
ln(1+V))-1; insufficient own references fall back to F2. Tiny baseline warning, no zeros
for unknowns, no future uploads/classification references or provider-score substitution.
F2 b=λ*b_channel+(1-λ)*b_peer, λ=n/(n+k), B=exp(b)-1. Channel log median and primary
median of peer channel log medians, video-weighted peer companion. Explicit k/minima;
no-own λ=0; peer video/channel/ownership counts. n5/k10/log9/log8 -> 8+1/3.
F3 H_i=1[V_i(a)>=G], observed hits/mature known outcomes; separate misses/pending/unknown.
F4 raw frozen channel ever-hit fraction under K/T exposure; full fraction only fully
ascertained, known-only fraction and finite bounds companion; stopped/zero-output retained.
F5 median across channels of Q25(V_c(a)); video-weighted median/Q25 and channel-floor
Q25/counts. Weak floor also reports explicit low-threshold fraction and observed zeros.
F6 Top1=maxV/sumV; Top3=sumlargest3/sumV. Canonical contributor IDs, total mass and
channel/group companions; zero mass -> null; no evaluative niche judgment.
F7 chronological next5/next10 after explicit observed qualifying anchor or first known
goal hit at declared landmark. Anchor excluded; full R_k=hits/k only all k mature and
positioned; known-only fraction/median plus pending/private/unknown/absent positions.
F8 qualifying topic-family count using explicit k documented independent units per
family. Frozen valid taxonomy, sister groups collapsed, unknown ownership provisional.
Coverage threshold gates results; unclassified/conflicted outcomes remain visible.
F9 HHI=sumshares² of matched-age reach; named channel/group/provisional-unit/topic
views, effective count, top shares/removal diagnostic. Multi-label topics allocate
reach equally; missing classification mass exposed, no good/bad cutoffs.
F19 paired creator-unit ever-hit and actual scoped upload hit fractions. First up to
K5/K10/no cap within T90/other explicit days, earliest frozen group entry, combined
sister chronology. Catalog completeness is a reviewed known-at profile input, never
provider totals; ended+mature+fully ascertained needed for no-hit miss. Attempts,
elapsed days, zero/low/stopped units, known-only/channel-balanced summaries and both
finite bounds retained. Unpositioned chronology blocks complete upload fraction/bounds.
F22 finite enumerated frame Lower=h/n, Upper=(h+u)/n. h8/u12/n40 ->[20%,50%]. Open
frame -> finite_frame_not_established; n0 -> null; not an inferential confidence interval.

## Frozen frames / outcomes / independence / provider firewall

Entrant/channel runs require a separately frozen eligible-video cohort with identical
Boundary object/version. Cutoff >= all freeze/creation clocks and <= actual read time;
F1/rule-anchor landmarks additionally cannot predate known video membership. Canonical
IDs deduplicate discovery occurrences. Later provider labels cannot revise frozen
membership. Publication/channel identity comes from retained official metadata known
at video freeze. Missing/conflicting chronology is not guessed; no historical subscriber
backfill, no interpolation, no lifetime total reconstructed as V(30).

Exact official public video counts only, observed in [publication+a, publication+a+
explicit tolerance], available by cutoff, retained at read. Closest forward observation,
latest availability then ID; contemporaneous official disagreement -> source_conflict.
Current/lifetime/provider-only counts outside the window -> insufficient_history.
Pending != miss; unknown != zero. Valid age-matched history before later removal remains
usable within permission; otherwise unavailable is explicit. Unknown eligibility,
excluded formats and unavailable source/identity have distinct states/reasons.

Known Phase2 creator/group units remain frozen; unknown ownership is not established
independence. F4 raw channels and F19 creator-unit denominators stay separate. F8 counts
only documented independent units; unknown channels and multi-label classification are
exposed, never silently assigned to other. T4/T5 outlier/VPH/averages/finance/quality/
geography and T2 auxiliary channel history never feed core age-matched outcomes.
NexLev optional modes/route registry/conflicts/retention remain as preserved below.

## Persistence, permissions, numerical context and CLI

v5 core_analytics checksum cf8f065640223bf1192b54f44ecef9acde06f738f3624cfec21ba55afec61383.
Frozen v1–v4 SQL/checksums unchanged. Only analysis_runs, analysis_metric_results and
analysis_outcomes added, with append-only UPDATE triggers and cohort/run deletion
cascades. Explicit configured DB migration installed [5]; 34 tables/integrity/FKs.
Existing sources/history/cohorts/cache remain reused; derived_cache is not used.

Manifests hash full frozen input/config/formula/software identity, options/thresholds,
input IDs, Boundary/cutoff/age/tolerance/goal/independence/missing policies. Creation time
is audit-only, not identity. Identical replay returns original results; changes create
new run IDs. Results include resolved-video sample counts (sample_unit video_outcome),
formula-specific channel/group/baseline/position denominators in details, numerators,
values/units/states/warnings and input hash. No naked or solely rounded metrics.

Run expiry <= every relevant loaded input/permission/frame expiry. Saved reads check
retained dependency IDs as well as expiry; permission revocation blocks derivatives.
No raw titles/comments/transcripts copied into runs. Statistical-only permission never
revives expired metadata/frozen frames. No real permission record configured; tests use
explicit scoped synthetic acceptance. Library AnalysisUnavailable.state and CLI report
policy_permission_required/insufficient_sample for unreadable frames. Empty/zero/
all-pending/all-unknown/small samples never emit NaN/Infinity. No silent retention bypass.

Operational CLI: analysis formulas (offline/no DB), analysis run --cohort ID --video-cohort
ID --options profile.json, analysis inspect RUN_ID (read-only). All profile thresholds
are explicit; docs/phase-3-analytics.md describes fields and trusted catalog/enumeration
review declarations. Server status adds offline_core_analytics, but extended analytics/
retention permissions remain gated. Startup/status/verify do not migrate/analyze/network.

## Acceptance / live calls / exact stop

Formal scripts/acceptance_phase3.py: 46/46. Full417 passed; analytic109 passed; NexLev51
passed; realstdio1 passed/416 deselected. Ruff check/122-file format,65 module imports,
20 JSON schemas/dependencies/CLI verify, clean/v1/v2/v3/v4 upgrades/integrity, no-key
provider diagnostics, in-memory and realstdio MCP pass. Exact timings/commands/results
are docs/phase-3-results.json; narrative docs/phase-3-verification.md.
Synthetic A–H fixtures, source/age/known-time, provider/finance, ownership, immutable
replay/permission revocation, stopped/low-output/private/pending and finite bounds
regressions cover bias. Deep sanity:100 channels/3,000 videos, <=12 bulk SELECTs, no
fragile wall-clock threshold. Prior307 regressions remain, latest schema/phase expectations
updated with one v4 upgrade parameter; frozen research/reports/runners compared to tag.

Live YouTube calls0/quota0; live NexLev calls0/quota0. Tests block live HTTP and scrub
keys. No live smoke, global plugin installation, hosted deployment or off-device backup.
Formula descriptors are not empirically calibrated predictions or recommendations.

Implementation checkpoint: e7dfed6c07a8a76c4827cdf56a95f6279c0873b6.
Final tag phase-3-verified identifies final documentation checkpoint. Resolve final
HEAD/tag/implementation SHA and enclosing bundle hash via adjacent parent manifest:
YouTubeNicheFinderMCP-phase3-backup-manifest.json. A tracked handoff cannot contain its
own enclosing SHA/bundle hash without circularity. Parent YouTubeNicheFinderMCP-phase3.bundle
has complete Git history; bundle verify, fsck and cold restore validate HEAD/tag,
seven research byte hashes, PROJECT_STATE bytes and restored-source offline CLI.
Earlier bundles unchanged; Phase2.5 bundle340356 bytes/SHA256
9DD1B8D613BFA3B856DEC45C934869C14EE29EEFD6A12F3934729AD35EC82259.

**STOP AFTER PHASE 3. Do not begin Phase 4.** Exact next scope: F10 measured historical
velocity/acceleration; F11 channel-balanced demand momentum; F12 observed supply change;
F13 older-catalog contribution; F20 ordinary post-hit baseline change; F21 winner
replacement. F14/F15/F16/F17/F18/F23, qualitative/packaging/production/risk, final
multi-axis decision, 15 public research tools and integrated release remain later work.

---

# Frozen Phase 0–2.5 handoff (historical, retained in full)

# YouTubeNicheFinderMCP — standalone Phase 2.5 handoff

Updated 2026-10-02 (Asia/Karachi). **Phase 2.5 COMPLETE AND VERIFIED. STOP before Phase 3.**
Current version **0.3.5**, schema **4**, **31 tables**, **13 eligibility rules**,
**307 tests**, **40/40 acceptance**, **zero registered research tools / 15 planned**.
Repository C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP.
Branch codex/phase-2-5. Local Python stdio MCP, without global host configuration.
**F1–F23 remain unimplemented after Phase 2.5.** The historical Phase 0–2 handoff
below remains complete; this current section supersedes its phase/version/provider limits.

## Frozen starting checkpoint and preflight

Phase 2 final HEAD/tag phase-2-verified:
**efd96e0f15344a3a0e92a69372864598636a4385**. Exact Phase 2.5 starting SHA is the
same. Before changes: clean codex/phase-2, full fsck exit 0, 255 tests in 17.86s,
Ruff/check/format, offline CLI verify, schema3/28 tables/status/integrity and both
MCP sessions passed. Default Windows pytest temp access was denied; explicitly
using repository .pytest-tmp basetemp passed without source changes. Preflight:
docs/phase-2-5-preflight.json. Seven original research files remain byte-identical
with exact hashes in the full retained history below and docs/research-files-read.json.
Relevant acquisition/retention/provider sections of all seven were revisited.

Absent, not invented: research_specs/nexlev/NEXLEV_DEEP_INTEGRATION_AUDIT.md,
NEXLEV_TOOL_CAPABILITY_MATRIX.md, NEXLEV_FIELD_TRUST_MATRIX.md,
NEXLEV_PHASE_2_5_SPEC.md and NEXLEV_TEST_PLAN.md. The user's locked Phase 2.5 brief
supplies those integration requirements. C01–C93/F1–F23 research contracts unchanged.
Current official NexLev API index/all linked reference pages and targeted public
REST discovery searches were reviewed before client code; docs/nexlev-api-contract.md
records sources, costs/limits, parameter contracts and limited absence findings.

## Current provider architecture and files

NexLev discovers/enriches; official YouTube verifies material public facts; local
Phase 2 adjudicates eligibility/cohorts. No provider score is final research truth.
collectors/nexlev/contracts.py: 30 stable routes, capability registry and 17 documented
REST endpoint contracts. models.py: narrow EvidenceBatch/ProviderRecord/FieldClaim/
DiscoveryContext/HistoryPoint contracts, T0–T5 field firewall, clocks and retention.
client.py: optional Bearer REST, safe errors, independent per-route capability states,
bounded GET retries/pagination and foreground async analysis jobs; no network on import.
repository.py: normalized route evidence, existing source/conflict/discovery/claim/quota
reuse, append-only replay, history anomalies, official conflicts and job provenance.
service.py: explicit REST projection/cache/ingestion, official hydration via existing
Phase 1 client/normalizer/history and Phase 2 metadata adapters, text hashes/track
metadata, reviewed external taxonomy aliases. collectors/provider.py adds optional
CapabilityProvider protocol; providers are not forced to implement every operation.

Mode A documented REST with optional NEXLEV_API_KEY. Mode B validated externally
orchestrated evidence without accessing ChatGPT's NexLev session. No direct remote
MCP OAuth/storage/refresh/deployment lifecycle implemented. REST metadata/catalog,
video details, transcripts/subtitles/comments, three similarity routes, YouTube search,
channel/short-long analytics, geography/revenue/RPM estimates, niche overview and
bounded documented async analysis are implemented. Similar channels is synchronous
with configurable timeout; thumbnails require explicit Deep mode.

Orchestrator-only: niche_finder semantic/filter, latest_faceless, faceless_outliers
semantic/filter, small_channel_viral, suggested_catalog, daily_analytics,
faceless_classifier, monetization_claim. Their rest_state is not_documented_for_rest.
No complete documented REST request contract for those routes was found; no private
endpoints or undocumented catalog parameters are called. Capability states separately
report available, not_configured, not_documented_for_rest, orchestrator_only,
plan_restricted, owner_authorization_required, quota_limited,
temporarily_unavailable and unsupported. Configured available is not entitlement;
CLI/server do not probe. Explicit client calls report runtime failure/probed state.
CMS ownership/network and promotions IDs reserved; owner-private analytics, Swipefile,
thumbnail generation, remote OAuth and convenience bulk routes remain deferred/excluded.

## Schema / identity / trust / quota / retention

New v4 optional_provider_evidence checksum:
384125aba24302812cedd74d6dd9aeb088a2e40ba37b4540a82ad003beac391d.
Frozen v1/v2/v3 checksums are unchanged (see retained schema history below).
Only three tables added: provider_runs (immutable ingestion/job manifests),
provider_evidence (route/provider-clock/trust/anomaly extension to source_records),
provider_quota_details (nullable provider quota extension to quota_requests).
Existing canonical IDs, source/conflicts, discovery runs/pages/results,
classification claims, live/derived cache, official observations/statistical history
are reused. UPDATE triggers protect all new evidence. Clean/v1/v2/v3 migrations pass;
explicit configured DB migration installed only v4; 31 tables/integrity/FKs passed.

T0 IDs; T1 public fact candidates; T2 auxiliary provider observations/history/text
metadata; T3 provider classification; T4 provider-derived scores; T5 estimates/claims;
T6 owner private reserved; T7 workflow excluded. Field->trust assignment is internal.
External payload cannot mark itself verified/canonical or self-attest REST acquisition.
Only rubric-supported provider duration/faceless/language claims enter Phase 2 as
provider_label, bounded by provider expiry. Finance/similarity/outlier values do not
enter canonical history or core eligibility/scoring. Broad raw text is not ingestible.

Provider record ID, created/updated/capture times, local fetch/observe/availability,
precision/state/normalization and route are retained. Same-field publication/duration
or simultaneous finance disagreement creates existing field-level conflicts. Counts
at differing capture times are distinct snapshots, not assumed semantic conflicts.
Official hydration returns captured public metadata/current count/hidden/rounded state,
stores official observations/claims and preserves provider originals/conflicts. No
missing official value falls back to a provider value marked canonical. Provider
faceless confidence .98 cannot override Bridged presenter sample 01:04–01:10; labels
become hybrid/conflicting/unknown pending coverage. English query/title/englishOnly
and English translated/generated subtitles cannot prove original spoken English.

Discovery retains semantic/filter/query/version/filter/limit/rank/seed/depth/channelType/
coverage/total/has_more/ceiling. Zero results are not absent competition; totals are
not a census. Viral feeds are not F19 denominators. Weak zero-subscriber records stay
candidates requiring hydration. Similarity remains T4, not audience overlap/CTR/causality.
Provider daily points live separately from OWN_HISTORY/statistical_history. Negative
counts/deltas, rebound, gaps, partial requested window, all-zero video counts, stale
series and questionable dataFetchedAt are flagged without repair. No reconstructed
history, V(30) or current-subscriber publication backfill is created.

ProviderQuotaLedger extends the existing ledger/sink architecture. Existing quota
rows retain endpoint/requests/bucket/time/contract; provider extension has provider,
access mode, nullable documented/charged cost, cached/free status, HTTP status and
unknown plan. Legacy assumed_cost=0 for undocumented external cost is only a mandatory
compatibility placeholder: nullable extension is authoritative. REST plan billing
balance is unknown; documented search20/min and analysis-create100/status500 per hour
have local guards. Failed REST4xx/5xx are documented free; eligible cached analysis free;
unknown transport charge remains null. YouTube, NexLev REST and external MCP separate.

No long-term NexLev retention permission is asserted. contract_review_required:
raw cache900s; transcript/comment text3600s; normalized public/provider history/provider
annotation86400s; private/restricted disabled. Hash/selected/generated/original/translated
metadata persists without raw text until its own expiry. Unknown origin stays unknown;
no subtitle URLs are fetched. Existing independent reviews and derived identity remain
extension points; no text analytics. Explicit history purge handles provider expiry;
cache expiry does not erase still-permitted normalized history. Official Phase 2
retention/permission gates remain unchanged; no accepted permission record configured.

## Configuration / diagnostics / acceptance

Process-only SecretStr NEXLEV_API_KEY, omitted from repr/serialization/log/DB/errors.
YTNMCP_NEXLEV_TIMEOUT_SECONDS default20, >0<=120;
YTNMCP_NEXLEV_SIMILARITY_TIMEOUT_SECONDS default300, >0<=900.
Both YouTube/NexLev key presence diagnostics only; no implicit .env loading.
Existing YouTube/db/retry/cache settings and dependency lock unchanged.
Installed editable package refreshed offline to0.3.5, no new dependencies.

Offline CLI provider status / capabilities / quota / contract / cache-status;
existing verify/db/history/snapshot/eligibility/taxonomy/cohort/tool commands retained.
Server status adds NexLev capabilities and phase2.5/schema4. Startup/status/verify never
initialize/migrate/collect or consume quota, and require no key. Public tools still0/15.

Formal scripts/acceptance_phase2_5.py: **40/40 passed**; full **307 passed in29.44s**;
NexLev51 passed in5.51s; real stdio1 passed/306 deselected in3.42s;
Ruff check and101-file format check passed;52 modules imported;15 JSON schemas;
clean/v1/v2/v3 upgrades/integrity, no-key provider CLI, in-memory MCP and all prior
regressions passed. All fixture HTTP is mocked and live transport blocked. Exact
commands/stdout/stderr docs/phase-2-5-results.json; narrative phase-2-5-verification.md.
Frozen phase0/1/2 reports/runners and original research blobs were compared to tag/hash.

Live YouTube API requests0 / quota0. Live NexLev API requests0 / quota0.
Optional NexLev smoke SKIPPED (NEXLEV_API_KEY absent). Only public docs were browsed.
No hosted deployment, global plugin installation, owner OAuth or off-device backup.

## Phase 2.5 checkpoint / backup / STOP

Implementation checkpoint: 3d0017b89e76b2361ae12dfc5a19e705789152bc.
Tag phase-2.5-verified identifies the final documentation checkpoint; resolve final
SHA via git rev-parse phase-2.5-verified or adjacent parent manifest. This tracked
handoff cannot contain its own enclosing SHA/bundle hash without circularity.
Parent bundle YouTubeNicheFinderMCP-phase2.5.bundle and adjacent
YouTubeNicheFinderMCP-phase2.5-backup-manifest.json contain authoritative final
HEAD/tag/implementation SHA, path/size/SHA256, bundle/fsck/cold-restore verification.
Cold restore verifies exact tag/HEAD/research bytes/PROJECT_STATE and restored-source
offline CLI with no created research DB. Earlier bundle SHA/size details preserved
below; Phase 2 final bundle SHA02F056A6340CE7ECD8DB0AD77FA1E3FA407AF397979FBE999EAA4CE5C39245CC,
285025 bytes. No earlier bundle is overwritten. Source bundle is local, not off-device.

**STOP after Phase2.5. F1–F23 and the15 public research tools remain unimplemented.**
Exact original next Phase3 scope: F1–F9; failure floor; next5/next10; concentration;
C90/F19; F22; demand breadth. Future analytics must use frozen local cohorts,
known-at-time/missing-history/creator-independence/permission gates. No scoring,
niche ranking/recommendations or Phase3 implementation has begun. Phase4 historical
F10–F13/F20/F21, Phase5 qualitative/production/C93, Phase6 confidence/F18 and Phase7
public-tool completion remain later scopes.

---

# Frozen Phase 0–2 handoff (historical, retained in full)

Updated 2026-10-02 (Asia/Karachi). **Phase 2 COMPLETE AND VERIFIED. STOP before Phase 3.**
Version **0.3.0**, schema **3**, **28 tables**, **255 tests**, **zero registered research tools**.
Repository: `C:\Users\hp\Documents\ChatGPT\Develpment\YouTubeNicheFinderMCP`.
Branch: `codex/phase-2`. Local Python stdio MCP; no global plugin/host configuration installed.

## Frozen prior history and Phase 2 preflight

Phase 0 code milestone c3acf9ed974d8baeed41ff78f3498f89291679fb;
final HEAD/tag phase-0-verified f7e7b88656d6091ce5bb396dcc35a709fa759baa.
Phase 0 acceptance had 56 tests. Its source/spec bootstrap was an independent repository.
Phase 1 code milestone 11688fb195658924308f15d5afe08d5d1a5385c5;
final HEAD/tag phase-1-verified **a2c017ab722bca0dccdd07acb702526de901f8d0**.
Phase 1 acceptance had 131 tests, schema v2/17 tables, real MCP stdio and zero tools/quota.

Exact Phase 2 starting SHA: **a2c017ab722bca0dccdd07acb702526de901f8d0**.
Before changes: correct path, clean codex/phase-1 tree, HEAD/tag agreement,
131 tests (8.59s), offline verify, DB integrity and Phase 1 bundle verification/hash passed.
Branch codex/phase-2 was then created. Neither prior migration nor frozen phase report,
acceptance runner, tag or bundle was rebuilt/overwritten. Prior generic regression
assertions now expect the latest phase/schema while preserving their original invariants.

## Authoritative research and hashes

All seven original files were copied unchanged from C:\Users\hp\Downloads and read fully
before Phase 1. Relevant sections of ALL seven were revisited before Phase 2 logic;
docs/research-requirements-map.md records the exact source/ranges/criteria and pre-code map.
research_specs/** -text preserves original bytes across Git/cold restores. The original
read manifest is docs/research-files-read.json. Exact files:

| File in research_specs/ | Bytes | SHA-256 |
| --- | ---: | --- |
| C90_Plus_Feasibility_Delta.md | 26659 | 5415EA7FCA736C5A1F0B2B106D21436067799D2713E28F3340A76C1F4C1F22CE |
| Faceless_Niche_Deep_Research_Prompt_Updated.txt | 60416 | 1431B91CEE1789A6AE6A5AA94E1379035E81A43C2960F465AF57CFDC8F47F892 |
| Faceless_YouTube_Research_Blueprint.md | 55120 | 17FC814A181DD6D5D7FAF9D4E897251361DFD7645298FB9187B40CB46DAD3558 |
| MCP_Feasibility_Matrix.md | 43092 | CD51997ECB3F5484CC46FBBE0CD076C98FB6F183E8B9CE483EB010F8AC630EC1 |
| Third_Pass_Evidence_Ledger.md | 32222 | 3E5C75F6E9EA38A36A1CA1D0679E1C4DBEF79AF94B6544FE879D35EEFAB5D3A3 |
| Third_Pass_Gap_Audit.md | 40249 | E3ADA4C68E743A9B1E9F6F163DB8092A35D00B804C3282AB11D7BEF0E6954DDF |
| YouTube_Evidence_Ledger.md | 35319 | D4BC5AD694E1B71E883DCE9FB30DC9786B009233031B96551FDD8987A3228F36 |

## Environment and architecture

Python 3.12.14 in .venv; official MCP SDK 2.2.0 (MCPServer), Pydantic 2.13.5,
httpx 0.28.1, pytest 9.1.1, Ruff 0.16.10. Exact lock: requirements-dev.lock.
Editable package refreshed offline to 0.3.0 without new dependencies. Restores need
Python 3.12+; bundled bootstrap runtime was
C:\Users\hp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe.

Phase 1 preserved: api/client.py/contracts.py/quota.py; collectors/normalize.py,
discovery.py/provider.py; domain/foundation.py; history/repository.py;
services/cache.py/capabilities.py/safety.py/snapshots.py. Async public-only request
helpers, bounded retries/pagination, per-ID failure outcomes, uploads/playlists/comments,
replaceable quota contract, immutable observations, explicit snapshots, known-at-time
queries, source conflicts and separated live/derived cache identities remain.

Phase 2 production modules:

- eligibility/models.py: typed claims, labels/states, review coverage, rules, taxonomy,
  memberships, boundaries, candidate landmarks and frozen member outcomes.
- eligibility/rules.py: deterministic versioned rubrics and calendar/duration helpers;
  no predictor, analytic metric or ML stack.
- eligibility/adapters.py: captured duration, declared audio, live details and rounded
  subscriber intervals as evidence; no fabricated Shorts boolean or visual verification.
- eligibility/repository.py: append-only evidence/decision storage, source-revision versus
  conflict handling, node/assignment versions, documented groups, five identity clocks
  and scoped channel aggregation from stored video reviews.
- eligibility/cohorts.py: eligible-video, small-channel and entrant constructors;
  canonical candidate freeze with every outcome, provenance, uncertainty and routes.
- history/retention.py: separate storage classes, trusted source-scoped acceptance
  records and statistics-only archive. No acceptance record is configured here.
- db/phase2.py: v3 append migration only. CLI/server/verification expose Phase 2 safely.

Architecture/database/methodology/requirements docs updated. Detailed contracts:
docs/eligibility-and-cohorts.md. Exact acceptance: docs/phase-2-results.json;
verification narrative: docs/phase-2-verification.md; runner: scripts/acceptance_phase2.py.

## Schema, tables and temporal invariants

v1 bootstrap checksum df4ead10f9d64ecd7950b0c37717976e475bd2dd6e0a6ca1d047554509f12177.
v2 research_foundation checksum c44e9bcca6a67d4007c209e306958ed31d02ef60f25aeeac01bb0bfae34a89c9.
v3 eligibility_cohorts checksum 7296eb9bec26ba21ea8caa0f6be50895e7944fd987d06106b08e873ee588ae7d.
Both older migrations' SQL/checksums are frozen. Clean [1,2,3], v1 [2,3], v2 [3];
atomic rollback, future/gap/tamper refusal and idempotence verified. The ignored default
DB explicitly upgraded with [3], contains no collected live history, and passes integrity.

Existing 17 tables: schema_migrations, app_metadata, channels, videos, source_records,
channel_observations, video_observations, source_conflicts, discovery_runs,
discovery_pages, discovery_results, eligibility_decisions, snapshot_jobs,
snapshot_targets, live_cache, derived_cache, quota_requests.

Eleven new tables: eligibility_rules, classification_claims, classification_details,
taxonomy_nodes, niche_memberships, creator_groups, creator_group_memberships,
cohort_definitions, cohort_memberships, retention_permissions, statistical_history.
Existing eligibility_decisions is reused through an FK extension; no old columns changed.
v3 updates schema_scope and adds normalized tables/indexes/immutable UPDATE triggers.

Canonical entities store identity/first availability, not timeless counts/titles.
Capture/source/entity replay is idempotent; changed replay is refused. T1 and T2 remain
separate. Known-at-time reads require observed/available/first-seen <= T; decisions
also require decided <= T and inputs valid under present retention. UTC microsecond
strings normalize offsets. Publication-time subscribers require bounded prior captures,
never current-size backfill. Classified decisions cannot borrow another subject/field,
future evidence or restricted-input lifetime. Same-source later claims are revisions;
independent contradictory claims remain conflicts with stronger preferred evidence.
WAL, foreign keys, FULL synchronization, busy timeout and integrity checks remain.
Explicit retention deletion is the append-only invariant's documented exception.

## Eligibility rule registry (13 versions)

| Rule ID | Type | Contract |
| --- | --- | --- |
| long_form_v1_6m | long_form | Duration convention, independent of Shorts/live eligibility |
| long_form_v1_8m | long_form | Duration convention, independent of Shorts/live eligibility |
| long_form_v1_10m | long_form | Duration convention, independent of Shorts/live eligibility |
| surface_format_v1 | surface_format | Official surface confirms; duration alone does not identify Shorts |
| live_status_v1 | live_status | Distinguish scheduled, current, archived live and ordinary VOD |
| spoken_language_v1 | spoken_language | Default audio and sampled speech are leads; text and region are not audio |
| faceless_v1 | faceless | Recurring human host is not central; verification is coverage scoped |
| current_small_v1_50k | current_small | Current observed size, never historical size or success |
| current_small_v1_100k | current_small | Current observed size, never historical size or success |
| niche_entry_v1 | niche_entry | First observed qualifying participation; earlier hidden uploads unknown |
| continuity_v1 | continuity | Documented pivot indicators; no ownership-transfer inference |
| activity_v1 | activity | Window-specific observed activity, never permanent abandonment |
| creator_independence_v1 | creator_independence | Only documented disclosure/company/network relation permits grouping |

Duration bands: below 6, 6–8, 8–15, 15–30, 30–60, 60+ minutes. Eight minutes is a
research convention; duration alone does not identify platform Shorts. Confirmed
surface class needs official surface evidence. Live distinguishes current/scheduled/
archived/ordinary/unknown; archived live is excluded unless the frame opts in.
Spoken English is separate from text/defaultLanguage/region. Audio metadata/provider/
caption/sample leads are likely; complete scoped human speech review can verify.
Faceless means recurring on-camera human host is not central. Thumbnail, synthetic
voice, stock assets or provider boolean alone do not verify. Channel aggregation
reports reviewed eligible IDs/count, observed denominator, coverage and supporting
review decision IDs; one opening or one video never verifies a channel. Scoped complete
review of at least two observed eligible videos is a convention, not lifetime coverage.

Current-small bands: 0–999, 1k–9,999, 10k–49,999, 50k–99,999, 100k+. Hidden count is
null/unknown and is retained as uncertainty. Current size is not size at publication,
breakout or entry. Five clocks: account_created_at, first_visible_upload,
first_observed_eligible_long_form, first_observed_niche_entry, first_mcp_discovery;
each reports observed/insufficient_history. MCP discovery means earliest canonical
availability, not necessarily a search occurrence. Entry uses first observed qualifying
participation; age bands are half-open 0–6/6–12/12–24/24–36 months, 36+ and unknown.
Earlier hidden/deleted/private participation remains unknown. Continuity/pivot rubrics
never assert ownership transfer or automatically exclude pivots. Observed activity is
active/low-output/currently-inactive/insufficient-followup/unknown, never permanent exit.

All classification results support verified/likely/uncertain/conflicting/unknown/excluded
and expose subject/type/label/confidence/rule/evidence/source/clocks/reason/conflicts.
Claim origin/permission is separate; external API/provider data cannot self-grant rights.

## Hierarchy, cohort frames, weak cases and independence

Stable taxonomy node IDs plus versions and labels; category > niche > sub_niche >
micro_niche > topic_family > video_premise, with missing levels allowed. Higher-level
same-version parents are required when supplied. Multiple meaningful subject labels
coexist. Assignment stores evidence, confidence, rule/source/time and separate semantic
layers: subject/entity, viewer promise, mechanism, production format, spoken language.
A boundary freezes version/nodes/descendants, inclusion/exclusion descriptions,
semantic scope, classifier version and uncertainty; broad/mid/narrow frames are possible
without robustness scoring. Same-node conflicting classifiers remain source_conflict.

Eligible-long-form constructor uses declared niche/publication window and duration,
format/live, spoken-language and faceless decisions. Current-small-channel adds current
observed size. Entrant constructor requires declared entry window, explicit candidate
entry_known_at landmark and first observed qualifying participation, not account birth.
Publication/entry windows are half-open. No minimum views, subscriber minimum, viral
hit, future five/ten uploads or continued activity exists. One-upload, three-upload,
weak, low-output and stopped entrants remain. Current/future popularity cannot silently
alter old frames; earlier missing content/unclear eligibility remains explicit.

Atomic freeze stores cohort ID/time/run/rules/boundary, canonical candidate identity,
member/exclusion/uncertainty state, reasons, evidence/decision IDs and entry status.
States: included, included_with_uncertainty, excluded, pending_classification,
source_conflict, insufficient_evidence. Excluded/unresolved candidates are retained.
Same ID/definition/frame replays stored membership; changed rules/candidates require a
new ID. Duplicate canonical IDs are one candidate but ALL retained discovery routes,
queries/ranks/pages/provider occurrences persist. Weak/recent/adjacent/entity/catalog
routes work without view floors. Five searches do not imply five independent creators.

Creator/studio/network groups require documented disclosure/shared company/network/
strong source. Style similarity leaves ownership unknown. Known sister and overlapping
group channels share connected independence units. Unknown relation uses canonical
channel provisionally and is never asserted independent ownership.

## Official API, permissions and retention

Official Google/YouTube contracts rechecked 2026-10-02. Phase 1 public methods and
quota contract google-public-2026-10-02 remain: cost assumptions one unit/request,
search/general/video_stats buckets with documented default 100/10000/10000 allocations;
no project balance or deployment entitlement is claimed. BatchGetStats stays disabled
by default with explicit per-ID failure behavior and no invented maximum. New video
hydration requests liveStreamingDetails and preserves requested-part provenance;
defaultAudioLanguage/defaultLanguage and live actual/scheduled clocks are normalized.
No request was made to YouTube during Phase 2. See docs/youtube-api-contract.md and
eligibility-and-cohorts.md for primary references and interpretation limits.

Public subscribers are rounded/hidden; published/upload/playlist/index dates differ.
Cumulative playback-start counts carry the 2026-08-24 mixed-regime caveat. No V(30)
backfill or views-to-income/engaged-attention conversion exists. Rival CTR, retention,
RPM/revenue, overlap and private traffic are unavailable; owner OAuth and captions
integration are absent. Provider protocol exists without an invented external API.
Policy acceptance and extended-retention entitlement remain unverified.

Retention classes: live cache TTL/stale display policy; refresh-limited raw/text
captures (30-day baseline); statistical history; input-bounded derived history;
independent supplied annotations; internal rules/taxonomy configuration; disabled
policy-restricted fields. Cache expiry/refresh never deletes/renews a valid snapshot.
A trusted administrative StoragePermission must document source-scoped acceptance,
verifier/reference/validity and 1–36 calendar months before statistical archive writes.
No configured acceptance exists. Archive stores statistical evidence only, never
raw titles/names/descriptions/provider text. Valid accepted statistics can survive text
expiry; unaccepted captures cannot. External claims/decisions/memberships/frames inherit
input expiry. Independent annotations/configuration are not blanket-deleted at day 30.
Reads refuse expired inputs; history purge-expired is explicit maintenance. There is no
scheduler; perform expiry/deletion maintenance, including separate data backups.
Source bundles exclude research SQLite data, credentials, logs, virtualenv and scratch.

## MCP/CLI and exact acceptance commands

Resource youtube-niche://status reports Phase 2/foundation_only/schema 3, actual DB,
key-present boolean, history/capabilities and live_collection_enabled=false.
**Zero** research tools registered; **15** planned. Startup/verify/inspection never
migrate, collect or initialize the configured DB. A missing DB is probed temporarily
by verify and remains absent. Stdout is MCP protocol only; package logs are stderr.

PowerShell, from the repository:

```powershell
& .\.venv\Scripts\python.exe -m youtube_niche_mcp migrate
& .\.venv\Scripts\python.exe -m youtube_niche_mcp verify
& .\.venv\Scripts\python.exe -m youtube_niche_mcp db integrity
& .\.venv\Scripts\python.exe -m youtube_niche_mcp eligibility rules
& .\.venv\Scripts\python.exe -m youtube_niche_mcp taxonomy status
& .\.venv\Scripts\python.exe -m youtube_niche_mcp cohort status
& .\.venv\Scripts\python.exe -m youtube_niche_mcp history status
& .\.venv\Scripts\python.exe -m youtube_niche_mcp history purge-expired
& .\.venv\Scripts\python.exe -m youtube_niche_mcp tool list
& .\.venv\Scripts\python.exe -m youtube_niche_mcp.server
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m ruff format --check .
& .\.venv\Scripts\python.exe scripts/acceptance_phase2.py
```

Formal result: **30/30 acceptance commands passed**, 255 tests in 19.36s, Ruff passed,
86 files already formatted, 45-module imports, 15 JSON schemas, dependency check,
CLI verify/integrity, clean/v1/v2 migrations/replay/rollback, in-memory MCP and dedicated
real stdio (1 passed, 254 deselected in 2.44s). All 131 older regressions retained;
124 Phase 2 cases cover duration/format/live/audio/faceless/coverage/current-small/entry/
clocks/pivots/multilabel/groups/frozen weak cases/retention and provenance/secrets.
Tests block live HTTP. Windows verified; other platforms not exercised. Exact commands,
return codes/stdout/stderr and scratch paths: docs/phase-2-results.json. CLI/tool/catalog
and host config examples remain in README and docs/tools.md/mcp-config.example.json.

## Checkpoint and portable backups

Phase 2 implementation checkpoint: f385c09625cd3e6db37cc2c65ef6510194ce3b4e.
The final documentation commit is tagged **phase-2-verified**. Resolve final SHA with
`git rev-parse phase-2-verified` or the adjacent manifest. This tracked handoff cannot
contain its own enclosing commit or bundle hash without circularity; the external
manifest is authoritative for final HEAD/tag SHA, bundle SHA-256/size and cold-restore
verification. Prior exact SHA/hash history is preserved above/below.

| Bundle in C:\Users\hp\Documents\ChatGPT\Develpment | SHA-256 | Bytes |
| --- | --- | ---: |
| YouTubeNicheFinderMCP-phase0.bundle | A13B08E7DBFF731CF48D0789CC67ED2790B8F1CBB31E2739877E067799E68FB1 | 47355 |
| YouTubeNicheFinderMCP-phase1.bundle | B8CE50AD584D0B37329E781B7C5C46BC35FC0CE4F8D05C614CE297EE30477DBB | 217761 |
| YouTubeNicheFinderMCP-phase2.bundle | 02F056A6340CE7ECD8DB0AD77FA1E3FA407AF397979FBE999EAA4CE5C39245CC | 285025 |

Adjacent manifests: YouTubeNicheFinderMCP-phase0-backup-manifest.json,
YouTubeNicheFinderMCP-phase1-backup-manifest.json, and
YouTubeNicheFinderMCP-phase2-backup-manifest.json, all in the same parent directory.
Phase 0/1 bundles are frozen and hashes reverified. Phase 2 source bundle includes all
prior history and the seven byte-preserved research originals. Finalization uses git
bundle verify, git fsck --full and a cold clone to compare HEAD/tag, research hashes
and PROJECT_STATE bytes. Restore into a new destination, recreate .venv from the
pinned lock, install editable package and run acceptance; docs/backup-restore.md gives
exact source/SQLite restore procedures. No remote push or off-device backup is claimed.
Git identity is repository-local automated Codex/noreply, without global changes.

## Known limits and STOP boundary

History is insufficient: no live channel/video observations or snapshot jobs.
Missing historical counts, earlier hidden catalogs, ownership and classification
coverage stay unknown. Current-size and duration/activity/sample thresholds are
research conventions, not calibrated growth predictors. No provider, owner OAuth,
accepted policy integration, classifier-validation study, ML/ASR/CV stack, scheduler,
niche scoring or recommendations. All F1–F23 analytics remain UNIMPLEMENTED.
The 15 public research tools remain planned/unregistered.

**STOP after Phase 2. Do not begin Phase 3 without the next user instruction.**
Exact original Phase 3 scope: **F1–F9; failure floor; next5/10; concentration;
C90/F19; F22; demand breadth**. Future analytics must use these frozen frames,
known-at-time, missing-history, independence and permission gates. Phase 4 historical
F10–F13/F20/F21, Phase 5 qualitative/production/C93, Phase 6 confidence/F18, and
Phase 7 tool completion remain later scopes. No Phase 3 work has begun.
