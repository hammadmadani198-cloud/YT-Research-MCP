# C90+ feasibility and measurement delta

**Research specification, 2 October 2026.** This supplements C01–C89 and F1–F18. No repository/code/schema/database was inspected or changed. Candidate IDs are for review: C91 is deliberately merged into existing criteria, and C92 is history-first. This is not an implementation approval or a validated predictive model.

Each candidate has the 19 fields below. “Public” means some inputs are public; it does not mean exact historical outcomes can be reconstructed. All public API-derived calculations are conditional on the application's applicable permission/audit state. NexLev observations are auxiliary public-surface records with independent provenance, not owner analytics or an assumed exception to platform rules.

## Candidate C90 — paired attempt and calendar exposure

| Field | Specification |
| --- | --- |
| 1. Proposed ID | C90 |
| 2. Name | Paired attempt/calendar exposure |
| 3. Definition | For a frozen entrant frame, report ever-hit outcomes and per-upload outcomes together with attempts and elapsed time; include low-output entrants |
| 4. Purpose | Prevent best-of-many and future-K-completion selection from masquerading as easy entrant access |
| 5. Raw data | Entrant ID/group; declared eligibility/entry evidence; first observation; public publication time; chronological eligible upload IDs; V(30); observed/available-at times; attempts; outcome and follow-up statuses |
| 6. Public availability / OAuth | Current chronology/counts are partial public inputs; V(30) and historical size need contemporary records. Public requests do not need owner OAuth; missing owner/private data stay unknown |
| 7. API endpoints | channels.list → uploads playlist → playlistItems.list → videos.list; batchGetStats for count snapshots after clock/contract checks; search.list only for candidate discovery |
| 8. Historical requirement | Prospective observations required for reliable first-30-day outcomes, publication-time size, and deleted/unavailable follow-up handling |
| 9. Auxiliary/human requirement | Provider discovery; human/validated rubric for niche, format, language, identity continuity, and creator groups; no licensed-history assumption |
| 10. Formula/rubric | F19 paired fractions plus attempt distribution; F22 unknown-outcome bounds; no subtraction of mixed denominators as a niche score |
| 11. Sample requirement | Any enumerated frame can report counts; display channel/group N and upload M. Existing 20–30 channel research targets remain exploratory, not a validity guarantee |
| 12. Recommended window | First K=5 and 10 attempts within T=90 days of observed eligible entry; outcome age 30 days, final assessment after T+30. Compare T=180 only with sufficient history |
| 13. Caveats | Actual creator birth/experience may be unknown; hidden/deleted videos and discovery misses; informative continuation; dependence; current-size selection; regime changes |
| 14. Quota cost | One-unit metadata/catalog requests plus snapshot requests; discovery consumes its separate search budget. No extra cost for arithmetic over permitted collected fields |
| 15. Difficulty | Medium–hard: chronology is feasible, entry validity and outcome completeness are difficult |
| 16. Priority tier | Tier 1 reporting contract; numeric outcomes may be history-unavailable |
| 17. Permission/policy state | Public retrieval subject to terms; cross-owner analysis/statistical history subject to applicable analytics permissions; refresh text and preserve policy state |
| 18. Evidence class/strength | Strong definitional logic; selected empirical illustration E12; E17 exposes completion conditioning. Growth-predictive value unvalidated |
| 19. Default/decision threshold | No universal successful fraction. Declare creator goal G and outcome age before sampling; show exposure and missingness even when results look strong |

**Decision: ADD NOW** to the measurement/reporting contract. Do not populate historical fields using fabricated averages or provider index dates.

## Candidate C91 — post-hit ordinary baseline change

