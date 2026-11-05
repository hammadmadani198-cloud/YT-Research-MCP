# Eligibility and frozen cohorts — Phase 2

The Phase 1 raw-data layer remains. Phase 2 adds offline reusable primitives,
with zero registered research tools and no F1–F23 calculations. Provider labels
are claims; a decision never destroys the competing claim.

## Evidence and adjudication

`Claim` records a canonical subject, field/value, evidence basis, source/version,
observation and availability clocks, review scope, origin, permission and expiry.
`Classification` records subject/type/label/state/confidence, immutable rule ID,
evidence IDs, source, observed/available/decided clocks, reason, conflicts and
details. General states are verified, likely, uncertain, conflicting, unknown and
excluded. Domain labels remain separate from confidence and permission state.

Use `EligibilityRepository.append_claim()` followed by `evaluate(subject, rule,
at=landmark)`. Rules are registered as immutable definitions. Full decisions reuse
`eligibility_decisions` through an FK extension, `classification_details`.
Availability, retention and subject/field checks prevent borrowing unavailable or
unrelated evidence. Stored decisions must follow their declared rubric. A new
version appends a decision; the old version stays readable at its own time.

Later captures from one source revise that source's current claim. Historical
claims remain stored. Different sources and equal-clock contradictory claims stay
conflicting. Human full review generally outranks sampled review and provider
labels. The preferred label can coexist with `state=conflicting`; conflicts never
silently become verification. Caption/provider language labels are leads, not
full speech verification. No local ML, audio recognition or vision stack is used.

## Rule registry

| Rule ID | Behavior / domain labels |
| --- | --- |
| long_form_v1_6m / long_form_v1_8m / long_form_v1_10m | Compare known duration with 360/480/600 seconds; duration_eligible, below_threshold, unknown; bands below 6, 6–8, 8–15, 15–30, 30–60, 60+ minutes |
| surface_format_v1 | short_form_confirmed, standard_vod_confirmed, probable_short, probable_vod, unknown; confirmed requires official surface evidence |
| live_status_v1 | currently_live, scheduled_live, archived_live, ordinary_vod, unknown; missing unrequested live part cannot prove ordinary VOD |
| spoken_language_v1 | verified_english, likely_english, mixed_language, non_english, unknown; text/title/defaultLanguage/region cannot verify audio |
| faceless_v1 | verified_faceless, likely_faceless, hybrid, host_central, unknown; recurring human host centrality, explicit scope/coverage |
| current_small_v1_50k / current_small_v1_100k | Exclusive current subscriber threshold; known_small, known_not_small, hidden, threshold_uncertain, unknown; rounded intervals, no historical backfill |
| niche_entry_v1 | First observed qualifying participation; uncertain earlier history; calendar age bands |
| continuity_v1 | continuity_consistent, possible_pivot, likely_pivot, continuity_unknown; no transfer claim or automatic exclusion |
| activity_v1 | active_observed, low_output, currently_inactive_observed, insufficient_followup, status_unknown; declared 90-day default observation window |
| creator_independence_v1 | Documented creator/group relation or unknown; style alone is insufficient |

