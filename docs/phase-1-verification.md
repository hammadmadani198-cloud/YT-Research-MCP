# Phase 1 verification

Verified on Windows, 2026-10-02. Python 3.12.14, MCP 2.2.0, Pydantic 2.13.5,
httpx 0.28.1, pytest 9.1.1 and Ruff 0.16.10. Application version 0.2.0, schema 2.
Installed editable package was refreshed offline using --no-index --no-deps and
--no-build-isolation. Runtime dependency versions remain those in requirements-dev.lock.

All **23 acceptance commands passed**; exact arguments, stdout, stderr and return codes
are in [phase-1-results.json](phase-1-results.json). Run from the repository:

```powershell
& .\.venv\Scripts\python.exe scripts/acceptance_phase1.py
```

| Check | Result |
| --- | --- |
| Full pytest | 131 passed, 0 failed (7.68s) |
| Ruff check | All checks passed |
| Ruff format check | 70 files already formatted |
| Package import sweep | 37 modules enumerated, all non-entrypoint modules imported |
| Dependency consistency | No broken requirements |
| CLI version/config/API capabilities/history/snapshot status | Passed, secret-safe offline results |
| MCP initialization / registered tools / status | Passed; zero registered research tools, 15 planned |
| Real stdio session, separately exercised | 1 passed, 130 deselected (2.45s) |
| Clean migration and repeat | [1, 2], then [] |
| v1 fixture upgrade | Fixture [1], upgrade [2]; v1 checksum unchanged |
| Default DB migration | Existing v1 upgraded explicitly with [2]; no research rows |
| Integrity / foreign keys / WAL | Passed on default, clean and upgraded databases |
| Offline verify | Passed on default, clean and upgraded databases |
| Live YouTube API | Not used; no API quota consumed |

The retained Phase 0 checkpoint was verified before any Phase 1 edits: clean repository,
HEAD/tag f7e7b88656d6091ce5bb396dcc35a709fa759baa, 56 original tests passing,
offline verify passing, portable bundle verified. The Phase 0 code milestone is
c3acf9ed974d8baeed41ff78f3498f89291679fb. Phase 0 reports and bundle are unchanged.

Focused evidence is included in the full suite:

| Test module | Invariants covered |
| --- | --- |
| test_db.py, test_history.py | Migration checksum, atomic failure/upgrade, future/gap refusal, update rejection, identical replay, T1=100/T2=200, indexes, integrity |
| test_history.py | Observed/available/first-seen bounds, exact boundary, time zones, historical title, external decision time, no subscriber backfill, both conflicting sources retained |
| test_api.py | Missing IDs, hidden/rounded counts, publication vs upload, all public routes, bounded retries, quota bucket overrides/accounting/sink, malformed responses/counts, key-free URL/error/log output |
| test_discovery_snapshots.py | Exact manifest, empty/multiple/repeated-token pages, duplicates/ranks, malformed IDs, failed page, bounded uploads traversal, replay without quota, per-ID failures, prospective-only capture |
| test_cache_capabilities.py | Fresh/expired/refreshed cache, explicit transient-only stale path, history unchanged, source/key isolation, forbidden credentials, derived identity, permission/owner/history gates |
| test_foundation_boundaries.py | Malformed batch summaries, retention cascade/expired manifest, five distinct source clocks, failures/future captures cannot advertise usable history |
| test_server.py, test_verification.py, test_cli.py | In-memory and real stdio, zero tools, no startup/network/migration writes, status/capabilities, non-destructive verification and secret-safe CLI |

Standard tests use synthetic checked-in API fixtures and block the live httpx transport.
No key is needed. API documentation browsing used official Google/YouTube references
and is distinct from making quota-consuming API requests.

Read-only commands do not create the configured database. SQLite can manage WAL/SHM
sidecars during access. Explicit maintenance removes expired retained evidence; the
default repository has no live history. Policy acceptance, auxiliary provider access
and owner OAuth remain unavailable/unverified. No off-device backup is claimed.

Git checkpoint/tag and final bundle verification/hash/size are recorded in PROJECT_STATE.md
and the adjacent YouTubeNicheFinderMCP-phase1-backup-manifest.json. Stop at Phase 1;
Phase 2 is eligibility/cohort foundations only. No F1–F23 analytics is implemented.