| Field | Specification |
| --- | --- |
| 1. Proposed ID | C91 candidate operator; merge into C26/C28/C29 |
| 2. Name | Age-matched post-hit ordinary baseline change |
| 3. Definition | Compare robust pre-anchor ordinary reach with post-confirmation ordinary reach at the same video age, excluding the anchor |
| 4. Purpose | Distinguish floor improvement from another exceptional hit or regression to the peak |
| 5. Raw data | Anchor ID; first confirmed-hit landmark t0; anchor rule/version; pre-reference IDs/V(30) known by t0; next eligible post-t0 IDs/V(30); maturity/missing statuses; topic/context annotations |
| 6. Public availability / OAuth | Current catalogs/counts are public, but valid V(30) is normally historical. Owner OAuth is unnecessary for public inputs and does not grant rival private analytics |
| 7. API endpoints | Same public catalog/metadata/snapshot route as C90; no API directly supplies historical matched pre/post counts |
| 8. Historical requirement | Yes. Freeze the pre-reference set and values at t0; collect post outcomes when they mature |
| 9. Auxiliary/human requirement | Topic/format continuity, season/event/context, pivot and ownership review; model labels stay uncertain |
| 10. Formula/rubric | F20 ratio and absolute median change; report companion goal attainment, low tail, and maturity. Use all eligible follow-ups in primary calculation |
| 11. Sample requirement | Pre/post five exploratory; ten preferred. Below five, present the sequence without a strong conversion conclusion. Report unique creators and overlapping events |
| 12. Recommended window | Pre: latest comparable five/ten uploads published before anchor and already measured at age 30 by t0. Post: first five/ten eligible publications after t0; each measured at age 30 |
| 13. Caveats | Survivorship, event/seasonality, evolving execution, delayed recognition, overlap, age mix, tiny baselines, incomplete prehistory; not causal audience transfer |
| 14. Quota cost | Existing metadata plus repeated snapshots; arithmetic adds no requests. Human annotation/visual/provider charges are separate |
| 15. Difficulty | Hard for retrospective data; medium once a permitted prospective panel exists |
| 16. Priority tier | Tier 2 after valid history; unknown in cold start |
| 17. Permission/policy state | Same analytics/retention gate; preserve permitted derived labels rather than assuming permanent raw-description/title history |
| 18. Evidence class/strength | Moderate selected observational support E10; calculation is our HEURISTIC design, not a replicated effect |
| 19. Default/decision threshold | No validated 1.2×/2× approval cutoff. Compare ratio, absolute goal, baseline magnitude, and uncertainty; judge incremental value against existing floor/repeat metrics |

**Decision: MERGE INTO EXISTING**, with history-first calculation. The already-defined next-five/next-ten **after anchor publication** sequence remains a descriptive companion. The post-t0 sequence is the decision-relevant test after the hit could actually have been recognized; never silently substitute between the two.

## Candidate C92 — winner replacement and entrant composition

| Field | Specification |
| --- | --- |
| 1. Proposed ID | C92 |
| 2. Name | Winner replacement / entrant share among winners |
| 3. Definition | In comparable mature publication windows, measure changes in winning creator identities and the verified recently entered share of current winners |
| 4. Purpose | Separate P(success within entrants) from the composition of successful creators and incumbent persistence |
| 5. Raw data | Stable creator IDs/groups; fixed cohort/query manifests; age-specific outcomes; entry and contemporary size records; window eligibility; discovery-expansion flags; winner rule/version |
| 6. Public availability / OAuth | IDs/current metadata public; contemporary entry/size/outcomes partial. No owner OAuth required for public fields; external audience/experience often unknown |
| 7. API endpoints | channels.list, playlistItems.list, videos.list/batchGetStats; search.list for consistent repeated recruitment, not complete population enumeration |
| 8. Historical requirement | At least two comparable outcome windows and roster provenance; three or more useful for stability. Continue collecting before recommending |
| 9. Auxiliary/human requirement | Group common studios where evidenced; distinguish newly observed from proven new-to-creation; audit discovery expansion and migration between niches |
| 10. Formula/rubric | F21 replacement share, incumbent persistence, and verified entrant fraction; unknown-entry bounds for winner composition |
| 11. Sample requirement | Always show winner and entrant counts; report small denominators as sparse. No N converts a selected panel into a population frame |
| 12. Recommended window | Adjacent 90-day publication cohorts with 30-day outcomes; rolling 180-day sensitivity if enough history. Respect format and regime breaks |
| 13. Caveats | Discovery changes, heavy tails, ranking turnover, current-size reclassification, hidden network ownership, event waves, duplicated editions; no causal market elasticity |
| 14. Quota cost | Repeated public metadata/count snapshots plus budgeted repeated discovery; no new privileged endpoint |
| 15. Difficulty | Hard: stable frame and historical entry/size matter more than the set arithmetic |
| 16. Priority tier | Tier 3 advanced history; predictive validation pending |
| 17. Permission/policy state | Cross-owner comparative analytics and stored history require applicable permission; preserve provider and derived-label policy provenance |
| 18. Evidence class/strength | Strong distinction between denominators; HEURISTIC new measurement. No direct faceless entrant predictive study verified here |
| 19. Default/decision threshold | Use fixed absolute goal for primary winners; top-N secondary with explicit N. No recommended “healthy replacement” percentage |

