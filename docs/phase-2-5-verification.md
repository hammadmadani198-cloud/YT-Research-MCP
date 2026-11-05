# Phase 2.5 verification — 2026-10-02

Verified starting SHA: efd96e0f15344a3a0e92a69372864598636a4385, matching
phase-2-verified on clean codex/phase-2. Full preflight: 255 passed in 17.86s,
Ruff/check/format (86 files), CLI verify, schema v3/28 tables, DB integrity,
in-memory and real stdio MCP, fsck exit 0 (harmless dangling blobs).
Default Windows pytest temp access was denied; workspace basetemp passed with no
source changes. Exact preflight and missing audit files: phase-2-5-preflight.json.

Final implementation version 0.3.5, schema 4, 31 tables, 13 frozen eligibility rules,
zero registered research tools / fifteen planned. Frozen migrations v1/v2/v3 and
all seven original research byte hashes are unchanged. All prior 255 regression
invariants remain, with latest phase/schema expectations updated and an extra v3
upgrade case. Added 51 NexLev tests: total 307, zero failures.

Formal offline runner scripts/acceptance_phase2_5.py: **40/40 passed**.
Full pytest 307 passed in 29.44s; targeted NexLev 51 passed in 5.51s;
real stdio 1 passed, 306 deselected in 3.42s. Ruff check passed; 101 files formatted.
Package imports: 52 modules. Fifteen JSON schemas, dependency check, CLI verify,
clean replay plus v1/v2/v3 to v4 migrations, integrity, offline no-key provider
status/capabilities/quota/contract/cache diagnostics and both MCP modes passed.
Exact commands, exit codes/stdout/stderr: phase-2-5-results.json.

Fixture coverage includes auth/plan/quota/transient/degraded states; secret rejection;
closed endpoints, bounded pages/jobs and persisted nullable quota/cached/free states;
route publication/subscriber/monetization conflicts; immutable replay and external
field/clock/trust validation; official public hydration; Bridged confidence/sample
conflict; englishOnly false positive; zero/semantic query sensitivity and dedup;
weak records; T4 similarity; T5 finance firewall; generated/translated/unavailable
transcripts, hash/TTL metadata separation; comments/replies; many-to-many taxonomy
annotations; partial/gapped/negative/rebounding/zero/stale provider daily history
outside own prospective statistics. Synthetic fixtures are not fresh channel facts.

Ordinary tests prohibit live HTTP and scrub both API keys. Startup/status/verify do
not initialize/migrate/collect. No live YouTube requests or quota. No live NexLev
requests or quota; optional smoke skipped (NEXLEV_API_KEY absent). Public documentation
was browsed, not authenticated provider API. Official-only operation remains available.

Checkpoint tag: phase-2.5-verified. Final HEAD/tag, implementation SHA, bundle
SHA-256/size and cold restore are authoritative in the adjacent parent manifest
YouTubeNicheFinderMCP-phase2.5-backup-manifest.json. Earlier bundles remain untouched.
A source document cannot embed its own final enclosing SHA/bundle hash without
circularity. Finalization verifies git bundle, fsck and a cold clone's HEAD/tag,
seven research hashes, PROJECT_STATE bytes and offline restored-source CLI.
No off-device backup or hosted deployment is claimed.

STOP after Phase 2.5. F1–F23 remain unimplemented; zero public tools. Exact next
Phase 3 scope (not started): F1–F9, failure floor, next5/next10, concentration,
C90/F19, F22 and demand breadth, gated by frozen frames/permission/history.
