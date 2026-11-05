# YouTubeNicheFinderMCP — third-pass adversarial research audit

**Research cutoff:** 2 October 2026. **Scope:** English, faceless, long-form opportunities for new/small creators. Research and design only; no repository, database, schema, migration, or MCP implementation was inspected or changed.

This is a delta audit against the complete current versions of `Faceless_YouTube_Research_Blueprint.md`, `YouTube_Evidence_Ledger.md`, `MCP_Feasibility_Matrix.md`, and `Faceless_Niche_Deep_Research_Prompt_Updated.txt`. The baseline has C01–C89 and F1–F18. Those identifiers are preserved.

The two new prompt attachments were treated as one instruction. The first ends at the heading for section 68; the continuation starts at 69 and ends at 104. Section 68's body was unavailable and has not been reconstructed. The earlier requested source order and dedicated actual-channel section already appear in the updated master prompt as section 3 and 3A. Actual-channel research remains mandatory; the supplemental prompt's primary/methodological evidence standard also governs this audit.

**Reading map:** this file contains deliverables A–P, the scope audit, and the final section-104 decision. [Third_Pass_Evidence_Ledger.md](sandbox:/workspace/scratch/ade053737c5b/deliverables/Third_Pass_Evidence_Ledger.md) supplies source methods, access limitations, contradictions, and 15 supplementary channel cases. [C90_Plus_Feasibility_Delta.md](sandbox:/workspace/scratch/ade053737c5b/deliverables/C90_Plus_Feasibility_Delta.md) supplies all 19 feasibility fields, formulas, API checks, and changed tiers. Source identifiers E01–E30 and K01–K15 resolve in that ledger.

## A. Executive findings — only material deltas

The earlier framework remains directionally sound. This pass supports **three candidate new criteria**, one additional calculation inside existing criteria, and several stricter measurement contracts. It does not justify dozens of new opportunity scores.

1. **Attempt exposure must accompany channel success.** A channel's chance of having at least one observed hit and the fraction of its uploads that hit are different quantities. A selected 30-channel study reported 22 channels with a breakout among 600 uploads, but only 43 breakout uploads: 73.3% versus 7.2%, with different denominators. These are descriptive figures from that selected study, not beginner success probabilities. Add C90: paired attempt and calendar exposure. [E12]
2. **Post-hit baseline change supplies information that binary repeat hits miss.** A disclosed observational study found its first follow-up median above the pre-hit baseline while substantially below the anchor. Its requirement for three later uploads excludes non-continuers. Add a pre/post calculation to C26/C28/C29, rather than announcing a wholly new repeatability dimension. [E10]
3. **Who replaces the winners needs a temporal panel.** Existing concentration and entrant success do not measure the share of current winners who are newly observed entrants, or incumbent persistence between windows. C92 is a justified history-first measurement, not a presently validated niche predictor.
4. **Capacity does not establish ability to fund a pilot until evidence matures.** C93 adds a creator-declared loss limit and a timed production/cash plan. The purpose is to make an experiment affordable; views must not be converted into expected earnings. Cross-platform industry surveys support examining sustainability, but do not calibrate faceless YouTube risk. [E14–E16]
5. **Availability at decision time needs an explicit gate.** The baseline already requires prospective validation. Tighten C71/C74/C76 so that future uploads, subsequently revised classifications, and retrospectively observed subscriber sizes cannot enter an earlier recommendation. This is a merge, not another new criterion. [E08, E09]
6. **Provider contracts need validation on returned items.** NexLev's date/duration search outputs did not consistently match the requested order or duration class. Its indexed dates differed from exact video-detail dates. An indexed faceless example, Bridged, had a presenter reported in its opening. These observations strengthen existing provenance and eligibility checks; they do not establish platform-wide provider error rates. [K04, K12–K15]

No probability of niche success, optimal minimum cadence, imitation effect, public retention, CPM, or causal supply elasticity became identifiable in this pass.

## B. What the original framework already got right

Keep the existing distinction between absolute reach, within-channel lift, and peer standing. Keep independent creator counts, ordinary-upload floors, post-hit next-five/next-ten sequences, partial follow-up, weak/stopped cases, and unknown-versus-zero handling. Keep first-in-niche versus account age, publication-time size versus current size, format bands, English-audio verification, production/rights feasibility, query sensitivity, and separate confidence.

