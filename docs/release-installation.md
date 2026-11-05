# Release installation - Phase 8

Version 0.9.0 is the eighth incremental release, classified separately as a release candidate. Schema remains v7/36 tables; there are 15 public tools. No dependency upgrade or methodology change is planned. This document is preparation only. Global host installation is NOT INSTALLED; automatic startup and scheduler are ABSENT.

Prerequisites: Windows, Python 3.12+ and Git. The verified machine uses Python 3.12.14. Other operating systems and Python versions require their own validation. From the repository PowerShell directory:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
& .\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e '.[dev]'
& .\.venv\Scripts\python.exe -m youtube_niche_mcp migrate
& .\.venv\Scripts\python.exe -m youtube_niche_mcp verify
& .\.venv\Scripts\python.exe -m youtube_niche_mcp db integrity
& .\.venv\Scripts\python.exe -m youtube_niche_mcp tool list
```

Install dependencies only in the local virtual environment. The lock freezes the verified versions. CLI verify and status are the health checks; a second overlapping health command is unnecessary. Startup and tool calls do not migrate. Migration is explicit and checksum validated. Back up existing data before migration; never downgrade its schema in place.

Review `mcp-config.release.example.json`: three separately selectable host examples (stored_only, official_youtube, hybrid). Replace the absolute command/cwd/DB paths for your checkout. Replace credential placeholders through the host's process-secret mechanism before launching. Do not save actual keys in these examples, prompts, screenshots, Git, logs or reports. Empty keys are treated as absent. The server does not load .env. Process environment may be inherited by the host: ensure a stored-only launch has both key variables absent. Use one selected profile in the host only after explicit user authorization.

The launch command is the local virtualenv Python with `-m youtube_niche_mcp.server`, repository cwd, and an absolute migrated YTNMCP_DB_PATH. Stdout is MCP protocol; logs go to stderr. The example uses 20-second ordinary HTTP timeouts, zero retries for controlled smoke, 300-second similarity timeout, and 10-second DB lock wait. Public acquisition has an overall 90-second bound, so lengthy NexLev similarity can be unavailable before its provider maximum. Do not increase ceilings silently.

Stored-only calls require no provider and use retained, unexpired compatible evidence. Empty storage returns insufficient_evidence; setting a query does not invent taxonomy, reviewed cohorts or past V(30). Discover returns a boundary where retained evidence permits; research returns a research_id; focused tools use that ID. New runs need explicit advanced measurement/frame/rubric/review conventions and source permission. See the Phase 7 reference and `phase-8-tool-examples.json`; placeholder IDs require real retained records and are never advertised as observed research.

Official or hybrid keys enable explicit bounded one-time acquisition only. Each refresh needs request_id and targets/search. Administrative storage approval is separate from API credentials; never invent approval. NexLev estimates and private owner analytics do not replace official public observations. Unsupported semantic REST routes remain orchestrator_only. Missing NexLev leaves official/stored workflows usable. No remote NexLev MCP OAuth is installed.

Use a separate process and database for each trusted owner. Local watch owner_context is a namespace, not authentication. Protect databases, backups and credentials using filesystem access controls; creator profiles and independently supplied reviews can be private. Do not expose this stdio server as an unauthenticated remote service.

Rollback: stop the host process, restore a separately protected consistent database backup to a new path, select the intended tagged source/environment, verify schema/expiry/integrity before reconnecting. A Phase 8 source bundle does not include user data. See release-recovery.md. Next actual host action requires an explicit request identifying the MCP host and selected profile; Phase 8 performs no host change.
