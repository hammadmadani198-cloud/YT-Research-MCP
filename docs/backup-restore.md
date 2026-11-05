# Backup and restore

Keep source in this local Git repository. Verified milestones are committed;
the tags are `phase-0-verified`, `phase-1-verified` and `phase-2-verified`. GitHub CLI was signed out during creation,
so no remote was created and nothing was pushed. Never claim an off-device backup
exists until a private remote push or external copy is confirmed.

Create a portable source-history backup in the parent workspace:

```powershell
git bundle create ..\YouTubeNicheFinderMCP-phase2.bundle --all
git bundle verify ..\YouTubeNicheFinderMCP-phase2.bundle
```

Restore into a **new empty destination**, preserving the existing repository:

```powershell
git clone .\YouTubeNicheFinderMCP-phase2.bundle .\YouTubeNicheFinderMCP-restored
```

The bundle contains committed source/history only, not ignored data, credentials,
virtual environments, or files created after the bundle. Copy it off-device for
durability beyond this machine. Recreate the virtual environment from the pinned
lock file and run the acceptance commands in the README.

Back up a live SQLite database consistently using the standard-library backup API
(replace paths with your own; the destination should be new):

```python
import sqlite3
from pathlib import Path

source_path = Path("data/research.sqlite3").resolve()
backup_path = Path("research-backup.sqlite3").resolve()
if backup_path.exists():
    raise FileExistsError("Choose a new backup destination")
with sqlite3.connect(f"{source_path.as_uri()}?mode=ro", uri=True) as source:
    with sqlite3.connect(backup_path) as destination:
        source.backup(destination)
```

Do not copy just the main database file while WAL writers are active. Keep backups
outside Git, verify their integrity, and store them securely. Restore a DB while
all writers are stopped, point `YTNMCP_DB_PATH` at the restored copy, then run
`db status`, `db integrity`, and `verify`. Do not initialize over an unrelated DB.

Secrets live only in process environment. `.env`, DBs, bundles, caches, and logs
are ignored. Git author metadata is repository-local `Codex` / automated noreply
identity because no Git identity was configured; no global Git configuration changed.

Phase 0's separate bundle is frozen and must not be overwritten. The Phase 2 source
bundle also includes Phase 0 history. Exact HEAD/tag SHA, bundle SHA-256/size and
verification statuses are in the adjacent YouTubeNicheFinderMCP-phase2-backup-manifest.json.
No off-device copy is claimed. Research SQLite backups require the same permitted
retention/deletion schedule as the primary data; refreshing a live row cannot renew
an older historical copy. Git bundles contain source/specifications only.

Phase 0 AND Phase 1 bundles/manifests are frozen; create a new Phase 2 bundle. The final manifest records cold-restore HEAD/tag, seven research byte hashes and PROJECT_STATE equality. Never include accepted statistics/text data in source backups; separate data copies remain subject to source-specific expiry.

## Phase 4 backup

The separate parent YouTubeNicheFinderMCP-phase4.bundle and YouTubeNicheFinderMCP-phase4-backup-manifest.json record phase-4-verified, final HEAD, implementation checkpoint, bundle bytes/SHA256 and exact cold restore checks. Do not overwrite earlier bundles. Restore into a new directory, verify tag/HEAD and fsck, load restored src on PYTHONPATH, then run offline CLI verify/formulas plus historical and frozen prior formula tests. The existing verified runtime can be reused; the manifest proves source import location. No real database, keys or network are needed.


## Phase 5 backup

Use the new parent YouTubeNicheFinderMCP-phase5.bundle and external
YouTubeNicheFinderMCP-phase5-backup-manifest.json. The manifest records exact final
HEAD/tag/implementation SHA, bundle size/hash, verification outputs and cold restore.
All earlier bundles are preserved. Restore into a new directory inside the workspace,
set PYTHONPATH to restored src, prove import location, then run the full offline tests,
CLI/MCP verification, frozen artifacts, fsck and clean tree checks. A restored missing
DB remains uninitialized; use the verified existing venv without bundling it.
No live data, secrets or off-device copy is included.


## Phase 6 backup

The new parent YouTubeNicheFinderMCP-phase6.bundle and external
YouTubeNicheFinderMCP-phase6-backup-manifest.json preserve committed source and all
prior history. scripts/verify_phase6_backup.py verifies hash/size, clones into a
new ignored workspace directory, proves restored source imports, runs all tests,
Ruff, CLI/MCP, frozen artifacts, fsck and clean state, and checks the unchanged
prior bundles. It creates the restored .pytest-tmp directory before passing a
pytest basetemp there. Exact outputs and final/tag/implementation SHAs are in the
external manifest. No live database, secrets, virtual environment or off-device
backup is claimed. Earlier bundles/manifests are not overwritten.