The baseline already rejects winner-selected success probabilities and public rival CTR, retention, revenue, audience overlap, and recommendation traffic. Its proposed time holdouts and pilot workflow are also already present. Reintroducing those as C90+ would inflate the criteria count without adding information.

The 2026 public-view regime and granular quota changes were already reflected in the baseline. Rechecking their official pages strengthens current validity; it is not a newly discovered correction. [E01–E04]

## C. Exact modifications to existing criteria

| Existing item | Change required | Status | Decision consequence |
| --- | --- | --- | --- |
| C20/C22 entrant and first-five outcomes | Display attempts, elapsed time, partial cohorts, and paired denominators; do not require future completion of K uploads to enter the cohort | MODIFY; C90 adds the paired exposure contract | A high ever-hit fraction with weak per-upload reach becomes a costly lottery, not automatically strong access |
| C23/F1 baseline | Freeze the eligible reference set and its values at the recommendation landmark; exclude future uploads | MODIFY | Stops hindsight from inflating or depressing the apparent breakout |
| C26/C28/C29 ordinary floor and follow-up | Add age-matched pre/post median change; include all qualifying follow-ups in the primary median, excluding only the anchor | MERGE; C91 is an operator | A useful baseline gain can coexist with no second viral hit |
| C17/C18/C30 identity/entry/drift | Record separate account, first visible upload, first observed niche upload, and first discovery dates; label pivots and unknown continuity | MODIFY | Old accounts and new public catalogs are not treated as proven novice creators |
| C32/C34/C67 eligibility | Validate faces, format, duration, archived-live status, and spoken language independently of search/provider labels | STRONGER EVIDENCE | Hybrid or uncertain examples cannot be silently counted as verified faceless LF entrants |
| C36/C37 topic depth | Test the first ten strongest premises and the next twenty for source and visual feasibility; deduplicate audio/video editions at the idea level | MODIFY | Thirty files or titles cannot stand in for thirty distinct feasible ideas |
| C39/C40/C73 event/regime context | Attach event, season, geography, and view-definition context to exceptional outcomes | MODIFY | Event capture is investigated before attributing demand to a durable format |
| C50–C53 production/capacity | Time research, factual checking, visual sourcing, permissions, editing, and revisions separately; show task ranges | MODIFY | Runtime, upload frequency, and apparent AI use remain inadequate labor estimates |
| C54/C55/C61 moat/originality/factuality | Separate source access, explanatory judgment, voice/editorial identity, and verification burden from visual style | MERGE | No automatic AI-commodity or credibility score |
| C69/C70/C72 coverage/independence/provider conflict | Retain route-level misses, ownership uncertainty, pagination scope, and field-by-field conflict | MODIFY | Empty index results reduce confidence in discovery completeness |
| C71/C74/C76 precision/sensitivity/confidence | Enforce known-at-time validation; show finite-frame missing-outcome bounds and decision flips | MODIFY | High confidence cannot be produced by repeated variants of the same biased route |
| C75/F17 optional index | Keep only optional, versioned research sorting; remove it as an automatic recommendation gate | SCOPE-LIMIT | Opportunity, evidence, entrant access, fit, and downside remain separate axes |

The documented `batchGetStats.snippet.publishTime` is described as upload time, while `videos.snippet.publishedAt` is public publication time with exceptions. Preserve their semantics separately; do not silently substitute one for a first-public-performance clock. This is a documentation-level ambiguity requiring contract verification before adoption, not evidence that the endpoint returned wrong timestamps. [E01, E02]

**Semantic boundary refinement belongs in C43/C69/C76.** Store separate subject/entity, viewer promise, explanatory mechanism, production format, and spoken-language labels. Use a broad parent, a practical mid-level niche, and specific subtopics; allow multi-label membership. Freeze assignment rules before examining outcomes. Report hard/uncertain membership, annotation version, and creator overlap between niches. Do not count the same creator as independent evidence twice in an aggregated total. Compare broad/mid/narrow results and include ambiguous weak cases as a sensitivity check. A model's semantic confidence is not evidence confidence, and no validated universal membership-weighting formula was established here.

## D. Genuine additions and duplicates rejected

