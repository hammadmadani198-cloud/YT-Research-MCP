# Phase 8 security and privacy review

Local source review and adversarial integration tests are the scope. This is not an external penetration test, a provider contract approval, a remote-service authorization model or an assurance against all future vulnerabilities. Offline acceptance and primary-source dependency review receipts determine final readiness.

| Boundary | Review and executable evidence | Release treatment |
| --- | --- | --- |
| Credentials | Settings excludes/repr-hides both keys; no implicit .env; both keys and authorization/token strings redacted by JSON logging; exception type only | No values in artifacts, protocol or logging; process-secret configuration |
| API traffic | Allowlisted fixed base URLs/routes, keys in headers, trust_env=false, redirects disabled, bounded retries/timeouts; no arbitrary URL fetch or subtitle download | No undocumented endpoints, proxy inheritance or OAuth experiments |
| SDK inputs | All 15 strict contracts, unknown fields/enums/IDs/cursors/ranges rejected; pre-validation UTF-8 request cap 128000 bytes; fixed error text | Rejected values never echoed; API/content data cannot supply SQL/path/config commands |
| Untrusted content | Query, title, comment, transcript and provider labels are data; SQL inputs parameterized; no eval, exec, shell invocation or provider-content instruction dispatcher | No tool installs/prompts/provider text can execute code; malicious query test preserves DB |
| Public outputs | Raw text, private analytics, sensitive creator capacity fields and profile IDs omitted; evidence confidence/state preserved | No CTR, retention, true demographics/revenue or success probability inferred |
| Creator profiles | Explicit local research capacity stays in separate records; generic query/boundary lookup excludes private creator runs | Trusted owner can explicitly inspect own research; source databases remain private |
| Watches | All actions scope by owner_context; A/B lookup/update/disable tests and persistence/100-target tests | Namespace only, not principal authentication; one trusted owner per DB/process |
| Filesystem | No public arbitrary-file/SQL endpoint; backup is administrative source function, distinct existing source/new exclusive destination | SQLite/WAL snapshot consistent, no overwrite; protect DB/backups using OS ACL |
| Storage | Busy, query-only, corrupt, pending/future and checksum cases on scratch; transactions rollback; integrity checked | Actionable sanitized errors; no automatic migrations/downgrades/delete-to-repair |
| Retention | Existing expiry, purge/revocation/dependency tests retained; source scopes and clocks preserved; raw caches short-lived | Backup is subject to expiry/deletion too; no permanent raw text or automatic cleanup |
| Tool effects | Actual all-15 stdio with separated cwd/DB paths containing spaces; watch writes are intent only | No startup HTTP, scheduler, global config changes or hidden background collection |
| Dependencies | 44 installed lock versions match; pip check; inventory in phase-8-dependency-inventory.json | Current primary-source security review recorded after offline gate; no automatic upgrades |

Release hardening fixed NexLev log redaction, authorization-string redaction, generic capacity-profile inheritance, silent byte-fallback primary-row loss, future-schema error misclassification, actionable SQLite errors and preservation of maximum watch targets. The frozen research equations, trust rules and recommendation states are unchanged. Current integration tests include 225 malformed per-tool cases, prompt/SQL-like query-as-data, both-provider failure matrix and secret markers. Database namespace controls cannot isolate malicious callers who can choose another owner's namespace or explicit run ID; local single-owner deployment is required. No authentication layer is claimed or added in this phase.

No keys were found in the process precheck. A secret scan checks tracked release files for common credential/private-key patterns, with values withheld. Documentation placeholders and synthetic test markers are not live credentials. Full official dependency advisory review and exact gate results are summarized in phase-8-verification.md. Any material unresolved gate blocks readiness; absent provider keys instead create a documented live-provider gap.