Eight minutes is a research convention. Platform Shorts classification cannot be
reconstructed from a less-than-60-second rule. The official resource documents
audio-language and completed-live fields; the metadata adapter preserves these
as claims. It supplies no invented Shorts flag. Current platform Shorts criteria
also depend on upload date/channel category/aspect ratio. See the
[videos resource](https://developers.google.com/youtube/v3/docs/videos) and
[three-minute Shorts help](https://support.google.com/youtube/answer/15424877?hl=en).

Full human speech review can verify English within its declared scope. Audio
metadata and sampled transcripts normally produce likely English. A provider
faceless boolean alone remains unknown. One face appearance does not establish
host centrality; one host-free opening does not verify a video or channel.
`aggregate_faceless()` uses stored reviewed video decisions and reports reviewed
eligible IDs/count, eligible observed catalog count, coverage and supporting
decision IDs. Complete review of at least two observed eligible videos permits
scoped channel verification; this two-video minimum is a rubric convention, not
proof of a complete lifetime catalog. Mixed presenter/faceless reviews yield
hybrid. No single-video automatic channel propagation occurs.

Current-size bands are 0–999, 1k–9,999, 10k–49,999, 50k–99,999 and 100k+. Hidden
counts stay null/unknown and can enter an uncertainty frame. They are neither
zero nor automatic exclusions. Publication-time size still requires contemporary
observations through `publication_size()` and otherwise returns
`insufficient_history`. Present size is never substituted for size at entry.

## Five clocks and continuity

`EligibilityRepository.clocks()` exposes account_created_at, first_visible_upload,
first_observed_eligible_long_form, first_observed_niche_entry and
first_mcp_discovery, each with an observed/insufficient-history state. The first
MCP discovery clock is the canonical earliest availability to this MCP; it need
not be a search result. Publication/index/upload clocks remain separate in the
raw layer. Niche participation is based on known versioned membership, not the
join date. A cohort's qualifying entry also applies its language/faceless/format
rules. Calendar entry-age bands use half-open 0–6, 6–12, 12–24, 24–36 months and
36+; displayed last band is >36 months. Missing entry is unknown. Earlier private,
deleted or hidden uploads cannot be disproved by visible pagination.

Old-account/recent-niche, subject drift, unrelated historic uploads, observed
name change and pre-entry subscriber base are pivot indicators only. An old
account can have recent first observed niche entry. No code asserts creator
inexperience, ownership transfer or permanent failure. Descriptive activity
windows do not change entrant eligibility.

## Hierarchy, multilabel boundaries and independence

`TaxonomyNode` identifies a stable node ID plus taxonomy version and label.
Levels are category → niche → sub_niche → micro_niche → topic_family → video_premise.
Missing intermediate levels are allowed; a supplied parent must exist in the
same version at a higher level and be known at assignment time. Renaming/reparenting
requires a new taxonomy version. A subject can have many `NicheMembership`
assignments with confidence, evidence, classifier version, source and clocks.
Separate semantic layers include subject/entity, viewer promise, explanatory
mechanism, production format and spoken language. Labels are neither exclusive
nor a single opaque embedding.

`Boundary` freezes taxonomy version/node IDs, descendant policy, semantic scope,
inclusion/exclusion descriptions, classifier version and uncertainties. Subject
membership is the executable inclusion predicate; semantic scope descriptions
are provenance, not arbitrary code. Broad/mid/narrow boundaries can create
separate frames; no robustness score is implemented. Classifier disagreement on
the same node retains source_conflict; multilabel membership on different nodes
is not a contradiction.

Documented public disclosure, shared company, explicit network identity or a
strong documented source can group channel IDs. Similar style cannot. Known
overlapping studio/network relations form connected independence units; sister
channels cannot count as separate independent creators. Without documentation,
the canonical channel is a provisional unit with ownership relation unknown.

## Constructors and frozen frames

`CohortBuilder.freeze(CohortDefinition, tuple[Candidate, ...])` provides:

1. eligible_long_form: declared boundary/publication window plus versioned
   duration, surface, live, English speech and faceless decisions.
2. small_channel: at least one eligible observed video plus current-size rule at
   the definition's known_at time; hidden/unknown size is retained as uncertainty.
3. entrant: qualifying first observed niche participation in a declared entry
   window, with eligibility known at each candidate's explicit entry_known_at
   landmark. No account-birth or future popularity selection.

Publication and entry windows are half-open. Archived live requires explicit
allow_archived_live. Confirmed Shorts, host-central/hybrid format, non-English or
mixed-language content and outside-window candidates are recorded as exclusions.
Unknown format/language/review remains pending or insufficient evidence. Likely
eligible states can enter a declared uncertainty frame; include_uncertain=False
retains them as pending. Conflicts remain source_conflict with original claims.

Every canonical candidate is stored: included, included_with_uncertainty,
excluded, pending_classification, source_conflict or insufficient_evidence.
Members preserve reasons/exclusion reason, evidence and decision IDs, entry
status, uncertainty, independence unit and every still-retained discovery
run/query/route/rank occurrence. Five searches do not make five creators.
Recent/adjacent/entity/catalog/low-popularity routes are accepted without a view
floor. No minimum views, viral hit, subscriber minimum, upload count or ongoing
activity criterion exists. One-upload, three-upload and stopped entrants remain
in the frozen frame. A zero-evidence candidate remains represented as unresolved.

Freeze is atomic, canonical candidate IDs are deduplicated, and conflicting
entry landmarks are refused. The same ID/definition/frame replays stored members;
changes require a new cohort ID. Future subscribers, views, uploads or reviews
cannot mutate that frame. Frozen content stays bounded by its most restrictive
input expiry; immutability does not override retention permission.

## Retention classes

Cache TTL deletes cache rows only. Raw source captures/text retain the baseline
30-day cap. Statistical history is a separate statistics-only table; a trusted
administrative `StoragePermission` records source, acceptance reference, verifier,
verification/expiry dates and a 1–36 calendar-month cap. No approval is inferred
from key presence, and no acceptance is configured in this project. The optional
archive excludes titles, descriptions, names and raw provider payloads. A valid
archive can survive raw-text expiry; an unapproved snapshot cannot.

Derived claims/decisions/memberships/frames inherit restricted input expiry.
Independent supplied annotations and internal configuration have their own
declared lifetime. Policy-restricted/owner-only capabilities remain disabled.
The exception is conditional on an accepted application; text still has a
separate refresh/deletion requirement. See the
[official storage policy](https://developers.google.com/youtube/terms/derived-metrics-policy).
Run explicit `history purge-expired` maintenance before keeping expired data;
reads reject expired evidence and startup/verify never silently write. Separate
data backups need the same expiry handling. Source Git bundles contain no
research database or credentials.

Operational diagnostics: `eligibility rules`, `taxonomy status`, `cohort status`.
All are offline and never create an absent database. Public research tools,
provider/owner integration, policy approval, live collection, embeddings,
classifier calibration and F1–F23 analytics remain deferred.