| Candidate | Increment beyond C01–C89 | Classification | Disposition |
| --- | --- | --- | --- |
| C90 Paired attempt/calendar exposure | Same cohort, two units of opportunity plus its attempt distribution; prevents future-K-completion eligibility | NEW CRITERION | ADD NOW as a measurement contract; historical outcome fields can remain unknown |
| C91 Post-hit ordinary baseline change | A distinct calculation, but its floor/follow-up dimensions already exist | MERGE | Add to C26/C28/C29; no separate weighted score |
| C92 Winner replacement and entrant composition | Changes in winner identities and new-entrant share across comparable windows | NEW CRITERION | HISTORY-FIRST; current single snapshots cannot calculate valid turnover |
| C93 Pilot downside and evidence runway | Explicit limit on spending/time before comparable outcome evidence arrives | NEW CRITERION | OPTIONAL creator-input module; required when making a budget-specific pilot claim |
| Availability-at-time integrity | Existing history, precision, and validation expressed as a enforceable contract | MODIFY/MERGE | C71/C74/C76 |
| Identity continuity, entity dependence, update debt, source moat, idea depletion | Already covered dimensions; evidence/rubric refinement only | ALREADY COVERED / MODIFY | Existing rows |
| Causal entry elasticity, public audience transfer, niche opportunity half-life from a few snapshots | Parameters not identified by available public evidence | RESEARCH ONLY / REJECT | No live opportunity score |

C90–C93 in the companion matrix are **candidate audit identifiers**, not a declaration that the live MCP now has 93 criteria. C91 intentionally maps back into existing rows. No code or schema change has occurred.

## E. Full feasibility matrix

See `C90_Plus_Feasibility_Delta.md`. Every candidate has definition, purpose, classification, fields, sources, public feasibility, API feasibility, OAuth/history/human needs, formula, window, minimum sample, thresholds, bias, quota, complexity, and tier. Unverified batching limits and project-specific quotas remain explicit unknowns.

Only C90's reporting contract and C93's declared-input planning can work immediately without inventing history. C91 and C92 require correctly collected historical measurements for strong claims. These distinctions govern the final decisions below.

## F. New or modified formulas

The companion file defines F19–F23, preserving F1–F18:

- **F19:** paired ever-hit and per-upload hit fractions, with fixed entry/calendar and first-K rules; attempt distribution and missing statuses are mandatory.
- **F20:** ordinary baseline change using comparable pre/post 30-day outcomes and all eligible post-landmark uploads.
- **F21:** replacement share, incumbent persistence, and verified entrant share among winners; three different denominators.
- **F22:** lower/upper missing-outcome bounds for the enumerated research frame, not unseen YouTube creators.
- **F23:** planned pilot cash/time consumption and date of first usable mature evidence, compared with creator-declared limits.

An illustrative independent-trial model gives `1−(1−0.10)^20 ≈ 87.8%` probability of at least one hit, despite a 10% per-attempt rate. This is a mathematical illustration, not a fitted creator-growth model: uploads are dependent, ability varies, and decisions to continue are informative.

For F20, a pre median of 2,000 and post median of 4,000 gives approximately 2× baseline lift. Both can remain below a declared 10,000-view goal. For F22, 8 known successes and 12 unknown outcomes in a 40-channel frame bound its ever-hit fraction between 20% and 50%. Neither example estimates the platform population.

## G. Supplementary evidence ledger and actual-channel reality check

See `Third_Pass_Evidence_Ledger.md` for 30 source entries and 15 new channel cases. They are additional to the earlier 12-case ledger. Sources from one company or overlapping corpus are counted as one evidence family where appropriate.

Official Google/YouTube contracts and retained creator education anchor the research. Actual channel/video observations are mandatory reality checks. Primary methodological work tests selection and validation; disclosed analyst/vendor research supplies scoped empirical comparisons. Books are used only to the extent legally accessible, and community evidence supplies hypotheses. This preserves the master prompt's channel-research requirement while applying the supplemental prompt's methodological priority. Academic methods do not substitute for faceless YouTube outcomes.

The new case set includes established references, an intermediate channel, recent small channels with multiple strong uploads, hits with weak ordinary catalogs, observable subject drift, and a very small recent catalog found through live discovery. It does **not** establish permanent creator failure or profitability.

Illustrative provider-observed current catalogs, using an 8-minute eligibility rule:

| Case | Current subscribers | Retrieved uploads / duration-eligible | Eligible current-view median | What it tests |
| --- | ---: | ---: | ---: | --- |
| Industrial Empire | 3,920 | 52 / 52 | 1,050 | Several exceptional uploads coexist with a much lower ordinary floor |
| Business Explained Network | 1,290 | 7 / 7 | 19,000 | Positive small-channel multi-upload reach; sparse cohort and unknown publication-time size |
| History Archive | 381 | 15 / 15 | 495 | A strong historical-reconstruction anchor did not produce comparable ordinary follow-up reach |
| threaded. | 654 | 11 / 7 | 151 | Huge anchor; four sub-eight-minute uploads must not enter the main LF cohort |
| Industrial History Archive | 8 | 41 / 41 | 55 | Weak catalog missed by constrained semantic discovery; recent entry on an older account |
| Mustard | 2,390,000 | latest 30 / 30 | 6,900,000 | Sparse observed releases undermine a universal weekly-cadence rule; incumbent resources unknown |

All counts are **current lifetime observations** on 2 October, with rounded list counts unless exact details were retrieved. They are not historical V(30), matched performance, income, or causal effects. Established-channel medians refer to the retrieved slice. The ledger documents scope and sampled visual verification.

Bridged illustrates a boundary problem: the auxiliary visual analysis reported a presenter at about 1:04 in the opening. Its classification becomes **hybrid/uncertain pending broader review**. A single face appearance does not establish that a recurring host is central throughout the channel; it does invalidate treating the provider label as complete verification.

## H. Contradiction and weak-evidence audit

| Existing assumption or tempting interpretation | New evidence | Relationship | Decision |
| --- | --- | --- | --- |
| A few hits demonstrate sustainable new-creator opportunity | Industrial Empire, threaded., and History Archive have hits alongside weaker ordinary catalogs | Confirms baseline caution | Retain floor and follow-up; add exposure and baseline change |
| A first-ten study represents all newly created channels | Indexed vidIQ methods require ten same-format uploads within 90 days | Scope-limits | Evidence applies to completers; include low-output entrants in our panel [E17] |
| An ordinary follow-up below the peak means the hit created no useful lift | OverseerOS compares follow-ups with the pre-hit baseline | Weakens this interpretation | Calculate F20, without claiming causal transfer [E10] |
| Same-topic repetition proves visual/style copying works | Continuation study identifies explicit title entities, with a small selected group | Scope-limits | Keep topic/narrative/title/visual layers distinct [E11] |
| Higher cadence causes faster beginner growth | Industry cadence frames are selected; successful sparse incumbent and weak frequent catalog coexist | Requires more evidence | Measure burden and association; no universal minimum [E18, K10, K15] |
| Date-sorted provider results construct a birth cohort | Returned order, coarse dates, old accounts, and filter misses | Contradicts treating results as a guaranteed cohort | Post-validate, recruit prospectively, record uncertainty |
| Empty weak-channel index results mean weak competitors are absent | A live route found an eight-subscriber, 41-upload catalog | Contradicts this interpretation | Record route blind spots, not population prevalence |
| Public views imply engaged attention or earnings | Official 2026 definition separates starts from private engaged measures | Confirms baseline rejection | No conversion factor or CPM-based opportunity inference [E01, E04] |
| Repeated sensitivity variants validate a ranking | Overfitting research warns about optimizing the validation criterion itself | Strengthens | Freeze design and use untouched future creator/time groups [E08] |

Industry and analyst evidence is observational, often current-size selected, commercial, and not independently replicated here. Several attractive studies were accessible only through indexed excerpts. They receive limited weight and never supply calibrated thresholds.

## I. False-positive audit

Before a strong recommendation, attempt these explanations:

| False positive | Required test | Result if unresolved |
| --- | --- | --- |
| One peak or best-of-many attempts | Remove anchor/top creator/top three creator groups; show attempt and floor distributions | Downgrade repeatability or access |
| Existing audience or professional operation | Historical size, old niche catalog, creator/studio disclosures, known cross-channel links | Experience/independence unknown; do not count as novice proof |
| Celebrity, incident, release, or regional event | Annotate anchor context and compare non-event uploads and alternative explanations | Event-dependent opportunity |
| Provider faceless/English/LF label | Sample openings/middles/later uploads and verify audio, format, archived live | Eligibility uncertain; exclude from verified denominator |
| A future-known baseline | Reconstruct what was actually available at the decision date | Invalidate retrospective score |
| High average from huge hit | Median, Q25, low reach, top shares, and per-creator summaries | Keep ceiling separate from ordinary reach |
| Cheap-looking AI or stock production | Timed source/verification/visual/rights/revision pilot | Production fit unknown |
| More entities or titles imply repeatable ideas | Verify the next twenty premises after the best ten; collapse semantic and edition duplicates | Inventory not validated |
| Similarity implies CTR or demand | Treat visual/title sameness only as annotation; inspect alternatives and credible differentiation | No causal packaging conclusion |

