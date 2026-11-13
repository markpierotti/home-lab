# Security policy

This repository contains experimental home-lab deployment examples, not an automatic
installer or a production support commitment. Report suspected vulnerabilities
privately through GitHub Security Advisories. Exclude credentials and household logs.

## Boundaries and invariants

The operator, local configuration, selected backups and installation roots are
trusted. Concurrent hostile modification of these roots is not sandboxed. Router
telemetry/syslog, DNS-derived labels and received webhook payloads remain untrusted.
Upstream collector identity, artifact, bounded parsing and cleanup guarantees are
owned by the pinned ASUS Router Telemetry dependency.

Privileged helpers must check effective authority before mutation. Dashboard
rollback must validate the backup and every requested dashboard before choosing
restore or deletion. Syslog current/rotated storage must remain within its fixed
filesystem budget and must not fall back to the shared root when storage is absent.
Do not turn missing, stale or malformed telemetry into healthy status.

Exporters read local databases/state and listen on loopback. Grafana authentication,
trusted-LAN restrictions and secret-file permissions are deployment obligations.
The Hermes webhook requires its configured signature; logs are data, never commands.
Hermes advice grants no restart authority. Upstream Hermes internals are not vendored
and are not audited merely by reviewing these examples.

Private DNS/client labels, credentials, captures, inventories and backup archives
must not enter public source or CI. Public fixtures use documentation addresses.
CI must use no live credentials and must not run untrusted pull-request code with
secrets or a privileged repository token. Root test fixtures belong on disposable
runners, not production installation paths.

Concrete boundary violations, command/path injection, credential disclosure, unsafe
rollback, unbounded storage and misleading security status are reportable. Dated
checks do not establish endurance, power-loss or whole-host restore readiness.

The optional Slim vault preserves selected private evidence outside Git. Its capture
helper requires root, uses SQLite-safe snapshots, reports failed sources and pauses
at storage guards without deleting archives. Source objects are hashed; hashes do
not authenticate events or make storage tamper-proof. Logs and transcripts remain
untrusted data. The Mac mirror never synchronizes deletion and retains overwritten
local copies. Learning records and model recommendations grant no live-change authority.
