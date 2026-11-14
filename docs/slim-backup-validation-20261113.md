# Mac backup pull and partial restore check — 13 November 2026

Recorded here on 14 November from the operator-provided 13 November session
handover and the committed backup-pull correction. These are historical session
results, not a new inspection of Slim or the Mac scheduler.

## Restoration and observed results

The Mac rebuild had removed the off-host backup pull. The session restored a
restricted SSH pull key, a forced-command authorization, a local pull script and
a daily 09:00 LaunchAgent. The key can list and fetch backup archives; a test of
an unrelated command was refused. Credentials and private configuration are not
published.

The first manual pull fetched only one archive: SSH inside the filename-reading
loop consumed the remaining standard input. Adding `ssh -n` kept SSH from reading
that stream. The subsequent manual run retrieved all 14 available archives,
covering 31 October through 13 November. All passed `gzip -t`.

The 13 November archive was unpacked into temporary private staging. Grafana and
Pi-hole SQLite databases passed `integrity_check`; the collector private key was
absent. The temporary extracted copy was removed after inspection.

## What remains unverified

- The next scheduled 09:00 Mac run had not occurred during that session.
- Compression and database integrity do not establish complete recovery coverage.
- No service was rebuilt from the archive on a clean host.
- Controlled power-loss recovery and a whole-host restore remain outstanding.

The [operations runbook](slim-operations.md) describes the full restore procedure
and existing best-effort backup limitations. The [pull script](../deploy/slim/macos/pull-slim-backups)
is a sanitized installation example, not the private deployed configuration.