**Decision: HISTORY-FIRST.** Existing C12/C20/C70/C73/C74 inputs are reused, but temporal winning-identity replacement is a distinct measurement.

## Candidate C93 — pilot downside and evidence runway

| Field | Specification |
| --- | --- |
| 1. Proposed ID | C93 |
| 2. Name | Pilot downside / evidence runway |
| 3. Definition | A creator-declared maximum pilot loss and time commitment compared with task-timed production, cash schedule, and wait for mature evaluation |
| 4. Purpose | Determine whether the creator can afford the experiment until evidence arrives, rather than just produce one week of output |
| 5. Raw data | Voluntary budget/loss limit; available hours; setup costs; per-release task hours and cash; revision ranges; cadence plan; payment timing; evaluation horizon; stop/review conditions |
| 6. Public availability / OAuth | Creator inputs and measured pilot logs, not rival public metadata; no YouTube OAuth needed for planning. Actual income/costs are private voluntary inputs |
| 7. API endpoints | None required. Public snapshots can later evaluate the pilot's reach but cannot supply financial inputs |
| 8. Historical requirement | No public history needed for a declared plan; one timed pilot plus additional ordinary tasks improves labor ranges. Unknown costs remain unknown |
| 9. Auxiliary/human requirement | Creator estimates, task timing, asset/source/permission quotes, optional contractor costs; no model-inferred team size or earnings |
| 10. Formula/rubric | F23 planned cash burn/time and first mature-evidence date; task-level scenario ranges, not a success Monte Carlo |
| 11. Sample requirement | At least one timed release for a preliminary estimate; several ordinary premises for a defensible cost range. These are planning heuristics |
| 12. Recommended window | Declared pilot K and schedule through final release's evaluation age; include setup, revision, and evidence collection costs |
| 13. Caveats | Learning effects, rights delays, revision tails, cash versus labor, opportunity cost, uncertain sales/payment timing; no universal cheap niche |
| 14. Quota cost | Zero for planning arithmetic; later public performance evaluation shares existing snapshot budget |
| 15. Difficulty | Low for declared limits; medium for honest task costing and uncertainty |
| 16. Priority tier | Tier 4 optional creator-fit module; mandatory inputs before budget-specific claims |
| 17. Permission/policy state | Voluntary purpose-limited user inputs; appropriate private-data handling. No earnings prediction from YouTube API counts |
| 18. Evidence class/strength | Strong budget identity; our HEURISTIC planning design. E14–E16 provide indirect cross-platform context, not calibrated costs |
| 19. Default/decision threshold | Creator's own maximum cash and time loss; fail fit if planned downside exceeds it or cannot be bounded to their satisfaction. No default currency amount |

**Decision: OPTIONAL.** Explicitly different from C53's weekly capacity; do not make missing budget a low opportunity score.

## Formulas F19–F23 and worked examples

### F19 — two opportunity units, with fixed exposure