Observed case contrasts are attempts to falsify interpretations. They are not a formal estimate of the research tool's false-positive rate.

## J. False-negative audit

Do not discard a niche merely because discovery returned few small channels, current subscribers are high, early uploads are young, a channel releases infrequently, or a follow-up is far below its exceptional anchor. Few results may reflect indexing, terminology, audio language, geography, or provider filtering. Current size can be an outcome of growth. A narrow profitable specialist audience may satisfy the creator's goal without huge public counts; that profitability still requires private evidence.

Use adjacent mechanisms, entity-based queries, different terminology, weak-case routes, and known-channel upload catalogs. Retain a **research-more** lane for promising need evidence with insufficient coverage. Measure false-negative performance only in a prospective, independently discovered evaluation frame; there is no observed population recall denominator in this pass.

## K. Sampling upgrade — weak channels and discovery stopping

1. Freeze a manifest: query, route, provider, locale, filters, fetch time, sort, pages, intended eligibility, and research budget. Avoid minimum views or subscriber thresholds in a weak-case route.
2. Recruit by first observed eligible publication/entry, not account birth or a provider's index date. Eligibility must be assigned without using later performance. Preserve account-age and identity uncertainty.
3. Keep a core tracked panel and a separate discovery-expansion panel. Changes in search coverage must not masquerade as performance changes or winner turnover.
4. Track each entrant whether it publishes one, five, ten, or no further visible eligible uploads. Record missing/deleted/private/unavailable outcomes separately from observed low counts.
5. Use provider semantic search, date/low-popularity search, entity searches, adjacent topics, public catalog pagination, and permissible archival context. Provider provenance and platform-policy eligibility must be checked before any auxiliary historical dataset is imported.
6. Record marginal newly eligible creators per additional route/page and overlap. Stop when the predeclared budget is spent or marginal yields remain below a declared research threshold across successive different routes. This demonstrates information saturation in the attempted routes, never completeness of YouTube.
7. Reopen discovery after a material event, substantial route change, conflicting provider evidence, or a decision that flips under missing-outcome bounds.

Sample-size targets in the old blueprint remain research budgets, not statistical power guarantees. No defensible population success percentage can be obtained simply by reaching 30 or 100 selected channels.

## L. Historical measurement upgrade

For each observation, preserve publication-clock semantics, observed-at time, available-at time, source, precision, eligibility/classification version, regime, creator grouping, and outcome availability. Publication-time subscriber counts need contemporary records; current subscribers cannot backfill them.

Collect early and 7/30/90-day counts prospectively where permitted. A missed 30-day snapshot cannot be recovered by dividing current views by days, and interpolation is not an exact value. Reconstruct no hidden/private/deleted video outcomes from current catalogs. An absent video is not automatically a zero-view failure.

Use creator-group-separated future time holdouts. Freeze discovery rules, semantic boundaries, thresholds, and weights before evaluating the holdout. Label whether earlier uploads' outcomes had matured before the decision. Standard time splitting alone does not guarantee creator independence, particularly with studios and multiple channels. [E08, E09]

**Validation protocol:** recruit a fresh enumerated entrant frame, freeze recommendations before its future outcomes, then assess the declared first-K/calendar goal at age 30. Compare the proposed deltas with simple absolute-floor and repeat-winner baselines. Report false-promising decisions, missed opportunities, research-more coverage, recommendation yield, and creator-declared wasted pilot cost. Precision/recall are conditional on this evaluation frame; non-published hypothetical alternatives have no observed outcome. Do not estimate population recall. Evaluate threshold changes on a development period and leave a later period untouched.

