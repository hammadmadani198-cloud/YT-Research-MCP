# MCP Feasibility Matrix — Faceless Long-Form Niche Research

This criterion register is part of the research blueprint dated 1 October2026 UTC. It specifies proposed research behavior, not an audit of implemented code. All numerical defaults and minimum samples below are **heuristics for exploration**, not validated universal YouTube thresholds. Do not interpret public proxies as access to the latent/private construct.

## How to read the matrix

Tables A and B join by criterion ID; together they provide every requested field. Meaning/importance, raw inputs, exact source mapping and access are in A. Formula, window, minimum sample, threshold, caveats, quota implications, difficulty, priority and tier are in B. Missing information remains unknown.

**H/C/T/A needs:** four Yes/No positions for historical snapshots, comments, thumbnail/visual inspection, and auxiliary provider or human/external evidence. For example `YNNY` means history Yes, comments No, thumbnails No, auxiliary Yes. A Yes can indicate a conditional enrichment/verification requirement, not that all sources must be used. A visual inspection is external to basic Data API metadata; selected video scenes may also be necessary.

**Public access:** Yes = raw facts observable publicly; Partial = public components/proxies exist but the full construct needs inference, history or human evidence; No = private, unavailable or creator-plan information. Every derived calculation separately requires the appropriate permitted analytics capability. See blueprint Section17; public availability does not establish unrestricted use, aggregation or storage.

**Raw-input dictionary:** `V` observed public views (same-age where specified); `P` exact video publication timestamp when available; `T` capture timestamp; `C` canonical channel ID; `S` subscriber count with hidden/rounding state; `D` duration. `V(30)` means a recorded30-day value, not today's lifetime total divided by age. Titles, comments, transcripts, thumbnails, source manifests and human labels are stated explicitly where needed.

**Tiers:**1 Essential;2 High Value;3 Advanced;4 Optional;5 Do Not Use. Priority labels are Must Have, High Value, Optional or Reject. Difficulty Easy/Medium/Hard concerns engineering plus validation, not platform permission. Tier3 identifies advanced-research functionality.

## Source / endpoint and quota mapping

| Code | Exact source / endpoint | Access and collection limits | Quota implication used in B |
|---|---|---|---|
| SE | Data API `search.list` | Discovery only; relevance/date orders and query variants; approximate totals do not give census or query volume | Search bucket,1/call;default 100/day;each page another call |
| CH | `channels.list(part=snippet,statistics,contentDetails)` | Public metadata/counts and uploads playlist ID; hidden/rounded size flags | General bucket,1/list request;batch known IDs where supported |
| V | `videos.list(part=snippet,contentDetails,statistics,status)`; supported subset via `videos:batchGetStats` | Public video metadata and counts; exact parts/field access vary | General1/list;granular stats1/call in its separate10k/day bucket |
| PL | `playlistItems.list(playlistId=uploads,maxResults=50)` | Paginated public upload enumeration; use actual video publish time rather than playlist-add time | General1/page;often the main enumeration cost |
| PS | `playlists.list` plus `playlistItems.list` | Public playlist structure; no session metrics | General1/list/page request |
| CM | `commentThreads.list(maxResults=100,order=time/relevance)`; `comments.list(parentId=...)` for remaining replies | Disabled/inaccessible comments are unknown, not zero; thread replies can be incomplete | General1/page;reply enrichment adds calls |
| HS | Prospective snapshots from public endpoints or separately licensed histories | Earliest observation limits backfill; provenance, gaps,regime and retention needed | Repeated V/CH cost;no history endpoint for arbitrary rival backfill |
| TR | Authorized transcripts/subtitles or auxiliary NexLev transcript access | Caption availability is not a downloadable public transcript entitlement; `captions.download` requires permission | Provider/owner access and pricing separate;avoid blind API caption retries |
| TH | Public thumbnail URLs, permitted image retrieval and human/provider visual inspection | Metadata URL is not actual visual analysis; video scene analysis is separate | No extra Data API method after URL retrieval;network/inference cost separate |
| HU | Human review, creator resource brief, fact checking and timed pilot | Qualitative/planning evidence must carry rubric and uncertainty | No additional API units;research labor can dominate |
| AP | NexLev or another licensed auxiliary source | Provider labels/history/estimates are source-specific;definitions and coverage can differ | Provider pricing/rate limits unverified;not equivalent to API quota |
| GT | Google Trends, optionally YouTube-search property | Normalized sampled interest;not raw volume or unique viewers | External access cost;no Data API quota |
| AS | Primary archives/asset-specific licenses and source evidence | Check reuse conditions for each asset;availability does not establish rights | External access/licensing/research cost |
| OA | Authorized owner's YouTube Analytics/Studio | Available only to the authorized owner for supported reports;does not unlock rival data | OAuth/report access separate;not a public niche endpoint |

Endpoint references: blueprint sources S3–S12 and current quota source S7. The separate stats bucket and `publishTime` schema come from S8. This document does not prescribe scraping as an API fallback. Provider-origin and permitted use must be checked before integration.

## A. Criterion meaning, inputs and access