Freeze a finite entrant frame E with n creator groups, a public-video eligibility rule, entry-clock evidence, calendar window T, first-K limit, outcome age a=30 days, and goal G. Define the scoped attempts as the first up to K eligible public uploads occurring within T. Low-output entrants remain in E. A creator with fewer than K attempts is not removed simply because it stopped publishing.

For each creator, define H=1 if any scoped attempt is observed reaching G at age a; H=0 only if the declared window ended and the scoped public outcomes are fully ascertainable with none meeting G. Otherwise H is unknown. Report no-observed-upload, insufficient history, pending maturity, unavailable content, and unresolved eligibility separately. These statuses are not invented zero-view uploads.

For fully ascertained finite-frame channel outcomes, `R_channel = ΣH / n`. For scoped upload outcomes, `R_upload = ΣY / M`, where Y is age-a goal attainment and M is the number of actual eligible attempts in the same scope. With incomplete outcomes, use F22 on each denominator and report the known-only descriptive fraction separately. Do not drop unknowns silently. Channel-balanced per-upload summaries are additional descriptors; channels with zero attempts have undefined per-upload rates.

Report K, T, attempts per entrant, zero/low-output groups, elapsed time, and both channel-balanced and pooled upload summaries. `R_channel − R_upload` is not an opportunity score: the units differ. Do not divide a catalog maximum by K as an “adjusted breakout.”

**Illustration:** ten fully tracked entrants make 100 eligible attempts in scope. Eight have at least one hit and ten attempts hit: 80% ever-hit, 10% per-upload. Both can be correct. Correlated attempts and heterogeneous creators mean `1−(1−p)^K` is only an illustrative IID model, not our estimator.

### F20 — ordinary floor change

At the confirmed-hit landmark t0, freeze eligible pre-anchor references with already-known age-a outcomes. Let `B_pre = median(V_pre(a))` and `B_post = median(V_post(a))`, with the post set being first k eligible publications after t0, measured as each matures. Exclude the anchor; include later hits in the primary post median.

`Lift = (B_post + 1) / (B_pre + 1)`; `Absolute_change = B_post − B_pre`.

The +1 only handles zero baselines; it does not make a near-zero denominator useful. Report the counts, full sequence, Q25 where meaningful, goal attainment, and context alongside the ratio. An “ordinary” median is a robust summary of all follow-ups, not a subset selected by future performance. A predeclared outlier-excluded diagnostic can be shown separately; excluding successful future uploads from the primary calculation changes the estimand.

**Illustration:** pre outcomes [1k, 2k, 2k, 3k, 4k], post [2k, 3k, 4k, 5k, 100k]. The post median is 4k; lift is about 2×, while only one post upload reaches G=10k. The gain may reflect execution or timing, not causal recommendation/audience transfer.

### F21 — three winner dynamics

Let W_t and W_(t+1) be creator-group winner sets under the same declared goal/age/format rules, in comparable publication windows within the documented frame.

`Replacement_share = |W_(t+1) \ W_t| / |W_(t+1)|`.

`Incumbent_persistence = |W_(t+1) ∩ W_t| / |W_t|`.

`Verified_entrant_share = |W_(t+1) ∩ verified_recent_entrants| / |W_(t+1)|`.

Newly replacing winners are not necessarily new creators. Entrant success remains `successful_entrants / all_eligible_entrants` in C20. If a winner set is empty its relevant fraction is undefined, with count zero reported. Unknown entry histories create bounds, not assumed novice creators.

**Illustration:** ten current winners, six shared with the preceding twelve, and three verified recent entrants: 40% replacement, 50% incumbent persistence, 30% entrant winner share. These describe this panel, not universal market openness. Discovery additions must be analyzed separately from the stable core.

### F22 — missing-outcome bounds within a finite frame

For an enumerated frame n, let h be known successes and u unknown outcomes. Then `Lower = h/n`; `Upper = (h+u)/n`. Known failures occupy the remainder. An analogous bound can use the actual scoped upload denominator M where outcome availability is incomplete.

