# Phase 5 internal analytics

Read phase-5-qualitative-contract.md for evidence semantics and
phase-5-production-risk.md for CLI/profile behavior. The service accepts frozen
cohort/video IDs and QualitativeOptions with explicit cutoff/age/tolerance/goal,
annotation inventory, generated candidates, review budget/seed, optional creator
capacity/pilot and at most 20 prior Phase-3/4 run IDs.

Annotation payload kinds: source, premise, relation, gap, packaging, continuation,
production, faceless, rights, policy, factual, comment_theme. The strict Pydantic
models reject unapproved private/financial/raw-text fields. Every annotation has
materials, sampling, reviewer/source type, versions, confidence, rationale,
limitations, known clocks and finite expiry. Model review requires model/prompt
versions. Taxonomy references must exist at the correct level and within scope.

Results reuse AnalysisBundle and MetricResult with phase5-v1, plus a Finding in
each detail payload. A Finding carries dimension/state/value/label, evidence IDs,
coverage, source types, warnings/limitations, generation time, boundary/taxonomy
and prior analysis IDs. Annotation-specific confidence is retained separately;
no final confidence equation is implemented. Decimal values serialize as strings.

Persistence replays identical inputs immutably. Expiry is bounded by all retained
inputs/profiles; revoked/purged dependencies block both review and saved analysis
reads. Explicit purge deletes expired reviews/runs. Prior saved discovery hashes
remain validated on contextual replay. No text/media is rescued by statistical
permission, no source is inferred from page count, and no future review can
backfill a past cutoff. Public comment/title annotations must belong to the
frozen video frame. Bounded sampling does not imply full-population coverage.

F17/F18 and final synthesis remain Phase 6. No public MCP tools are registered.