| ID / criterion | Meaning and why it matters | Raw fields / evidence | Source codes | Public? | H/C/T/A |
|---|---|---|---|---|---|
| C01 Independent demand breadth | Reach across separate creators reduces single-winner dependence | V,P,C,network annotation | V/CH/HU | Partial | YNNY |
| C02 Useful absolute reach | Outcomes relevant to the creator goal prevent tiny-baseline false positives | V,P,goal G | V | Yes | YNNN |
| C03 Observed reach ceiling | High comparable outcomes identify potential scale without pretending to count people | V,P,topic/creator flags | V/HU | Partial | YNNY |
| C04 Recent demand persistence | Distinct windows test whether attention is recurring | V,P,snapshot T,topic | V/HS | Partial | YNNN |
| C05 Demand across topic families | Several viable subjects reduce one-event dependence | Titles,topic tags,V,P | V/TR/HU | Partial | YNNY |
| C06 Older-catalog demand | Incremental old-video reach tests persistence rather than lifetime popularity | V,T,P,old-age flag | V/HS | Partial | YNNN |
| C07 Viewer question demand | Repeated requests identify useful explanatory needs | Comment text/order/date;video context | CM/TR/HU | Partial | NYNY |
| C08 External search trend | Directional interest adds context beyond video winners | Query/property/region/window/index | GT | Partial | YNNY |
| C09 Observed active supply | Active qualifying creators describe the sampled competitive field | C,P,eligibility,query manifest | SE/PL/V | Partial | NNNN |
| C10 Upload pressure | Current production rates indicate how quickly relevant supply arrives | C,P,eligibility | PL/V | Yes | NNNN |
| C11 Observed supply growth | Repeated discovery detects change in sampled supply | Query manifest,C,P,T | SE/PL/HS | Partial | YNNN |
| C12 Channel concentration | Dependence on a few creators helps assess accessibility | V,C,P | V/CH | Partial | YNNN |
| C13 Entry barriers | Rights, reputation or access may prevent practical competition | Sources/assets/expertise/resource brief | HU/TR/TH | Partial | NNYY |
| C14 Competitive differentiation | A feasible distinct treatment tests effective competition | Need,current alternatives,original proposal | HU/TR/TH/CM | Partial | NYYY |
| C15 Repeated packaging density | Crowded title/visual conventions indicate execution pressure | Title,thumbnail,topic/format labels | V/TH/HU | Partial | NNYY |
| C16 Current small-channel status | Current size stratifies beginner-relevant references | S,hidden flag,C | CH | Yes | NNNN |
| C17 Account age | Old accounts are separated from new channel creation | Channel join timestamp,C,T | CH | Yes | NNNN |
| C18 First observed niche-entry age | Actual subject activity is more relevant than account age | Oldest qualifying P,titles,history coverage | PL/V/TR/HU | Partial | YNNY |
| C19 Size at publication | Pre-outcome size prevents post-treatment labeling | S,T,P | CH/HS/AP | Partial | YNNY |
| C20 Independent small-entry success | Repeated entrant outcomes test accessibility | Entry,S_at_pub,V(30),C | CH/V/HS | Partial | YNNN |
| C21 Time to first useful result | Entry-to-first-goal timing tests fast growth | Entry,P,V(30),censor flag | PL/V/HS | Partial | YNNN |
| C22 First-five-upload outcomes | Early upload sequence reveals accessibility beyond winners | Chronology,V(30),eligibility | PL/V/HS | Partial | YNNN |
| C23 Relative breakout lift | Unusual channel outcomes identify leads | V(30),baseline uploads,P,C | V/HS | Partial | YNNN |
| C24 Peer performance standing | Comparable references put a breakout in context | V(30),size/entry/format,reference set | V/CH/HS | Partial | YNNN |
| C25 Outlier density | Frequency matters only with a fixed eligible denominator | Goal/lift flags,eligible count,C | V/HS | Partial | YNNN |
| C26 Typical viewing floor | Ordinary uploads reveal downside and production sustainability | V(30),C,eligibility | V/HS | Partial | YNNN |
| C27 Top-hit dependence | One hit may mask a weak catalog | V,C,P,catalog coverage | V/PL | Partial | YNNN |
| C28 Next-five repeatability | Follow-through tests whether a breakout repeats soon | Breakout chronology,next5,V(30) | PL/V/HS | Partial | YNNN |
| C29 Next-ten repeatability | Longer follow-through separates a spike from a pattern | Breakout chronology,next10,V(30) | PL/V/HS | Partial | YNNN |
| C30 Post-hit topic drift | Changed content offers an alternative explanation for decline | Titles,transcript,topic/format chronology | V/TR/HU | Partial | YNNY |
| C31 Stopped/stagnant public activity | Low outcomes and no uploads preserve weak cases | P,V(30),C,last observed date | PL/V/HS | Partial | YNNN |
| C32 Faceless production fit | Intended presentation can avoid recurring on-camera host | Representative scenes,transcript,resource brief | HU/TR/TH/AP | Partial | NNYY |
| C33 Named-person dependency | Celebrity voice/fame can undermine independent entry | Scenes,title,narration,asset provenance | HU/TR/TH | Partial | NNYY |
| C34 Long-form eligibility | Correct formats and durations keep comparisons meaningful | D,P,live/Shorts/language labels | V/PL/AP | Partial | NNNY |
| C35 Runtime outcome association | Length segments describe observed results without fake retention | D,V(30),topic/format,size | V/CH/HS | Partial | YNNN |
| C36 Topic depth | Distinct credible premises prevent rapid exhaustion | Topic premises,sources,payoff,visual plan | HU/TR | Partial | NNNY |
| C37 Format repeatability | A repeatable method reduces reinvention burden | Structure,source availability,topic variation | TR/HU | Partial | NNNY |
| C38 Semantic evergreen character | Durable subject matter is a planning clue | Topic,update requirements,source dates | HU/TR | Partial | NNNY |
| C39 Seasonality | Recurring timing can explain demand variation | V(30) cohorts,T,P,trend context | HS/GT | Partial | YNNY |
| C40 Trend production fit | Urgency must fit research/visual lead time | Event dates,interest trend,pilot hours | HU/GT/HS | Partial | YNNY |
| C41 Video shelf-life | Ongoing increments measure persistence of a release | V,T,P,definition regime | V/HS | Partial | YNNN |
| C42 Validated content gap | An underserved need requires demand and feasible differentiation | Need,alternatives,comments,topics,resources | CM/TR/TH/HU | Partial | NYYY |
| C43 Adjacent-topic fit | Nearby audience tasks can expand ideas without random drift | Topic/promise similarities,examples | V/TR/HU/AP | Partial | NNNY |
| C44 Title mechanisms | Recurring truthful promises support original packaging research | Title,topic/format labels | V/TR/HU | Partial | NNNY |
| C45 Thumbnail clarity and distinction | Visual hierarchy matters but requires actual inspection | Thumbnail pixels,title,context examples | TH/HU | Partial | NNYY |
| C46 Packaging-change observations | Changes are useful history but not causal experiments | Title/thumb versions,T,V,T | V/TH/HS/AP | Partial | YNYY |
| C47 Series coherence | An ongoing payoff can support sustainable followups | Titles,playlists,transcripts,next ideas | PS/TR/HU | Partial | NNNY |
| C48 Playlist structure | Public organization is a proxy for navigation opportunities | Playlist membership/order/title | PS | Yes | NNNN |
| C49 Series outcome persistence | Comparable-age sequels describe sequence outcomes | Episode labels,P,V(30) | PS/V/HS/HU | Partial | YNNY |
| C50 Research burden | Evidence access and verification determine practical costs | Source availability,claims,pilot hours | HU/TR | Partial | NNNY |
| C51 Visual burden | Scenes/maps/assets may dominate effort | Visual plan,scenes,asset access,pilot hours | HU/TH/TR | Partial | NNYY |
| C52 Narration and identity fit | Credible voice and continuity matter without a visible host | Audio/style sample,expertise,resource plan | HU/TR/AP | Partial | NNNY |
| C53 Production capacity | Cadence must fit hours,skills,cost and revisions | Task hours/cost,available resources | HU | No | NNNY |
| C54 Source-access moat | Exclusive/expensive evidence can block similar output | Research paths,archives,credentials/access | HU/TR | Partial | NNNY |
| C55 Original contribution | Meaningful analysis/storytelling avoids shallow replication | Drafts,sources,structure,visual plan | HU/TR | Partial | NNNY |
| C56 Asset-rights feasibility | Availability is different from lawful usable assets | Asset licenses,permissions,attribution | HU/AS | Partial | NNNY |
| C57 Partner-linked content flag | Metadata clue can direct rights review without false accusation | licensedContent;license field | V | Yes | NNNN |
| C58 Inauthentic/reused-content exposure | Production pattern may conflict with monetization policies | Channel pattern,original contribution,asset plan | HU/TR/TH | Partial | NNYY |
| C59 Advertiser suitability exposure | Sensitive context can constrain the chosen business model | Topic/scene/context and current guidance | HU/TR | Partial | NNNY |
| C60 Synthetic-media disclosure need | Realistic altered/generated scenes require contextual review | Intended scenes/audio,realism/context | HU | Partial | NNNY |
| C61 Factual credibility burden | High-stakes/historical claims need sourcing despite popularity | Claims,primary sources,uncertainty | HU/TR/AS | Partial | NNNY |
| C62 Measured view velocity | Recorded growth informs timing | V,T,precision/regime | V/HS | Partial | YNNN |
| C63 Measured acceleration | Changing increments can reveal a surge | V,T,precision/regime | V/HS | Partial | YNNN |
| C64 Channel subscriber growth | Public channel increments add context but not per-video conversion | S,T,hidden/rounding,Vchannel | CH/HS | Partial | YNNN |
| C65 Comment velocity | Observed comments change with attention and moderation | Comment count,T,V | V/CM/HS | Partial | YYNN |
| C66 Public engagement descriptors | Likes/comments give context but not retention/satisfaction | Like/comment counts,V,T | V | Yes | YNNN |
| C67 Language verification | Actual English audience content differs from ASCII-title filtering | Audio language,transcript,title,language flags | V/TR/HU/AP | Partial | NNNY |
| C68 Localized underserved need | Region-specific tasks may support differentiated ideas | Localized needs,alternatives,query settings | SE/CM/TR/HU/GT | Partial | NYNY |
| C69 Sample coverage | Enumeration and missing records determine what claims are possible | Query manifest,page tokens,counts,errors | SE/PL/CH/AP | Partial | NNNY |
| C70 Independent sample size | Many videos from few creators remain dependent | C,network flags,eligible count | CH/HU | Partial | NNNY |
| C71 Timestamp/count precision | Exact dates and rounded counts alter chronology/rates | Raw date/count strings,details,T | V/PL/AP/HS | Yes | YNNY |
| C72 Provider disagreement | Different sources must be reconciled or flagged | Same IDs,source timestamps,raw fields | AP/V/CH/PL | Yes | YNNY |
| C73 Metric counting regime | Changed view definitions invalidate naive temporal comparisons | Definition version,P,T,source changelog | V/HS/HU | Yes | YNNY |
| C74 Sensitivity robustness | Decision stability tests arbitrary defaults | Repeated queries,cohorts,goals,weights | All permitted inputs | Partial | YNNY |
| C75 Opportunity prioritization index | Transparent components can organize a shortlist | Demand/entry/floor/repeat/fit/depth | All permitted inputs | Partial | YNNY |
| C76 Evidence confidence | Coverage/comparability matter independently of opportunity | Coverage,precision,history,source agreement | All permitted inputs | Partial | YNNY |
| C77 API/provider permission state | Technically observable data may be restricted in use/storage | Audit acceptance,accepted scope,contracts | Policy/contract records | No | NNNY |
| C78 Exact competitor search volume | Public API has no actual niche query-volume count | Unavailable raw query counts | None | No | NNNN |
| C79 Competitor impressions/CTR | Private exposure/click rates cannot be read from public views | Private impressions/clicks | OA | No | NNNY |
| C80 Competitor retention/watch time | Private viewing curves cannot be inferred from runtime/views | Private watch/retention reports | OA | No | NNNY |
| C81 Competitor returning viewers/binge | Public series structure does not measure repeat sessions | Private audience/session reports | OA | No | NNNY |
| C82 Competitor traffic sources/search terms | Views above subscriber count do not identify distribution | Private traffic/query reports | OA | No | NNNY |
| C83 Actual competitor revenue/RPM | Financial outcomes require private data or verified disclosure | Private revenue/monetized views | OA/AP | No | NNNY |
| C84 Competitor audience country/income | Creator country and language do not reveal audience mix | Private geography;income unavailable | OA | No | NNNY |
| C85 Per-video subscriber conversion | Channel subscriber change is not video-attributed gain | Private attributed subscribers/views | OA | No | NNNY |
| C86 Public dislike ratio | Dislike counts are not public basic API data | Private dislike count | OA | No | NNNY |
| C87 Guaranteed niche success probability | Selected winners and anecdotes cannot produce a validated probability | Representative future outcome panel absent | None | No | NNNN |
| C88 Automatic copyright-violation score | Partner flags and asset appearance cannot establish infringement | Permissions/context/rights unknown | None | No | NNNY |
| C89 Algorithm favoritism score | Public counts do not expose recommendation weights or causal push | Private model/exposure unknown | None | No | NNNN |

