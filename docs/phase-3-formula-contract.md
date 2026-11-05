# Phase 3 formula contract — version phase3-v1

This contract is written before analytics implementation and governs it. Outputs
describe the frozen researched frame, never niche rankings or population probabilities.
All seven preserved research specifications were re-read. Primary equations are
Blueprint §28 lines 283–291; C90+ §F19 lines 113–123 and §F22 lines 149–153;
Third Pass Gap Audit lines 36–37, 77–85 supplies later temporal/exposure clarifications.
MCP Feasibility Matrix C01/C02/C12/C20/C23/C26–C29 supplies sample cautions.
The Evidence Ledgers document selection/dependence limits; the original research
prompt asks for comparisons, without superseding these final equations.

## Shared input, population and reproducibility contract

Each run consumes immutable Phase 2 cohort definitions/memberships, never discovery
result totals. Channel/entrant analysis requires a separately frozen eligible-video
cohort with the identical Boundary object. Frozen channel members and their entry
landmarks remain even without attempts. Video eligibility, topic memberships and
creator units are resolved as known at that video frame's freeze; entry independence
for F19 is taken from the entrant freeze. Later labels cannot revise these frames.
Analysis cutoff must be at/after both freezes and at/before the actual read clock.
Input publication chronology must be official, known by the video freeze, and
retained. Unresolved publication/identity conflicts block the affected outcome.

Caller explicitly supplies goal G, age a, nonnegative observation tolerance, own/peer
sample minima, pooling k, low-outcome threshold, breadth k and classification coverage
minimum. The initial k=10 is a documented research proposal, not a hidden universal
threshold. No lifetime fallback, interpolation, provider-history substitution or
subscriber backfill. Accept exact integer view observations from the official public
API source policy only; observe at age [a,a+tolerance], never before maturity. Choose
closest to a, then latest available time, then ID; unresolved contemporaneous official
counts conflict. Both observed_at and available_at must be <= cutoff. Stored extended
statistics require a currently valid scoped permission; expired live evidence cannot
be rescued by analysis. Deleted/private later state does not invalidate a valid earlier
age-matched outcome. Without one, preserve deleted/private or insufficient history.

Each result carries ID/version/run/cohort/Boundary/cutoff/age/tolerance/goal, included,
mature/pending/unknown/excluded counts, independent/unknown ownership diagnostics,
numerator/denominator/value/unit/state/warnings and input-manifest hash. Analysis
manifests include options, input IDs/hashes, code version and creation time. Creation
time is audit metadata, excluded from content-derived run identity. Identical retained
inputs/configuration replay identically; changed evidence creates another identity.
Persist only permitted frozen inputs/outcomes and derived numbers, never raw metadata
text. Expiry is bounded by every used frame, observation, classification, grouping and
permission. Read/replay checks current retention; no derived cache bypass.

Counts are integers; ratios use Decimal with 28-digit context, logs use Decimal ln/exp.
No percentage rounding in storage. Q25 is explicit type-7 linear interpolation at
(n-1)*.25; median is ordinary midpoint median. Small samples are disclosed; caller
minima gate baselines, while other descriptive statistics may report n=1 with warnings.
Empty/zero denominator returns null and a structured state, never NaN/Infinity.
Unknown != zero, pending != miss. No inferential intervals or composite score.

## Equations and formula-specific contract

