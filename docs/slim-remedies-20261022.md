# Slim incident remedies — 22 October 2026

Deployed to the existing Slim installation following the owner's request to deploy
the remedies documented in [incident PR #2](https://github.com/markpierotti/home-lab/pull/2).
The [operations plan in PR #3](https://github.com/markpierotti/home-lab/pull/3)
continues to own the wider automation design. This change does not implement its
complete repair/executor, retry or specialist-profile programme.

## Installed behaviour

| Remedy | Installed change | Acceptance and remaining limit |
| --- | --- | --- |
| R1 — reboot discrimination | The existing `router-rebooted` UID now reports **ASUS uptime reset detected**. The expression uses uptime decreases, current scrape/exporter/collection success, nonnegative sample age at most 180 seconds, at least two observations, and finite nonnegative uptime. Missing/unhealthy evidence is `NoData`. | 19 exact-expression `promtool` fixtures pass, including both directions of boot-time jitter, reset after short uptime, gaps, missing inputs, stale/future timestamps, invalid uptime and outages. Current live result is zero resets. A decrease is restart evidence, not proof of its cause; no real reboot was induced. |
| R2 — evidence persistence | Add only `/var/lib/slim-telemetry-vault/Inbox` to the gateway's writable paths. Preserve `ProtectSystem=strict`, the empty capability set, `NoNewPrivileges` and the unprivileged account. | In the actual gateway mount namespace, the Hermes identity can write a temporary Inbox note and cannot write elsewhere in the vault or raw evidence tree. The host root was writable while the service view was read-only; the screenshots' host-wide read-only claim was unsupported. |
| R3 — investigation outcomes | The transform saves a bounded deterministic evidence packet and incident note **before** dispatch/dedupe commitment. Fingerprint plus start time identifies an episode; the same alert's previous episode is linked as historical context. A home spool retains notes if canonical storage fails. Lifecycle callbacks record start, end observation and iteration-budget state. A minute timer marks expired work unresolved without model calls. | Regression fixtures cover storage denial/full errors, interrupted work, repeated episodes, corrupt/full ledgers, resolution-only intake and budget exhaustion. The installed hook handler was replayed in the gateway namespace with isolated fixture state; partial output survived and delivery remained unknown. This is not an end-to-end model/provider/Telegram failure injection. |
| R4 — camera coverage | Add an observation-only `camera_network` ICMP job, derived from the existing private inventory, with `alert_policy=baseline_pending`. Record the owner's correction that the 20 October outage was a flat battery. | The network probe is scraped; no camera outage alert is enabled until a charged-camera healthy baseline is established. ICMP does not establish application/cloud health. A healthy application endpoint is not known. |
| R5 — diagnostic permissions | The operator and alert prompt use monitored probe results first and distinguish stale/missing evidence from permission errors. No extra ping capability is granted to Hermes. | Existing monitored probes remain available; gateway capability and privilege restrictions are retained. Camera network reachability is separate from camera application health. |

The alert prompt requests at most **four additional read-only tool calls** and an
explicit partial answer if unresolved. That is an instruction to the model; the
existing configured **15-turn hard limit** is unchanged. It is not a new enforced
four-tool security boundary or a guarantee of model compliance.

## Receipt and storage semantics

`hermes/scripts/slim_incidents.py` uses a private, locked, atomically replaced ledger
under `~/network/state`. Up to 100 indexed incidents retain the last 12 event records
each; the index has a 2 MB guard. A total event count exposes truncated per-incident
history. Existing bounded Grafana JSONL and the private vault archive retain source
history separately. Safe pruning removes only the home index/spool for resolved
terminal records whose canonical note was saved; canonical notes are retained.
An index full of unresolved records or a corrupt ledger fails explicitly instead
of silently resetting history or reporting success.

Canonical notes live in the narrowly writable Inbox. The fallback is a different
path on the **same host/disk**, not independent disaster recovery. If both paths
are unavailable or the entire disk is full, durable intake cannot be guaranteed;
the error must remain visible rather than being acknowledged as stored. Existing
vault capture/mirroring and retention policies still apply; raw objects are not
rewritten by the incident helper.

`agent:end` exposes only a 500-character response excerpt and fires before final
delivery. Therefore the ledger says **end observed**, never “diagnosis verified”
or “message delivered”. The response may be a partial answer or provider error.
Delivery stays **unknown** without an independent receipt. Grafana resolution
updates the alert transition separately; it cannot mark investigation success.
An isolated resolution received without a matching firing episode is explicitly
`not_requested_resolution_only`, not a fictitious failed investigation.

The minute checker marks pending/started work unresolved after a five-minute
observation deadline, preserves its evidence and exposes it to the digest. It does
not cancel a running agent, make model calls, retry work or send Telegram messages.
Native best-effort coalescing and the existing repeat-trigger behaviour remain;
there is no new global concurrency lock or crash-safe model retry queue in this
change. Those remain work for PR #3. The raw Grafana notification route is retained.

## Deployment and validation

Selected live script hashes matched source before deployment. The live rule,
effective systemd restrictions and directory ownership were reconciled. Private
configuration was patched on Slim so unrelated rules, private targets, model
settings, credentials and delivery identities were preserved. No credential file
was copied off the host.

The first application failed because `ProtectHome=tmpfs` hid the new checker's
state path. Automatic rollback restored the old configuration; an orphaned timer
symlink was removed. Adding an explicit state-directory bind passed an isolated
systemd namespace test before the successful retry. This failure and recovery are
not presented as a successful first deployment.

The successful application and final edge-case refinement were backed up under
root-only manual backup directories. Grafana and Hermes were restarted. Prometheus
reloaded through HUP; Pi-hole, Unbound and Prometheus retained their original PIDs.
There was no router, gateway, DNS, firewall, firmware or package change.

Checks performed:

- Full deployment and repository fixture suites on Slim, including privileged
  cases: **114 deployment tests and six repository tests passed**, zero skipped
  on Slim. No tests target production storage or induce a real network outage.
- 19 fixtures run in Slim's actual Prometheus engine tooling using the exact
  expression extracted from the provisioning source.
- Authenticated local Grafana database read confirms the provisioned title,
  expression and `NoData` state; Grafana health reports database OK and Prometheus
  readiness is healthy. Current expression evaluation reports zero resets.
- Gateway logs confirm the incident hook was loaded and Telegram polling connected.
  That connection is not a receipt for a future incident notification.
- Namespace acceptance verifies permitted Inbox writes and denied other vault writes;
  isolated installed-handler replay verifies partial-result storage and unknown
  delivery without making a model call or sending a notification.
- Installed file hashes, checker success and timer activation verified. These are
  short acceptance observations, not endurance, actual reboot or power-loss tests.

After the owner reported the camera was charging, the first sampled five-minute
window contained one ICMP success and nine failures, while the monitoring scrape
itself stayed healthy and the neighbour identity matched inventory. This establishes
some network response, not stable availability or application health. Camera outage
alerting therefore remains suppressed while baseline work is incomplete.

## Rollback

The base backup is
`/var/backups/slim-manual/20261022-062131-incident-remedies/`.
The final edge-case backup is
`/var/backups/slim-manual/20261022-062558-incident-edge-cases/`. Its
`rollback-all.py` wrapper restores its two
preceding files and invokes the base rollback. Use the final backup path recorded
in the private deployment report; do not invoke the base rollback directly after
the edge-case update because its new-file hash guard correctly notices that update.

Run the final wrapper as root. It checks saved hashes, stops the checker/gateway,
restores file ownership/modes and the original configuration, disables the new
timer, reloads systemd/Prometheus and restarts Grafana/Hermes. Private incident
notes, the fallback spool and the owner's battery correction are retained.
Verify DNS, monitoring, bot connectivity and the restored rule after rollback.
The first automatic rollback was exercised; the final combined wrapper has not
been run against production simply to demonstrate a second interruption.