## B. Formula, operating window, sample, defaults and implementation

Formula IDs refer to blueprint Section28, which supplies purpose, normalization, interpretation, failure cases and worked examples. Rubrics are human assessments, not public platform metrics. Quota is determined by the source codes in A; the entry below identifies additional collection work beyond hydrated current metadata.

| ID | Formula / scoring approach | Window | Minimum sample | Suggested threshold / default | Caveat / limitation | Quota implication | Difficulty | Priority / Tier |
|---|---|---|---|---|---|---|---|---|
| C01 | F8 | 90-day publication cohort;30-day outcome | 10 independent channels exploratory | ≥3 independent repeat winners is a hypothesis | Common ownership and selection can overstate independence | Snapshots add V/CH calls; Provider/human costs separate | Medium | Must Have / 1 |
| C02 | F3 | 30 days;7/90 secondary | 20 mature eligible videos exploratory | Example G10k;test5k/25k | No universal profitable-view level | Snapshots add V/CH calls | Easy | Must Have / 1 |
| C03 | Matched-age P90/P95 | 90-day cohort;30-day outcomes | 50 videos;10 channels exploratory | No universal ceiling cutoff | Celebrity and external-traffic examples can mislead | Snapshots add V/CH calls; Provider/human costs separate | Medium | High Value / 2 |
| C04 | F11 plus breadth | Two90-day cohorts | 10 channels/window preferred | Direction with sensitivity, no fixed ratio | Season and cohort mix confound | Snapshots add V/CH calls | Medium | High Value / 2 |
| C05 | Count validated successful families | 90/365-day cohorts | 3 families;10 channels exploratory | ≥3 families proposed | Classification and missing topics affect count | Snapshots add V/CH calls; Provider/human costs separate | Medium | Must Have / 1 |
| C06 | F13 | 30-day tracking;videos≥90 days | 10 old videos preferred | No universal catalog-share cutoff | Current totals cannot reconstruct increments | Snapshots add V/CH calls | Medium | High Value / 2 |
| C07 | Deidentified validated question clusters | Recent comments plus 90-day videos | ≥100 comments across 5 videos preferred | Repeated need across≥2 videos as lead | Commenters are selected and may be noisy | Comment/reply pages; Provider/human costs separate | Medium | High Value / 2 |
| C08 | Directional normalized-index comparison | 12–24 months | One full cycle;two preferred | No raw-volume interpretation | Separate normalized extracts not absolute comparisons | Snapshots add V/CH calls; Provider/human costs separate | Easy | Optional / 4 |
| C09 | Count distinct active qualifying channels | Last 90 days | 10 channels exploratory | No saturation cutoff | Search/index coverage is incomplete | Search/page budget; Upload pagination | Easy | Must Have / 1 |
| C10 | Uploads/channel/week;median and distribution | 90 days | 10 active channels | No mandatory creator cadence | Availability and eligibility affect denominator | Upload pagination | Easy | High Value / 2 |
| C11 | F12 | At least2 repeated windows;3 preferred | Stable protocol and cohort | No universal growth cutoff | New indexing is not new production | Snapshots add V/CH calls; Search/page budget; Upload pagination | Medium | High Value / 2 |
| C12 | F9;top1/top3 creator shares | 30-day outcomes within90-day cohort | 10 independent channels | No universal HHI barrier | Sample concentration is not platform market share | Snapshots add V/CH calls | Easy | High Value / 2 |
| C13 | Component rubric with hard constraints | Current production plan | 3 contrasting production references | Reject proven infeasible method | Costs and private access often unknown | Image/visual costs outside API; Provider/human costs separate | Hard | Must Have / 1 |
| C14 | Gap-validation rubric | Current alternatives;90 day evidence | 3 alternatives;2 independent demand leads | Specific difference required | Distinct appearance alone may add no value | Comment/reply pages; Image/visual costs outside API; Provider/human costs separate | Hard | Must Have / 1 |
| C15 | Mechanism counts;visual similarity descriptors | 90 days | 30 videos;5 channels | No numeric saturation cutoff | Similarity is not audience fatigue or rights violation | Image/visual costs outside API; Provider/human costs separate | Medium | High Value / 2 |
| C16 | Declared subscriber bands | At capture | Each channel | <50k focus;<100k sensitivity | Rounded/hidden and post-outcome size | Reuse hydrated metadata;no incremental API for calculation | Easy | Must Have / 1 |
| C17 | Observation minus creation | At capture | Each channel | Report only;no automatic rejection | Rebrands/transfers/deletion unknown | Reuse hydrated metadata;no incremental API for calculation | Easy | Must Have / 1 |
| C18 | Entry-age bands with uncertainty | 0–6/6–12/12–24/24–36 months | Oldest coverage verified perchannel | ≤12 months focus, heuristic | First observed is not necessarily first ever | Snapshots add V/CH calls; Upload pagination; Provider/human costs separate | Medium | Must Have / 1 |
| C19 | Nearest historical observation plus timing gap | Near publication | One supported size observation/video | Unknown if not recorded | No exact reconstruction from current size | Snapshots add V/CH calls; Provider/human costs separate | Hard | Must Have / 1 |
| C20 | F4 stratified by entry/size | Fixed entry horizon;30-day outcomes | 20 channels exploratory;30 preferred | ≥3 independent repeat winners proposed | Selected samples do not yield population probability | Snapshots add V/CH calls | Hard | Must Have / 1 |
| C21 | Time-to-observed goal;show censoring | 6/12 month entry horizons | 20 entrants preferred | No guaranteed timeframe | Late discovery and unavailable history bias timing | Snapshots add V/CH calls; Upload pagination | Hard | High Value / 2 |
| C22 | First-five goal count and floor | First5 eligible uploads | 5 mature uploads/channel | Partial/pending if fewer | Deleted uploads and episode quality unknown | Snapshots add V/CH calls; Upload pagination | Medium | High Value / 2 |
| C23 | F1/F2 | Same publication age/format/era | 10 refs preferred;5 exploratory | 3× exploratory plus absolute goal | Tiny baselines and trend shifts mislead | Snapshots add V/CH calls | Medium | Must Have / 1 |
| C24 | External-reference percentile | 30-day outcomes;90 day cohorts | 30 peer videos;10 channels preferred | P90 exploratory, not own-niche guarantee | Within-niche percentile is tautological cross-niche | Snapshots add V/CH calls | Medium | High Value / 2 |
| C25 | Qualifying uploads /all eligible;channel-balanced too | 90 day mature cohort | 50 videos;10 channels | No universal density cutoff | Winner feed and dynamic thresholds bias denominator | Snapshots add V/CH calls | Medium | High Value / 2 |
| C26 | F5;median/Q25/low-view share | 30-day outcomes | 5 uploads/channel;10 channels preferred | Goal-linked floor, no universal threshold | Age-mixed lifetime fallback is approximate | Snapshots add V/CH calls | Medium | Must Have / 1 |
| C27 | F6 | Same-age preferred;lifetimes labeled | 10 eligible videos preferred | High share triggers review, not automatic reject | Incomplete catalog and age skew | Snapshots add V/CH calls; Upload pagination | Easy | Must Have / 1 |
| C28 | F7 k5 | Next5 at same age | 5 matured or explicit partial | No fixed success fraction validated | Censoring, topic drift and missing uploads | Snapshots add V/CH calls; Upload pagination | Medium | Must Have / 1 |
| C29 | F7 k10 | Next10 at same age | 10 matured or explicit partial | No universal fraction validated | A stopped channel is not ten zero-view videos | Snapshots add V/CH calls; Upload pagination | Medium | Must Have / 1 |
| C30 | Human-confirmed drift annotation | Next5/10;90 days | Breakout and≥5 followups preferred | Annotate;do not causal-score | Intent and audience overlap unknown | Snapshots add V/CH calls; Provider/human costs separate | Medium | High Value / 2 |
| C31 | No-public-upload status and cohort floor | 90 days;context365days | Coverage verified | No permanent-failure label | Private activity and creator intentions unknown | Snapshots add V/CH calls; Upload pagination | Easy | Must Have / 1 |
| C32 | Style classification with confidence | Current and earlier samples | 3 videos/channel;beginning/middle/later preferred | Provider label stays tentative | A thumbnail or opening is not whole-channel proof | Image/visual costs outside API; Provider/human costs separate | Hard | Must Have / 1 |
| C33 | Dependency rubric | Representative current samples | 3 videos preferred | Review rights and replacement path | No automatic violation or earnings inference | Image/visual costs outside API; Provider/human costs separate | Medium | High Value / 2 |
| C34 | Duration bands;exclude known live/Shorts | At publication/capture | Every candidate | ≥8min;test6/10 | No universal API Shorts flag;duration alone incomplete | Upload pagination; Provider/human costs separate | Easy | Must Have / 1 |
| C35 | Stratified outcomes by duration band | 90 day cohort;30 day outcomes | 20 videos/band exploratory | No universal best runtime | Confounding and selection;not causal optimum | Snapshots add V/CH calls | Medium | High Value / 2 |
| C36 | F15 plus family counts | Planned first30 uploads | 30 candidates;≥10 human checks | ≥3 feasible families proposed | Generated ideas can be redundant or false | Provider/human costs separate | Medium | Must Have / 1 |
| C37 | Repeatability rubric and pilot | First10/30 planned uploads | 3 completed outlines/pilot estimates | Feasible cadence, creator-specific | Template reuse can become repetitive output | Provider/human costs separate | Medium | Must Have / 1 |
| C38 | Durability/update-debt annotation | 12 month planning | 10 representative topics | No quantitative evergreen score as fact | Semantic durability is not observed shelf-life | Provider/human costs separate | Medium | High Value / 2 |
| C39 | Repeated-cycle comparison | 12–24 months | 1 cycle minimum;2 preferred | Insufficient history if absent | Regime/cohort/production changes confound | Snapshots add V/CH calls; Provider/human costs separate | Hard | High Value / 3 |
| C40 | Time-to-publish versus useful window | Current event lifecycle | 3 historical comparisons preferred | Reject clearly infeasible deadline | Future decay uncertain | Snapshots add V/CH calls; Provider/human costs separate | Medium | High Value / 2 |
| C41 | Increment curve;F13 contextual | 30/90/180 day tracking | 10 comparable videos preferred | No universal half-life | Monotone decay assumption can fail | Snapshots add V/CH calls | Hard | High Value / 3 |
| C42 | Gap evidence card | Current alternatives;90/365 day demand | 2 independent leads;3 alternatives | Positive demand required | Absence in search is not a gap | Comment/reply pages; Image/visual costs outside API; Provider/human costs separate | Hard | Must Have / 1 |
| C43 | Similarity plus human task fit | 90/365 day references | 5 relevant examples;≥2 creators | No private audience-overlap claim | Algorithmic similarity may be shallow | Provider/human costs separate | Medium | High Value / 2 |
| C44 | Mechanism clusters | 90 days;historical context | 30 titles;5 channels | No predicted CTR | Topic and brand confound performance | Provider/human costs separate | Medium | High Value / 2 |
| C45 | Human rubric at realistic size | Current plus comparable examples | 10 thumbnails;3 channels | No universal word/color rule | Views cannot establish CTR effect | Image/visual costs outside API; Provider/human costs separate | Medium | High Value / 2 |
| C46 | Version timeline and context | Tracked before/after | ≥2observed versions | No causal lift claim | Refresh retention and coincident distribution | Snapshots add V/CH calls; Image/visual costs outside API; Provider/human costs separate | Hard | High Value / 3 |
| C47 | Structural coherence rubric | Current portfolio/planned10 | 3 linked episodes preferred | Standalone comprehension plus recurring payoff | Coherence is not actual binge behavior | Playlist pages; Provider/human costs separate | Medium | High Value / 2 |
| C48 | Count/structure annotations | Current playlists | Complete selected playlists | No binge/session inference | Private/unlisted organization inaccessible | Playlist pages | Easy | Optional / 4 |
| C49 | Episode floor/trend by series | 3–10 episode sequences | 3 mature episodes exploratory | No universal sequel ratio | Viewer overlap and causality unknown | Snapshots add V/CH calls; Playlist pages; Provider/human costs separate | Medium | High Value / 2 |
| C50 | Task hours/costs;F16 | 3 topic estimates and pilot | 3 contrasting topics | Creator-resource fit required | Public titles cannot reveal actual budget | Provider/human costs separate | Hard | Must Have / 1 |
| C51 | Task hours/asset feasibility;F16 | Representative pilot plus 3 topics | 2 short visual samples exploratory | Explicit feasible asset path | Sample style may not represent whole channel | Image/visual costs outside API; Provider/human costs separate | Hard | Must Have / 1 |
| C52 | Voice/authority rubric | Pilot and3references | 3 samples preferred | No generic AI-voice success rule | Provider audio judgments can err | Provider/human costs separate | Medium | High Value / 2 |
| C53 | F16 | Weekly/monthly resource plan | Timed pilot;3 estimates | No mandatory daily/weekly cadence | Setup,overhead and revision variance | Provider/human costs separate | Medium | Must Have / 1 |
| C54 | Access feasibility rubric | Current and planned30topics | 3source paths;rights checks | Reject plan needing unavailable essentials | Do not assume competitor budget/access | Provider/human costs separate | Hard | High Value / 2 |
| C55 | Human originality/evidence review | Pilot plus series plan | 3 premises and draft sample | Distinct substantive contribution required | No automatic platform approval prediction | Provider/human costs separate | Hard | Must Have / 1 |
| C56 | Asset-specific rights checklist | Each intended asset/method | Every essential asset class | Reject unavailable essential rights | Fair-use/ownership cannot be inferred from public viewability | Provider/human costs separate | Hard | Must Have / 1 |
| C57 | Raw flag plus caveat | At capture | Every relevant video | No violation/reuse conclusion | Flag means partner-linked claim, not blanket permission | Reuse hydrated metadata;no incremental API for calculation | Easy | Optional / 4 |
| C58 | Current-policy review | Pilot and planned catalog | 3 representative videos and method | No automatic AI/faceless rejection | YPP adjudication is private/contextual | Image/visual costs outside API; Provider/human costs separate | Hard | Must Have / 1 |
| C59 | Separate suitability rubric | Current plan | 3 representative topics | Secondary to growth;no rival RPM inference | Cannot infer actual ad decisions from metadata | Provider/human costs separate | Hard | High Value / 2 |
| C60 | Current-policy review by scene | Every relevant planned scene | All realistic altered scenes | Disclose when current rules require | Public absence of label is not proof of violation | Provider/human costs separate | Medium | Must Have / 1 |
| C61 | Claim-source reconciliation | Every material claim;pilot | All key claims,not only hook | No invented evidence | Transcript popularity is not factual validation | Provider/human costs separate | Hard | Must Have / 1 |
| C62 | F10 | 24h/7 day exact intervals | 2 snapshots | Unavailable without history | Rounded counts,late discovery and corrections | Snapshots add V/CH calls | Medium | High Value / 2 |
| C63 | F10 | Equal consecutive intervals | 3 snapshots | No tiny-count trigger alone | Noisy differences and regime breaks | Snapshots add V/CH calls | Medium | High Value / 3 |
| C64 | ΔS/Δt;optional ΔS/ΔV | 30/90 days | 2 snapshots;rounding checked | Rename growth descriptor | Public rounding hides small increments;causal source unknown | Snapshots add V/CH calls | Medium | Optional / 4 |
| C65 | Δcomments/Δt | 24h/7 days | 2 snapshots | Optional contextual metric | Deleted/held/spam comments distort | Snapshots add V/CH calls; Comment/reply pages | Medium | Optional / 4 |
| C66 | F14 | Same-age or same observation | 20 videos preferred | No universal quality threshold | Bots/controversy/denominator regime | Snapshots add V/CH calls | Easy | Optional / 4 |
| C67 | Confidence label with source | Every finalist | Audio/transcript check where possible | Unknown when unverified | Metadata can be missing or mixed-language | Provider/human costs separate | Medium | Must Have / 1 |
| C68 | Gap rubric;matched query comparisons | Current localized cohort | 3 variants/location;2demand leads | No viewer-country inference | RegionCode controls viewability;not viewer distribution | Search/page budget; Comment/reply pages; Provider/human costs separate | Hard | High Value / 2 |
| C69 | Retrieved/available scope;unresolved gaps | Every run | All collection paths logged | No complete flag from one page | Counts conflict;private/deleted scope unknown | Search/page budget; Upload pagination; Provider/human costs separate | Medium | Must Have / 1 |
| C70 | Channels/creator groups;effective count | Defined cohort | ≥20 channels exploratory;30preferred | Report count,not confidence guarantee | Unknown common ownership | Provider/human costs separate | Medium | Must Have / 1 |
| C71 | Precision flags;interval bounds | Every observation | All critical fields | Detail enrich before follow-up order | Relative-label dates can cluster on month start | Snapshots add V/CH calls; Upload pagination; Provider/human costs separate | Easy | Must Have / 1 |
| C72 | Conflict log and preferred-source rule | Same capture period | Every finalist | Unresolved stays flagged | Differences can reflect coverage/cache/definitions | Snapshots add V/CH calls; Upload pagination; Provider/human costs separate | Medium | Must Have / 1 |
| C73 | Regime segmentation and sensitivity | Across2026-08 transition | Every temporal series | No universal conversion factor | Cumulative totals blend earlier and newer counting | Snapshots add V/CH calls; Provider/human costs separate | Medium | Must Have / 1 |
| C74 | F18 | Each research run | ≥5 predeclared variants;10preferred | Report flips and reasons | Biased variants can agree | Snapshots add V/CH calls; Provider/human costs separate | Hard | Must Have / 1 |
| C75 | F17 | Same cohort/version | Essentials complete | Illustrative weights;unscored if essentials unknown | Correlated components and arbitrary weights | Snapshots add V/CH calls; Provider/human costs separate | Hard | Optional / 4 |
| C76 | Dimension rubric;cluster intervals where valid | Every result | Independent mature evidence required | High/Moderate/Low rubric | No guaranteed population-confidence percentage | Snapshots add V/CH calls; Provider/human costs separate | Hard | Must Have / 1 |
| C77 | Capability gate and retention schedule | Before implementation;on changes | Verified scope record | Unknown → dependent feature disabled | Provider availability does not establish permission | Provider/human costs separate | Medium | Must Have / 1 |
| C78 | Do not calculate | Not available | Not applicable | Reject as public input | Search totals and Trends indices are different | Do not request unavailable public metric | Easy | Reject / 5 |
| C79 | Owner-only analysis if separately authorized | Owner-defined | Authorized owner data | Reject competitor estimate as fact | Public packaging success has many confounders | Provider/human costs separate | Easy | Reject / 5 |
| C80 | Owner-only analysis | Owner-defined | Authorized owner data | Reject public rival score | Duration and comments do not reveal watch time | Provider/human costs separate | Easy | Reject / 5 |
| C81 | Owner-only analysis | Owner-defined | Authorized owner data | Reject public rival count | Playlists are structure proxies only | Provider/human costs separate | Easy | Reject / 5 |
| C82 | Owner-only analysis | Owner-defined | Authorized owner data | Reject algorithm-push inference | Search/browse/external source unavailable publicly | Provider/human costs separate | Easy | Reject / 5 |
| C83 | Optional labeled scenarios only | Owner/provider defined | Verified owner or explicit assumptions | Reject provider estimate as actual | YPP status and ad display do not prove earnings | Provider/human costs separate | Easy | Reject / 5 |
| C84 | No protected/unsupported profiling | Not publicly available | Not applicable | Reject inference from comments/region | Income/private audience traits cannot be established | Provider/human costs separate | Easy | Reject / 5 |
| C85 | Owner-only attributed analysis | Owner-defined | Authorized owner data | Reject public conversion claim | Other videos/external channels/rounding confound | Provider/human costs separate | Easy | Reject / 5 |
| C86 | No public satisfaction ratio | Not public | Not applicable | Reject public substitute | Third-party estimates are separate uncertain data | Provider/human costs separate | Easy | Reject / 5 |
| C87 | Do not produce | Not established | Prospective validation needed | Reject guarantee | Confidence rubric is not probability of success | Do not request unavailable public metric | Hard | Reject / 5 |
| C88 | Human asset-risk review only | Case-specific | Actual rights evidence | Reject automated verdict | Avoid unsupported accusations | Provider/human costs separate | Hard | Reject / 5 |
| C89 | Do not calculate | Not established | Not applicable | Reject claim | Observed reach is not a causal algorithm explanation | Do not request unavailable public metric | Hard | Reject / 5 |

