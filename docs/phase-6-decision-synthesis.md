# Phase 6 decision synthesis and F17

Evidence supports further consideration under tested assumptions. It does not
predict creator success or approve a niche, pilot expenditure or legal clearance.

DecisionService consumes a retained Phase 3 base, compatible Phase 4/5 source runs,
a versioned DecisionRubric and a predeclared SensitivityPlan. It performs no HTTP.
AnalysisRepository stores/replays typed manifests in the existing three analysis
tables. Qualitative annotations and policy snapshots retain their own ancestry.
Schema remains v6/35 tables, with no migration. Package 0.7.0 marks the next
internal feature phase without changing dependencies or public tool registration.

## Separate axes

Performance, ordinary floor, repeatability, entrant accessibility, demand breadth,
concentration, momentum/history, differentiation, idea depth, production, sources,
rights, platform policy, factual risk and pilot downside remain visible. Each has
source metrics/details, annotation IDs, warnings and caller rule judgments.
Unknown or observed-ungraded values remain explicit. No universal view, HHI,
workload or revenue threshold is introduced; numeric thresholds and materiality
references belong to the caller's versioned goal rubric.

Generic states: supported, supported_with_caveats, mixed_evidence, weak_under_goal,
insufficient_evidence, high_execution_burden, high_rights_or_policy_dependency and
history_immature. Severe rights/policy/factual dependency takes display precedence;
underlying insufficiency/history gates remain attached. Required unknown/ungraded
axes or unverified critical classifications gate support. Mature required history
is separate from strong current evidence. Cautious support carries sensitivity
warnings and less-than-high confidence. Evidence against a niche is preserved.

Explicit CreatorCapacity uses Phase 5 compatibility in a separate creator_fit
receipt. A constraint mismatch cannot alter base formulas, generic axes,
recommendation state, F18 or canonical niche burden.

## Optional F17

Disabled by default. Caller supplies a version, positive weights, direction and
finite external low/high benchmarks with a reference. For each allowlisted numeric
canonical formula value, normalize `(raw-low)/(high-low)`, clamp to [0,1], invert
for lower-is-better, then report `100 * sum(weight*normalized)/sum(included weights)`.
No synthetic-fixture tuning or hidden weights. Raw value, normalized value,
endpoints, direction, clipping and weight are visible.

Missing essential data or canonical insufficiency yields insufficient_dimensions.
Explicit allow_partial permits optional omissions with a disclosed included-weight
denominator and partial_index. Otherwise full data yields sorting_index_available.
Sorting ties resolve by run ID; unavailable indices sort last. F17 runs after
synthesis/confidence and is never read by either. High sorting values cannot erase
risk, unknowns or an incompatible creator profile. RPM/revenue/monetization,
opaque T4 scores, F18 and decisions are excluded from the input allowlist.

## Internal CLI

`python -m youtube_niche_mcp decision f17-config` displays the schema.
`decision run --options <JSON-path>` performs synthesis; `decision inspect <run-id>`
returns retained immutable results including sensitivity comparisons. DecisionOptions
JSON is strict: base_run_id, cutoff, age_days, tolerance_seconds, goal, rubric and
sensitivity are required; retained context IDs, creator and F17 are optional.
Python integrations import youtube_niche_mcp.decision.service.DecisionService.
Status reports phase6 availability. Public research tools remain 0/15.