**Example:** h=8, u=12, n=40 gives [20%, 50%]. If the research decision changes across this range, confidence is insufficient. This does not account for undiscovered creators, semantic misclassification, unidentified studios, or sampling weights. It is not a confidence interval or a population probability. Use clustered resampling only for a defensible frame and a clearly stated descriptive estimand; it cannot repair selection.

### F23 — pilot downside and evidence maturity

For the declared schedule, calculate `Planned_hours = setup_hours + Σ(release_task_hours) + evaluation/overhead_hours` and a dated cash-outflow schedule. For a no-income-assumed pilot, `Planned_cash_loss = setup_cash + Σ(variable_cash) + contracted_overhead`. If the creator supplies real contracted inflows, use a separately labeled cash-flow scenario; no public-view income conversion is permitted.

Compare both with the creator's declared limits. Track peak cumulative cash deficit when payment timing matters. The first mature outcome date is first publication +a; a complete K-release comparison is not ready before the last qualifying publication +a. Include revision/permission delays as scenario ranges.

**Illustration:** $100 setup plus five $60 releases costs $400 before any income. Ten setup hours plus five eight-hour releases costs 50 hours, before monitoring/revisions. With a $300 maximum loss the plan exceeds the limit; neither high demand nor a 20-hour weekly capacity fixes the cash mismatch. Weekly release dates d=0/7/14/21/28 give first age-30 evidence on day 30 and complete five-release evidence no earlier than day 58, excluding setup time.

## Current official API/permission recheck

References were read on 2026-10-02. No API request, OAuth credential, account entitlement, or live quota allocation was tested.