**Placebo checks:** repeat an equal-budget discovery/analysis workflow on predeclared unrelated queries, neighboring weak topics, and pre-anchor periods; where an enumerated comparable frame exists, sample from that frame without selecting its future winners. If the same alleged strong signal appears everywhere, inspect global size/age/trend confounding and the score's discrimination. These are falsification/query-sensitivity checks, not proof that formal causal negative-control assumptions hold. Cross-niche benchmarks must match outcome age, format, era, and contemporary entry/size evidence; current successful size cannot be adjusted in as if it preceded the outcome.

Survival models are research-only until event and censoring assumptions are supportable. A recorded public non-upload interval is an observable state; permanent creator abandonment is latent. Death-like competing-event models cannot be imported mechanically from another domain. Incomplete discovery creates left truncation; missing measurements and hidden content require additional handling beyond ordinary right censoring. [E07]

The official amended storage policy is conditional: accepted analytics applications have permissions that should not be presumed for this MCP. Statistical/derived history and refresh-limited text have different rules. In particular, a topic-drift design cannot assume that keeping superseded raw titles forever is allowed. Research proposes retained permitted derived annotations and policy review before adoption, not a policy bypass. [E05]

## M. Production economics, cadence, quality, and moat

The productive unit is an original, evidence-backed release at a sustainable cost. Record setup work, task hours, revision ranges, asset rights, source access, expert review, and overhead. Test the creator's next ten ordinary ideas, rather than extrapolating from the single easiest proof-of-concept.

Cadence is an observed schedule plus a workload question. It is not an experimentally established minimum for fast growth. Nor does an incumbent's sparse schedule prove that a beginner can use the same strategy. Mustard and Industrial History Archive are counterexamples to simplistic cross-channel frequency rules, with substantial differences in age, audience, and execution. [K10, K15]

For AI-assisted work, inspect what remains scarce: reliable sources, original analysis, defensible technical explanation, accessible visual evidence, editorial taste, personality through voice, and credibility. Do not infer AI use from smooth narration or synthetic-looking art; separate creator disclosure from model guesses. Template-like visuals and similar titles do not establish policy failure, originality, or lack of audience value.

Source-to-story yield and declining idea quality belong inside C36/C50/C61. Entity refresh depends on new legitimate evidence and a new viewer payoff, not repeating a famous name. News/event niches incur verification and update debt; advertiser suitability, monetization originality, copyright, and legal/ethical exposure are different reviews. [E06]

C93 compares a declared downside limit with production and waiting time. Revenue diversification and outsourcing can be creator inputs. Public counts cannot establish total income, team cost, burnout, or break-even. Commercial surveys motivate collecting these inputs but are not faceless-channel income forecasts. [E14–E16]

## N. Lifecycle — only measurable additions

| Proposed lifecycle signal | Current public snapshot | Prospectively tracked panel | Decision |
| --- | --- | --- | --- |
| Account age / first observed niche date | Available or partial, with continuity caveats | Improves with time | Existing C17/C18 |
| Older catalog still earning new views | Not identifiable from lifetime totals | Increment measurements by age/format/regime | Existing C06/C41 |
| Winner turnover and entrant share | Not valid from one snapshot | Comparable mature publication windows and consistent frame | C92 HISTORY-FIRST |
| Rapid title/topic wave | A descriptive cluster can be observed | Arrival/decay requires consistent retrieval over time | Merge C15/C43/C73; no imitation effect |
| Saturation, mature decline, resurgence | Interpretive labels are possible | Require sustained demand/supply/entrant evidence and competing explanations | Research labels, not calibrated stages |
| Niche opportunity half-life | Unavailable | No validated estimator established here | RESEARCH FURTHER |
| Cannibalization, audience transfer, platform favor | Public counts cannot identify causes | Owner analytics may help specific questions, not platform causal attribution | Reject public-score claims |

Do not turn a handful of snapshots into a market lifecycle clock. A late entrant's failure can reflect execution; a late entrant's success can reflect external distribution or a new treatment. A panel can document change without identifying its cause.

## O. Tier changes — changed or new items only