| ID / source | Exact definition; numerator / denominator; unit | Population, maturity, balancing and independence | Missing, minimum, edge cases and use |
| --- | --- | --- | --- |
| F1 / Blueprint 283; Gap Audit 37 | L=(V+1)/(B+1). Own robust B=exp(median(ln(1+V_prior)))-1; below explicit own minimum use F2. Numerator V+1; denominator B+1; times lift. Also absolute V. | Candidate excluded; unique eligible prior videos in identical frozen boundary/format/era, published before candidate. Baseline landmark is caller-supplied <= analysis cutoff; reference outcomes already available at landmark. Same a/tolerance. | Required candidate outcome and configured sufficient own or peer baseline. Zero B gives finite +1 ratio with tiny-baseline warning; missing/pending never zero. Descriptive comparison, not opportunity. |
| F2 / Blueprint 284 | b=λ*b_channel+(1-λ)*b_peer; λ=n/(n+k); B=exp(b)-1. b_channel=median ln(1+V_prior). b_peer=median of peer channel medians in log space (channel-balanced primary), video-weighted log median companion. | Same references/landmark/age/boundary as F1; exclude candidate channel from peers; report n, peer videos/channels and frozen ownership units. If n=0 λ=0 and channel term absent. | Explicit peer-video/channel minima; k>0. This is shrinkage, not a replacement raw pooled median. Blueprint example n=5,k=10,b_channel=9,b_peer=8 => 8+1/3. The brief's 1,750 raw median is a diagnostic only; it is not the preserved F2 equation. No future entrant/winner selection. |
| F3 / Blueprint 285 | H_i=1[V_i(a)>=G]; observed hit fraction h/m. Integer hit numerator, mature known denominator; fraction. | Frozen unique eligible video frame; absolute G explicit. No subscriber criterion. | Hits/misses/pending/unknown separate. m=0 null; sample-scoped, known-only when incomplete. Decision support only under declared goal. |
| F4 / Blueprint 286, superseded by Phase-3 brief §19 and C90+ F19 | ΣH_c/C, H_c=at least one scoped goal hit. Full fraction only if all states ascertained; known-only fraction and finite bounds alongside. | Correct frozen raw channel frame, same declared K/T exposure as F19; no future-K completion requirement. Raw channels primary, frozen group companion. | H=1 on observed hit; H=0 only after window closure, maturity and complete catalog/eligibility ascertainment; else unknown. Zero/low/stopped output retained. No Wilson interval: current brief excludes inference. |
| F5 / Blueprint 287 | median_c Q25(V_c(a)); per-channel Q25 numerator summary / contributing channels; views. Video-weighted Q25 and median companions, median/Q25 of channel floors. | Mature eligible unique views, first summarize channels then aggregate; same frozen horizon. Report channels with no known mature outcomes separately. | At least one observed outcome/channel for descriptor; warn <5 preferred. All pending/unknown => null. Prolific channels get one floor each; group companion descriptive only. |
| Failure floor / Blueprint §8, Matrix C26 | F5 plus global median/Q25; count[V<threshold]/m; threshold explicit, strictly below. | Same mature frame, observed zero only; per-channel counts, weak channel floors below threshold, incomplete channels separate. | Unknown/pending omitted from numeric denominator but counted. No universal rejection threshold. |
| F6 / Blueprint 288 | Top1=max V/ΣV; Top3=sum largest min(3,m) V/ΣV. | Same-age unique mature outcomes; video shares primary; channel/group aggregates companion. | ΣV=0 => null; n<10 warning; partial coverage exposed. Contributors named by canonical IDs. Concentration does not imply bad niche. |
| F7 / Blueprint 289, 320 | R_k=ΣH_j/k only when all k actual eligible follow-ups are observed mature; known-only h/m companion for partial frame. k=5,10. | Explicit verified anchor or first known qualifying goal hit at caller-declared anchor landmark; canonical publication order, anchor excluded; same a. | Show each position mature/pending/unknown/deleted/private/uncertain/not_yet_occurred; excluded formats separately. Three actual follow-ups never becomes 3/10; null full R until complete. No hindsight best anchor. |
| F8 / Blueprint 290 | Count qualifying validated topic families with >= explicit k documented independent units each; qualifying creators and provisional channel counts separate. Optional effective count from F9. | Goal hits at a; frozen topic_family nodes/assignments. Known sister channels collapse by frozen unit. Unknown ownership is provisional, not verified independent. Multi-label hit contributes to each documented family count; cannot inflate creator total. | Explicit classified proportion threshold; conflicted/unclassified outcomes counted, never an 'other' family. Below coverage => insufficient_classification_coverage. No universal 'strong niche' label. |
| F9 / Blueprint 291 | HHI=Σs_c², s_c=ΣV_c/ΣV. Named channel, documented-group/provisional-unit, topic-family views. N_eff=1/HHI diagnostic. | Same-age observed mass in frozen frame. Multi-label topics allocate V equally across known labels; topic denominator is classified mass; unclassified mass/count and coverage reported. | Zero total => null; no good/bad cutoffs. Topic coverage threshold gates topic statistic. Top creator removal sensitivity exposed separately. |
| C90/F19 / C90+ 113–123 | Paired ΣH/n entrants and ΣY/M actual uploads; known-only fractions and F22 bounds when incomplete. Per-entrant hit/attempt ratios, channel-balanced mean of defined ratios. | Frozen entrant units, first up to explicit K=5/10 (or no K cap) uploads within explicit T (90/180 days examples). Entry+T+a final maturity; group sisters together, raw-channel companion F4. | Retain zero/1/3/stopped entrants; no invented attempts. Unknown eligibility/entry/catalog coverage prevents known miss. Report elapsed days, attempts, pending/unknown, zero/low output. 8/10=80%,10/100=10% test. No difference-of-ratios score. |
| F22 / C90+ 149–153 | Lower=h/n; Upper=(h+u)/n; finite-frame fraction bounds, raw h/u/n retained. | Explicitly enumerated frozen frame only; unknown includes pending/unavailable/unresolved. Applies separately to entrant and actual upload frames. | n=0 null insufficient_sample; open discovery finite_frame_not_established; inconsistent h/u/n rejected. 8/40 and20/40 => [20%,50%]. Not confidence interval; no undiscovered-unit inference. |

## Exposure and catalog ascertainment

Analysis options identify which frozen channel/group catalogs are complete through
the exposure end, with a documented coverage evidence reference and known-at clock.
This is an explicit reviewed input, never inferred from discovery pagination or a
provider total. Without it, an observed hit is known but a no-hit entrant remains
unknown. Completeness cannot erase unresolved eligible candidate records. Calendar
window is [entry, entry+T); first K uses publication order, not performance. An entrant
with no uploads can have a known no-hit only under completed/ascertained exposure;
its per-upload rate is undefined. F19 aggregate scope is the caller's enumerated
researched frame, with unresolved ownership plainly disclosed.

Only F1–F9, failure floor, F19 and F22 are implemented in this phase. F10–F18,
F20–F21/F23, rankings, recommendations and public tools remain future work.

Operational clarifications: sample_unit video_outcome names the shared resolved-video counts; actual formula denominators are separately named. Group exposure uses earliest frozen member entry. Unpositioned chronology cannot establish a complete scoped upload denominator, so full upload fraction/F22 upload bounds are suppressed while observed-only counts remain explicit. Stored derivative reads revalidate dependency/permission presence in addition to expiry.
