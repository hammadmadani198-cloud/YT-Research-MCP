# Phase 5 qualitative contract — phase5-v1

Written before production implementation, 2026-10-02. The clean starting checkpoint is
b53e5bfacf33ce581f3f7ba7e5eaeaee990f5486. The seven preserved research documents are
authoritative; this phase adds descriptive and feasibility axes, never a recommendation.

## Common evidence contract

Every review has an immutable ID, boundary/taxonomy version, source type, reviewer,
material IDs, input dependencies, available/decision timestamps, confidence, concise
rationale, limitations, rubric/version, expiry and reproducible sample manifest.
Confidence describes the annotation only; it is not F18. Model reviews additionally
require model and prompt versions. Provider/model reviews are attributed interpretations,
not observed facts. Human review is permitted for every qualitative dimension.

Only structured derivations are stored: no full transcript, comment body, thumbnail,
chain of thought, personal commenter identity or allegations. Restricted provider text
requires the existing retention permission and bounded input expiry; contract_review_required
cannot be bypassed. Removing/revoking/expiring an input invalidates all its derivatives.
Normal execution and tests are offline. Existing F1–F13, floor and F19–F22 stay frozen.

| Dimension / research source | Required evidence and minimum | Semantics / missing / confidence | Status and permitted review |
|---|---|---|---|
| F14 / Blueprint §28, Matrix C36–37, ledgers | Official public counts from one capture selected at the same publication age; numerator, denominator, clocks, missingness. Prefer ≥20 comparable videos. | 1000 likes/views and 1000 comments/views; per-channel medians. Zero denominator or unavailable field gives unknown. Descriptive, never satisfaction or retention. | Public facts only; comment themes can be human/model annotations, provider auxiliary. |
| Comment themes / Blueprint §13, Matrix C36–37 | Deidentified categories with video, route, ordering, page/sample count, retrieval time, reply/deleted/disabled state. One reviewed sample suffices for a sample-only theme. | Questions, confusion, objections, followups, vocabulary, trust friction; no representative sentiment/demand percentage. Coverage and local confidence required. | Public sample or explicitly permitted provider derivation; no raw text. |
| F15 / Blueprint §28, Matrix C42–59 | Generated candidate inventory; reviewed subject, promise, mechanism, long-form treatment, checked sources, production path, taxonomy family/premise nodes. ≥10 human reviews and every finalist preferred; 30 candidates is a planning example. | Validated distinct premises / generated candidates. Reviewed same/near duplicates merge; uncertain remains unresolved. Classification, duplicate density, source support and unknowns reported separately. Missing review is not a validated idea. | Decision-supporting review; human confirmation required for validation/canonical merging. Similarity T4 auxiliary only. |
| Content gaps / Blueprint §13, Updated Prompt | Positive demand, reviewed inadequate supply, feasible differentiation and checked sourcing/production. Comments alone insufficient for confirmation. | supported_gap, possible_gap, saturated, insufficient_demand_evidence, insufficient_supply_evidence, insufficient_differentiation, unknown. Content, packaging and production gaps stay separate. | Decision support; reviewed human corroboration required for supported_gap; provider/model alone remains possible. |
| Saturation / Blueprint §13, Matrix | Canonical premise relations, dated publication wave and explicitly linked observed outcomes from prior analyses. | Descriptive similarity and weak/strong observed treatments; no copying intent, competition-count score or causal claim. Unknown chronology/outcomes remain explicit. | Public + canonical human review; T4 similarity auxiliary. |
| Packaging / Blueprint §14, Updated Prompt | Reviewed title mechanism, length/promise; thumbnail composition, face, dominant asset, text density. | Counts of public patterns; unknown unreviewed media. Homogeneity/differentiation, never CTR. | Parser/human/model; T4 visual similarity descriptive only. No media storage. |
| Series / Blueprint §15 | Reviewed compatible premise links, recurring entities/families, chronology/geography/comparison/rise-fall/investigation structure and exhaustibility. | Continuation graph and depth; playlists alone never prove bingeing, retention or audience overlap. | Descriptive structural review, human/model/provider attribution. |
| F16 / Blueprint §16, §28, Matrix, Third Pass Gap Audit | Task estimates or timed pilot for research, sourcing, script, visuals, rights, edit, narration, expertise, updates, revisions/overhead; currency and cash separate from labor. Prefer timed pilot +3 contrasting cases. | Hours/release and weekly capacity = declared hours/week / task hours/release, before additional overhead. Missing tasks disclosed. No opaque difficulty score. | Creator/human/model estimates with local confidence; no assumed creator budget/skills. |
| Creator compatibility / Blueprint F16 | Optional declared hours/week, monthly cash, cadence, skills, narration, animation, footage, team. | Unknown without profile; compatibility separate from unchanged underlying burden. Missing constraints remain unresolved. | Explicit creator inputs only; compatibility is declared-scenario support, not recommendation. |
| Faceless feasibility / Blueprint §16, Updated Prompt | Reviewed asset paths: archive, maps, diagrams, documents, stock, screens, data, original graphics, animation, voiceover; host/field/interview constraints. | Feasibility separate from cost/ease and Phase-2 faceless eligibility. Unchecked paths unknown. | Human/model review, provider classifications auxiliary. |
| Source-to-story / Blueprint §16, Third Pass documents, Updated Prompt §59/65 | Checked accessible credible primary/secondary sources, categories, freshness and supported story premises. | Source-supported premise yield, diversity and fragile shared-source dependence; page count is not quality. Unchecked source availability unknown. | Human checked sources required for validation; model/provider suggestions remain unverified. |
| Rights/legal / Blueprint §17, C90 Plus | Asset-specific ownership/license/public-domain verification, necessity, archive/broadcast/sports/movie/music/logo dependence. | low_apparent_dependency, moderate_clearance_burden, high_clearance_dependency, uncertain. No legal conclusion or safe clip duration. | Human/model evidence with verification state; separate from platform/factual axes. |
| Platform policy / Blueprint §17, C90 Plus; current official contract | Reviewed production characteristics and dated/versioned official policy snapshot, URL, scope, refresh/expiry. | Review flags for reused/generic/mass-produced content, disclosure, advertiser concerns. Stale/unchecked policy unknown; no monetization approval/violation prediction. | Official public policy plus attributed human/model review; provider monetization/quality never truth. |
| Factual/editorial / Third Pass documents, Updated Prompt | Reviewed claim domain, verification, disputed-source reliability, current-event volatility/corrections; identifiable-entity verification burden. | Structured production burden only, no allegations or universal safe niche. Missing review unknown. | Human/model review with source/rationale/confidence; distinct from legal/platform risk. |
| C93/F23 / C90 Plus C93/F23 | Optional declared setup hours/cash, dated K releases, task hours/cash, evaluation/revision/contracted overhead, delays, limits/runway and evidence age. | Planned hours = setup + release tasks + evaluation/overhead; planned cash loss = setup + variable release cash + contracted overhead. No income. First mature ≥first release+age; complete ≥last+age. Missing history prerequisites remain unresolved. | Explicit creator scenario only; not ROI or success forecast. F7/F19/F10–13/F20/F21 maturity requirements disclosed. |

## Storage and sampling decision

Schema v6 adds only qualitative_annotations: existing classification_claims restrict
field vocabulary to Phase-2 eligibility and cannot carry these structured reviews.
Existing taxonomy, source/provider records, permissions and analysis_runs/results are
reused. Creator/pilot profiles live in immutable run options, not duplicate tables.
Input ancestry is validated on every read and bounded by its earliest expiry.

Sampling uses declared population IDs, deterministic hash ordering with seed, a hard
budget, selected IDs, cutoff, reason and coverage. Deep review cannot exceed its budget.
Unsampled material never receives full-population conclusions. Prior analytic runs are
read-only contextual inputs, checked for boundary, cutoff and retention compatibility.

F17, F18, final ranking/recommendation and all 15 public research tools remain absent.