| Item | Revised priority | Reason |
| --- | --- | --- |
| C90 attempt/calendar exposure | Tier 1 reporting; outcomes history-dependent | Essential denominator contract |
| C91 calculation in C26/C28/C29 | Tier 2 after valid history; unknown at cold start | Adds decision-relevant ordinary baseline information |
| C92 winner replacement | Tier 3, history-first | Requires consistent panels; predictive validity untested |
| C93 downside/runway | Tier 4 optional inputs; gate for budget-specific pilot advice | No public-data income inference |
| C71/C74/C76 known-at-time and finite-frame bounds | Tier 1 | Prevents retrospective validation from supporting a live recommendation |
| C32/C34/C67 provider-label audit | Tier 1 eligibility | Contract mismatch can contaminate all downstream ratios |
| C75/F17 composite | Tier 4 optional sorting only | Unvalidated weights cannot make the recommendation |
| C87 population success probability | Tier 5 remains rejected | No representative future outcome frame |

No other existing row is promoted simply because this report repeats it.

## P. Final delta list

**ADD:** C90 paired exposure; C92 only as a history-first candidate; C93 declared downside/runway as an optional planning module.

**MODIFY:** F1's known-at-time reference set; C17/C18/C30 identity clocks; C32/C34/C67 eligibility checks; C69/C70/C72 route/conflict manifests; C71/C74/C76 temporal validation and finite-frame bounds; C50–C53 task-based production estimates.

**MERGE:** C91 into ordinary floor/follow-up; source/credibility/AI moat into existing access/originality/factuality; premise quality curve into depth/repeatability; event context into seasonality/event dependence; topic-wave annotations into similarity/classification/history.

**REMOVE:** use of the optional composite as an automated approval gate; undocumented assumption that future K-completers represent entrants; substitution of an upload/index timestamp for first-public publication without verification. These are removals from proposed interpretations, not claims that live code contained them.

**KEEP:** the original cohort framework, age/format comparisons, independent creators, weak-case discovery, ordinary floors, next-five/next-ten tracking, absolute-plus-relative reach, production/rights checks, separate confidence, and prospective pilots.

**REJECT:** creator population success probability from selected data; public CTR/retention/RPM/recommendation traffic; causal imitation/cadence/entry elasticity; Monte Carlo probabilities that simulate uncertainty in a biased sample while ignoring selection; automatic rights violations; unaudited archive/provider policy bypass.

**NEEDS FUTURE HISTORY:** valid first-30-day outcomes, publication-time size, pre/post floor change, turnover, arrival/decay waves, seasonal durability, and population validation. Existing provider snapshots may support exploratory description, not fabricate the missing panel.

## Prompt coverage and limits

| Prompt scope | Disposition in this pass |
| --- | --- |
| 1–6; supplementary hypotheses A–F | Applied as a delta research audit; source order and real-channel study retained |
| 7–18 selection, entry, identity, post-hit, attempts, denominators, replication, competition, replacement, mobility | C/F/K/L/N; C90; C91 merge; C92 history-first; no causal elasticity or portable success guarantee |
| 19–30 public audience transfer, cadence, economics, quality, source/trust/personality moat, ideas, replenishment, updates, cannibalization | C/M/N; task/input rubrics and public-identifiability limits |
| 31–43 lifecycle, volatility, persistence, cross-niche baselines, confounding, post-treatment, censoring, competing risks, early signals, regimes, depth, whitespace, format fit | F/L/N; frozen benchmarks and future validation; no private proxies |
| 44–57 portability, title/visual waves, quality/comments, cross-platform/knowledge graphs, news, policy, originality/AI/human moat, failures, novice disadvantages | C/H–M; existing-row merges, scoped evidence, and rejections |
| 58–67 small-channel false positives, independence, entrant quality, supply, weak/archive discovery, precision, semantic/hierarchical/multi-label boundaries | C/I/K/L and source ledger; boundary/overlap rubric and unknowns retained |
| 68 | Heading only; body unavailable |
| 69–85 stopping, event capture, holdouts, multidimensional decisions, robustness | I–L; final decision contract; history-based analyses specified, not falsely claimed completed |
| 86 new cases | 15 new cases across industrial/engineering/transport, history/archaeology, business/economics, and some space/architecture/science references; not a balanced all-category sample |
| 87 industry datasets | Eligible/completer/current-size frames audited; blocked full methods explicitly marked |
| 88 books | Publisher/author pages and legal excerpt inspected; no full-book or unaccessed-edition claim |
| 89 sustainability | Cross-platform paid/survey frames used to motivate inputs only |
| 90 methodology | Heavy tails, attempt maxima, clustering, finite-frame bounds, censoring, future holdouts; no unvalidated statistical sophistication |
| 91–92 API/policy | All named endpoint families rechecked; no API execution or permission assumed |
| 93–100 ledger, contradictions, duplicate audit, matrix, formulas, decision axes | Companion files plus A–O |
| 101–103 A–P outputs; no implementation; materiality | This report and two companions; three justified candidate dimensions, one merged operator |
| 104 final answer | Below |

