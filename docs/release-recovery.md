# Release recovery and retention

Source bundles and SQLite backups are separate. The Git bundle contains committed source/specifications/tests/documentation and history; it excludes .venv, research databases, raw provider payloads and secrets. A cold source restore must prove imports come from the new checkout, create its scratch parent before pytest, and pass full tests, schema/migration checks, integrity and all-15 stdio. The cold drill reuses the original virtualenv dependency installation, with PYTHONPATH pinned to restored source/tests; it does not prove a fresh network installation.

Administrative DB backup is an explicit Python function, not a public MCP filesystem endpoint:

```python
from pathlib import Path
from youtube_niche_mcp.db.backup import backup_database

receipt = backup_database(
    Path("C:/research/research.sqlite3"), Path("C:/protected-backups/new-snapshot.sqlite3")
)
```

Use actual absolute paths and a new destination. SQLite's backup API makes a consistent snapshot including WAL state; copying only the .sqlite3 while active can lose WAL changes. Source opens read-only; destination is exclusively created and never overwrites an existing file. Integrity and foreign keys are checked, and both connections close. Failure retains the original source and the failed destination for inspection; do not use a partial destination as a valid backup. Protect the destination and copy it off-device yourself if needed. No off-device backup has been established by Phase 8.

Restore with the same backup function from the snapshot into a distinct new database path. Stop conflicting users, select that path in process environment, run `db integrity`, `db status`, `verify`, and read retained watch/analysis/review records. Do not mutate the original to conceal an error. Before migration, preserve a backup and confirm the expected tagged schema. Migrations are transactional/idempotent, reject checksum tampering and unknown future versions. Busy database returns database_busy with retry/close actions; corrupt/unavailable/future storage returns database_unavailable; older schema returns schema_upgrade_required. Never delete user data in response to a lock or corruption error.

Current expiry rules remain frozen: YouTube non-authorized data <=30 days; permitted statistical archives source-scoped with accepted approval, <=36 calendar months; derived runs expire with dependencies; NexLev raw 15 minutes, text 1 hour, normalized/provider history 24 hours pending contract review. Raw transcripts/comments are never returned in public tools. Historical observations are immutable except explicit expiry/revocation purges; refresh creates a new observation instead of renewing an old value. Private reviews and internal configurations are separate retention classes.

Maintenance is manual: `python -m youtube_niche_mcp history purge-expired` against each explicitly selected DB, including restored snapshots when applicable. Query paths exclude expired inputs even before purge. Provider caches enforce short TTL and use the same repository expiry maintenance. Revoked source permission invalidates dependent derived evidence. Apply retention/deletion obligations to every research-data backup and off-device copy; a snapshot does not grant extra storage rights. No scheduler, automatic cleanup or recurring collection is installed. Watch cadence expresses intent and last_checked_at remains null.

Phase 8 tests backup/restore on a scratch database with representative runs, reviews and watches, validates v7/36 tables, exercises rollback/checksum/future failures only on scratch copies, and leaves production history untouched. Source and DB corruption are different failures; recover the appropriate artifact. Final receipts state the actual verification result.

## Operational failure actions

| Failure | Explicit recovery action |
| --- | --- |
| Missing DB | Confirm the configured absolute path; migrate a new empty DB only when intended, or restore a consistent snapshot to a new path. Never treat an accidental empty path as recovered evidence. |
| Damaged DB | Stop the host, preserve the damaged file/WAL for inspection, restore the latest valid snapshot elsewhere, then check integrity/FKs/schema/expiry. |
| Wrong or pending schema | Select compatible tagged source; back up before explicit migrate. Checksum/future rejection requires investigating the mismatch; never edit migration checksums or downgrade in place. |
| Missing API key | Use stored-only tools. Configure a process secret for the intended provider only when explicitly enabling refresh; API keys do not grant storage permission. |
| Quota exhaustion or 429 | Preserve existing evidence, inspect local attempted-cost receipts, honor provider reset/retry timing, reduce the next explicitly requested budget. Remote remaining quota stays unknown unless documented and actually observed. |
| Provider outage/timeout/401/403 | Use retained evidence and review the structured limitation. Correct authentication/plan permissions or retry later explicitly; no undocumented fallback or background retry. |
| Invalid/stale watch | Read within the trusted owner namespace, use the current expected_revision for update/disable, or create a new ID for changed immutable targets. Cadence does not run a scheduler. |
| Failed migration | Preserve the source and diagnostics; the tested transaction rolls back. Verify the original, investigate the failure, and retry only after it is resolved. |
| Source rollback | Select phase-7-verified in a separate checkout/environment and a compatible separately restored DB; do not modify the current verified release or prior bundle. |

## Source restore example

Use a new destination and the actual absolute Phase 8 bundle path. These are manual recovery instructions:

```powershell
git bundle verify 'C:/Users/hp/Documents/ChatGPT/Develpment/YouTubeNicheFinderMCP-phase8.bundle'
git clone 'C:/Users/hp/Documents/ChatGPT/Develpment/YouTubeNicheFinderMCP-phase8.bundle' 'C:/research/new-source-restore'
git -C 'C:/research/new-source-restore' checkout phase-8-verified
git -C 'C:/research/new-source-restore' rev-parse HEAD
```

Compare HEAD, bundle bytes and SHA-256 with the external Phase 8 backup manifest. Install the locked dependencies into that checkout's own local environment, point to a separately restored/migrated DB, and verify imports/CLI/tests before host use. For Phase 7 rollback use its preserved bundle/tag in another new destination. A source clone does not restore private research data or credentials.

Local validation runtime recovery: the app-bundled Python and shell disappeared during finalization. A publisher-checksummed Python 3.12.14 standalone archive restored the ignored local virtualenv runtime at .venv/runtime/python, retaining all 44 installed pins. No global install or host change occurred. See phase-8-runtime-recovery.json. A new source clone must still create its own environment; source bundles omit this runtime.
