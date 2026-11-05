# Phase 2 verification

Phase 2 is complete. Version 0.3.0; schema v3; 28 tables. STOP before Phase 3.
Starting HEAD/tag phase-1-verified: a2c017ab722bca0dccdd07acb702526de901f8d0.
Preflight: correct repository, clean codex/phase-1 tree, 131 tests, offline verify,
integrity, Phase 1 bundle verification and SHA-256 match. Work used codex/phase-2.

## Formal offline acceptance

All 30 commands in docs/phase-2-results.json passed (exact arguments, stdout,
stderr, timestamps and exit codes retained). Full suite: 255 passed in 19.36s;
131 prior regression cases retained and 124 Phase 2 cases added. Ruff check passed;
86 files already formatted. Import sweep passed: 45 modules. Fifteen Pydantic JSON
schemas validated. Dependency check passed. CLI version/config/API/history/snapshot/
rule/taxonomy/cohort/tool/DB checks all passed. Clean migration [1,2,3] and idempotent
replay, v1 upgrade [2,3], v2 upgrade [3], integrity/foreign-key checks and offline
verify all passed. Failed-v3 rollback and unchanged v1/v2 checksums are tested.

In-memory MCP status/resource initialization passed; real stdio session passed
(1 passed, 254 deselected in 2.44s). Phase 2 status is honest: foundation_only,
live_collection_enabled=false, zero registered research tools, 15 planned.
No live YouTube API call or quota consumed. Tests prohibit live HTTP and use
synthetic metadata/MockTransport. Official documentation was browsed only.

## Eligibility/cohort evidence

Tests cover exact/below 8:00, 6/10-minute sensitivity and all duration bands;
missing/malformed evidence; confirmed/probable/unknown surface states without a
duration-only Shorts claim; requested/omitted live details and all five live
states; English audio versus title/defaultLanguage/region, mixed/non-English,
provider/human conflict; host centrality versus provider/thumbnail/style/sample
shortcuts, scoped channel coverage and aggregate hybrid behavior; rounded/current/
hidden sizes and historical missingness; distinct old/recent account and niche
clocks; calendar entry bands; continuity without ownership-transfer claims;
descriptive inactivity and low output; known-time classification/membership,
versions, flexible taxonomy and multilabel conflicts; disclosed sister channels,
unknown ownership, duplicate route/rank preservation; frozen weak/stopped/one/
three-upload entrants with no future-K requirement; future subscriber growth and
rule/frame changes cannot mutate frozen membership. Excluded candidates persist.

Retention tests cover cache/raw-history independence, scoped acceptance, statistics
surviving text expiry, permission/expiry bounds, independent annotations surviving
a blanket API-data cap, and no self-granted external permission or extended claim
retention. All captured/derived externally sourced content stays permission-bound.
Existing replay, source conflicts, availability, migration integrity, secrets,
noncreating offline inspection and MCP regressions pass.

## Reproduce

Run from the project in PowerShell:

```powershell
& .\.venv\Scripts\python.exe scripts/acceptance_phase2.py
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m ruff format --check .
& .\.venv\Scripts\python.exe -m youtube_niche_mcp verify
& .\.venv\Scripts\python.exe -m youtube_niche_mcp db integrity
```

Inspection does not migrate a pending/absent default database. Run migrate
explicitly if needed. The ignored default DB was upgraded from v2 with [3],
contains no live observations, and passes integrity. Earlier reports/runners and
seven research Git bytes remain frozen; both earlier bundle hashes are unchanged.

## Checkpoint and limits

Implementation checkpoint: f385c09625cd3e6db37cc2c65ef6510194ce3b4e.
The final documentation tag and backup identity are recorded in
PROJECT_STATE.md and the adjacent Phase 2 backup manifest. Finalization verifies
a new phase2.bundle, git fsck --full and a cold clone with matching HEAD/tag,
research hashes and PROJECT_STATE bytes. The manifest provides exact final SHA,
bundle hash/size and verification status without a self-referential Git hash.

Windows only exercised. Provider/owner integration and application policy
acceptance are absent. Rubric/sample thresholds are research conventions, not
calibrated classifiers or growth predictors. Earlier hidden/deleted content,
ownership and historical size can remain unknown. There is no maintenance
scheduler or permanent raw-text archive. No F1–F23 analytics, scores,
recommendations, embeddings, heavy ML or public research tools are implemented.
Exact next Phase 3 scope: F1–F9, failure floor, next5/10, concentration, C90/F19,
F22 and demand breadth. Phase 3 has not begun.