The case study does not fill every established/new/weak/pivot cell in every requested niche. Legal education, independent biography/mystery, geography, and several nature/space subcategories lack a fresh balanced case panel here. No recommendation for those categories is supported by this audit. The missing section-68 text and blocked sources also limit coverage. These gaps do not justify inventing measurements or postponing the valid deltas above.

For any later niche recommendation, return separate **Opportunity (Strong/Moderate/Weak), Evidence Confidence, Entrant Accessibility, Downside, Repeatability, Production Fit, and Durability**. Attach policy/rights/factual risks, strongest counterexample, important unknowns, likely failure mode, and evidence that would reverse the decision. With insufficient coverage, return research-more rather than a calibrated probability. This pass recommends measurements, not a ranked niche shortlist.

## Final answer to section 104

**After three rounds, what exact additional information, if any, should the MCP measure before recommending an English faceless long-form niche to a new/small creator?**

It should add attempt/calendar exposure, explicitly test what information was known at the recommendation time, and verify provider eligibility and timestamp contracts. It should measure post-hit ordinary baseline change within existing follow-up criteria when valid history exists. Winner replacement is worth collecting prospectively. A creator-declared pilot loss limit is useful when assessing personal production fit. The remaining requested dimensions mostly belong in the existing framework or remain unidentified; more criterion names would not make the recommendation more reliable.

| Proposed addition | Evidence strength | Already covered? | MCP value | Feasibility | Final decision |
| --- | --- | --- | --- | --- | --- |
| C90 paired first-K/calendar exposure and attempt distribution | Strong denominator logic; selected empirical illustration | Components yes; paired reporting contract missing | Prevents many-attempt optimism and completer bias | Collect fields now; comparable outcomes need history | **ADD NOW** |
| Known-at-time feature/outcome audit | Strong methodological basis | Time holdouts already; explicit gate strengthens them | Makes retrospective validation relevant to future decisions | Provenance plus stored observations; no backfill invention | **MERGE INTO EXISTING** |
| Provider eligibility, language, duration, and clock reconciliation | Official semantics plus concrete returned-item conflicts | Yes | Protects every downstream cohort metric | Metadata and targeted sample review | **MERGE INTO EXISTING** |
| C91 age-matched pre/post ordinary baseline change | Moderate observational support; causal mechanism unknown | Floor and follow-up already covered | Separates useful floor gain from repeat-hit failure | Needs genuine age-specific pre/post records | **MERGE INTO EXISTING** |
| C92 winner replacement / verified entrant share | Strong conceptual distinction; predictive value unvalidated | Concentration/access components, not temporal identity replacement | Measures whether access persists beyond incumbent winners | Consistent historical panel and contemporary entry/size evidence | **HISTORY-FIRST** |
| C93 pilot cash/time downside and evidence runway | Practical budget logic; indirect survey support | Capacity covered; explicit loss horizon missing | Tests whether the creator can afford evidence collection | Creator inputs and timed pilot; no view-to-income estimate | **OPTIONAL** |
| Identity continuity, weak discovery, event capture, idea depletion, source/verification moat | Mixed but useful; mostly strengthens baseline | Yes | Improves existing annotations and gates | Partial public data plus human review | **MERGE INTO EXISTING** |
| Calibrated future false-positive/false-negative performance | Methodologically necessary; no completed validation here | Yes | Tests whether recommendations help entrants | Independent future entrant/time frame | **HISTORY-FIRST** |
| Niche opportunity half-life and causal entry elasticity | Insufficient identifying evidence | Only context/association covered | Uncertain incremental decision value | Observational public counts insufficient | **RESEARCH FURTHER** |
| Public rival CTR/retention/RPM, audience transfer, algorithm favor, selected-sample success probability | Unsupported for the claimed public use | Already rejected | Misleading precision | Not publicly identifiable | **REJECT** |