## Policy, retention and missing-data behavior

All scoring/aggregation/history designs are conditional on the capabilities described in blueprint Section17. The additional-metrics acceptance is not established for the user's MCP. Verify scope rather than treating this report as permission. Keep raw public facts, own derived measures and provider estimates visibly distinct.

Use structured states: `available`, `approximate`, `partial_coverage`, `pending_maturity`, `insufficient_sample`, `insufficient_history`, `classification_unknown`, `source_conflict`, `policy_permission_required`, `owner_authorization_required`, and `not_publicly_available`. A disabled or unknown metric is never zero. An approximate proxy never silently replaces the named private metric.

Special cases: `licensedContent` is a partner-linked content flag, not a rights verdict; public subscriber counts can be rounded/hidden; search region/language settings do not measure audience geography/language; captions need authorized or auxiliary access; public playlists do not reveal binge sessions; daily provider zeros can be missing/unsupported values. These limits are covered by the linked primary references and the evidence ledger's actual conflicts.

## Verification before implementation

Hand-check exact fields and date precision against several conflicting NexLev cases. Confirm pagination and missing-ID/error handling. Reconcile counts only within equivalent public scopes and capture dates. Ensure same-age comparisons never backfill missing history, and that follow-up denominators expose maturity and coverage. Then inspect the actual MCP code before classifying features as implemented, correct, missing or broken.

The register covers public research criteria, creator-plan inputs, historical/auxiliary enhancements and expressly rejected public-data claims. New criteria should use this same schema and an evidence/permission state before being added to a composite.