| Capability / official reference | Current cost/capability | Research constraint |
| --- | --- | --- |
| [search.list](https://developers.google.com/youtube/v3/docs/search/list) | 1 unit in Search Queries bucket; documented 100 calls/day; maxResults 50 | Additional pages consume calls; channelId video searches can have 500-result cap; totalResults approximate/capped, not search volume or complete entrant population |
| [videos.list](https://developers.google.com/youtube/v3/docs/videos/list) | 1 unit; public metadata/statistics; maxResults up to 50 in applicable modes | No historical V(30); ID-batch plan must respect supported contract; metadata is needed beyond count-only snapshots |
| [videos.batchGetStats](https://developers.google.com/youtube/v3/docs/videos/batchGetStats) | 1 unit; dedicated quota bucket documented in revision history; current statistics/duration, failure summary; public use without owner OAuth | Preserve documented upload-time publishTime versus public-publication metadata; maximum ID size unverified; do not invent it |
| [channels.list](https://developers.google.com/youtube/v3/docs/channels/list) and [resource](https://developers.google.com/youtube/v3/docs/channels) | 1 unit; current statistics, account metadata, uploads playlist; applicable maxResults 50 | Subscribers rounded to three significant figures/hidden; video totals span formats; join date is not niche entry or experience |
| [playlistItems.list](https://developers.google.com/youtube/v3/docs/playlistItems/list) | 1 unit; maxResults 50, pagination | Use contentDetails.videoPublishedAt rather than playlist-item addition as publication evidence; uploads surface not deleted/private history |
| [playlists.list](https://developers.google.com/youtube/v3/docs/playlists/list) | 1 unit; maxResults 50 | Structural clues only; cannot infer audience binge/retention or distinct story count from playlist membership |
| [commentThreads.list](https://developers.google.com/youtube/v3/docs/commentThreads/list) | 1 unit; maxResults 100; relevance/time sorts | Partial replies, moderation/selection; qualitative viewer phrasing, not population satisfaction |
| [comments.list](https://developers.google.com/youtube/v3/docs/comments/list) | 1 unit; maxResults 100, replies via parentId | Reply expansion adds calls; no public retention/private audience inference |
| [activities.list](https://developers.google.com/youtube/v3/docs/activities/list) | 1 unit; maxResults 50 | Activity timestamps are not a historical statistics archive or a creator birth census; old activity types changed/deprecated |
| [captions.list](https://developers.google.com/youtube/v3/docs/captions/list) | 50 units; authorized access; caption metadata | Not arbitrary public caption text; third-party transcript route needs its own provenance/permission |
| [captions.download](https://developers.google.com/youtube/v3/docs/captions/download) | 200 units; appropriate OAuth/edit permission | Cannot retrieve every competitor transcript through ordinary public API access |
| [Video localization fields](https://developers.google.com/youtube/v3/docs/videos) | Retrieved with relevant metadata parts; defaultLanguage/defaultAudioLanguage/localized title fields | Localized English title, hl, and relevanceLanguage do not prove English narration or target-audience geography |
| [Quota guide](https://developers.google.com/youtube/v3/determine_quota_cost) / [revision history](https://developers.google.com/youtube/v3/revision_history) | Granular buckets; other endpoint costs; invalid requests consume quota; daily reset Pacific | Old pooled “search costs 100 units” assumptions cannot price this design; project dashboard remains authoritative for granted limits |
| [Derived metrics/storage](https://developers.google.com/youtube/terms/derived-metrics-policy) | Conditional accepted analytics permissions; statistical/derived retention up to specified 36-calendar-month policy horizon; designated text refreshed/deleted within 30 days | Approval state unknown; keeping superseded raw titles is not assumed permitted. Review annotation retention and cross-owner aggregation before implementation |
| [Developer Policies](https://developers.google.com/youtube/terms/developer-policies) | Governs authorized routes, use, storage, and aggregation | No undocumented API/archive/provider loophole; compliance is a deployment prerequisite, not an opportunity score |

**Illustrative request budget:** for 1,000 known video IDs, a supported batch size b implies `ceil(1000/b)` snapshot calls. If b=50 is supported for the chosen method, three snapshots use 60 calls in that method's applicable quota bucket. This is arithmetic, not a verified batchGetStats maximum. Add metadata, catalog pagination, failed-ID handling, and separately budgeted discovery. Human/visual/provider prices were not verified and must be priced separately. A larger snapshot allowance does not increase the separate 100-search-call discovery budget.

### Policy changes versus baseline

The baseline already recorded the June 2026 granular quota and late-August public-view changes. Current references confirm those; no novel correction is claimed. The newly material contract issue is preserving upload/publication/index clocks separately. The revision history also documents changed activity fields, which reinforces that activities are not a durable reconstructed upload/statistics ledger.

Current monetization, AI disclosure, advertiser suitability, and fair-use pages were rechecked (E06). No new universal ban on AI-assisted faceless channels or fixed safe reuse duration was found. Disclosure/labels do not establish factual quality, asset permissions, or the full production method. Public starts are not private engaged attention, watch time, monetized playbacks, or earnings.

## Changed existing rows and recommendations

| Existing IDs | Material change | Tier disposition |
| --- | --- | --- |
| C20/C22/C23 | Attempt/calendar denominators and frozen known-at-time references | Tier 1 remains |
| C26/C28/C29 | F20 inside floor/follow-up, only with suitable history | Tier 2 operator; no extra score weight |
| C17/C18/C30 | Separate clocks, identity/pivot uncertainty; no current-size backfill | Existing tiers; required before novice claims |
| C32/C34/C67 | Provider-label/result-contract verification | Tier 1 eligibility gate |
| C69/C70/C72 | Route misses, deduplication, creator groups, field conflicts | Tier 1 coverage/independence |
| C71/C74/C76 | Available-at gate, F22 bounds, separate future creator/time holdout | Tier 1 data/validation gate |
| C50–C53 | Task estimates and revision ranges; reuse in C93 | Existing production tiers |
| C75/F17 | Optional sorting; remove automatic approval interpretation | Tier 4 |
| C87 | No selected-sample guaranteed/validated population probability | Tier 5 remains rejected |

Recommendations should expose separate opportunity, confidence, entrant access, repeatability, downside, production fit, and durability. A missing history or budget field changes the supported claim; it does not automatically lower a niche's demand score. Every shortlisted conclusion needs a counterexample, failure mode, important unknown, and reversal condition.
