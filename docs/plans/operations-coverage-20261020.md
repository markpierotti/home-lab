# Operations coverage review — 20 October 2026

Scope: why the current operator did not proactively report the NTP and Wi-Fi
observations, and what the next operations design must cover. This is a read-only
inspection and a proposal, not a deployed expansion of authority.

The target is a coordinated operations team covering systems, networking, service
reliability, recovery and security. Security operations is one discipline within it.
See the [team plan](autonomous-operations-20261020.md).

## What was checked

Source baseline: home-lab `main` at `9c437bd`, including the
[operator deployment record](../slim-hermes-20261018.md),
[role](../../deploy/slim/hermes/SOUL.md),
[configuration overlay](../../deploy/slim/hermes/config.overlay.yaml),
[snapshot](../../deploy/slim/hermes/scripts/slim-snapshot.py),
[watcher](../../deploy/slim/hermes/scripts/asus-logwatch.py),
[webhook transform](../../deploy/slim/hermes/scripts/grafana-alert.py),
[alert rules](../../deploy/slim/etc/grafana/provisioning/alerting/slim-rules.yaml)
and the current heartbeat/syslog metrics scripts.

Live checks around 06:03–06:12 AEST used the existing owner SSH connection to read
public loopback Prometheus metrics, accessible journal entries, selected service
properties, timers and bounded current/rotated ASUS logs. No sudo, model invocation,
service restart, secret read, DNS query-history read or permission change was used.
Private evidence stays in the owner's workspace; no household log dump is included.

| Boundary | Evidence | Limit |
| --- | --- | --- |
| Hermes process | System gateway active, running as `hermes`, started 19 October 12:27; automatic restart counter zero. | Active does not establish scheduler or model-provider health. |
| Process restrictions | `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=tmpfs`; write paths restricted to Hermes home/runtime. | Selected unit properties, not a fresh penetration test. |
| Deterministic jobs | Syslog metrics, heartbeat and backup timers active with recent trigger timestamps. | Does not verify every output or off-host delivery. |
| Selected installed scripts | Heartbeat and ASUS syslog metrics SHA-256 match repository bytes. | Does not establish that private Hermes scripts/configuration also match. |
| Alert follow-up | Owner screenshot shows raw ASUS reboot alert at 02:12 and Hermes diagnosis at 02:14. Accessible gateway journal has a webhook-related entry at 02:12:37. | One successful incident path; not a delivery/retry guarantee. |
| Hermes jobs, model config and history | Operator documentation describes minute watcher, 08:00 digest and webhook route. | Live files are protected from this SSH account. Current schedules, enabled flags, model configuration, worker records and private alert history were not independently read. |
| Grafana rules | Checked-in source contains 16 rules. | Live provisioning file is protected. No authenticated live rule export was obtained. Historical docs variously say 13, 15 or 16; do not infer the live count from those claims. |

Private-home protection is functioning as a boundary. It is not evidence that
Hermes itself cannot read its own state. Do not loosen it to make external
inspection convenient.

## Coverage gaps supported by source

| Observation | What the current source does | Consequence and next work |
| --- | --- | --- |
| Slim NTP unsynchronised | No clock-sync rule in checked-in alert source; snapshot reports boot time but not sync state, last successful sync or clock uncertainty. Heartbeat checks DNS, Prometheus readiness and Grafana database health. | This condition has no dedicated source-level proactive path. Add deterministic clock-health evidence, persistence, missing-data handling and a triage route. |
| ASUS channel activity | Minute watcher detects unknown devices, selected authentication events and logging/restart signatures. It has no channel-change-rate detector; snapshot does not report radio channel trends. | No dedicated source-level path for this observation. Establish a per-radio baseline and correlate client symptoms before classifying frequent switches as a fault. |
| Brief external failures | Internet-down rule takes the maximum across HTTP and external ping probes and requires five minutes below threshold. It represents sustained failure of all those available targets. | Isolated failures while another target works do not qualify. That is useful noise suppression, not proof of missed outage delivery. Add a separate degradation summary with sample counts, multiple-target/protocol corroboration and graded severity. |
| False ASUS reboot alert | `changes(rtax_router_boot_time_seconds[15m]) > 0`, no hold time. | A one-second shift can trigger it. Improve discrimination and validate actual reset versus clock jitter, absent/stale data and outages before changing it. |
| Failed triage or delivery | Transform records a dedupe timestamp when waking the agent; eligible repeat investigation waits 3h30, intended for Grafana's four-hour repeat. | This is dispatch intent, not an investigation/delivery receipt. A resolved incident can stop repeating before a failed follow-up is retried. Add explicit accepted/started/completed/delivered outcomes and bounded durable retries. Source behavior was inspected; no model outage was injected. |
| Missing history or failed inspection | `recent_jsonl()` returns an empty list on unreadable history; digest then prints “none”. `sh()` also collapses exceptions into empty output. | An unavailable input can be presented as no events/no failed units. Return explicit unknown/error/partial states and expose the checker failure itself. This does not show that a live read failed inside Hermes today. |
| Operators' own health | Host heartbeat is independent of the model but does not inspect Hermes job completion, webhook processing or provider/delivery success. | Gateway active alone is insufficient. Monitor each stage and preserve the raw owner alert independently. |

These gaps explain absent **coverage in the reviewed source**. They do not prove
the complete live cause of every missing message. Obtain a safe live configuration
and execution summary before claiming that the deployed wiring has been reconciled.

## Observations requiring graded interpretation

The 24-hour investigation found:

- Slim currently reports NTP enabled but unsynchronised, with repeated time-server
  timeouts. Earlier received packets do not demonstrate current synchronisation.
- ASUS logs contain 66 channel-switch announcements on one radio, median spacing
  approximately 18.4 minutes. Client disconnection was not established.
- 33 of 2,880 external ping samples failed; Ubuntu and Google HTTPS probes had
  13 and two failed samples respectively. All recovered. Gateway, ASUS and local
  DNS probes recorded no failure in the same window.
- Available boot history showed only the known one-second ASUS boot-time shift,
  with increasing uptime. The [incident PR](https://github.com/markpierotti/home-lab/pull/2)
  preserves the screenshot and the distinction between bot claims and evidence.
- Resources, current collection and core service state looked healthy. Selected
  “disk full” journal messages came from named isolated storage-test fixtures,
  not the live log filesystem. Routine firmware-check `WATCHDOG` messages did not
  establish a watchdog reset.

NTP loss is a persistent health issue. Channel activity and brief probe failures
are observations to assess against baselines and impact, not automatic repair
instructions. None of these observations justifies rebooting the gateway or
weakening DNS/PS5 restrictions.

## Finish live reconciliation without extra privilege

Have the existing Slim operator, from its own authorised account, return a small
redacted summary. A suitable owner request is:

> Read-only audit: report the installed Hermes version; cron job name/ID, enabled
> state, schedule/timezone and no-agent flag; last successful completion/error for
> the watcher and digest; last webhook processing and Telegram delivery outcomes;
> the configured primary/auxiliary model names and reasoning setting; and whether
> the expected scripts are readable and their SHA-256 hashes. Use your own home
> files and supported read-only commands. Do not execute a job, modify a schedule,
> inspect `.env`/credentials, expose recipient IDs or webhook secrets, or dump
> conversation history. If a field or delivery receipt is unavailable, say unknown.

An authorised Grafana operator should separately export only rule UID/title,
expression, hold time, enabled state and routing names, excluding contact-point
credentials and recipients. Compare with reviewed source and record drift. Do not
call an unavailable export “matching”. No such export is claimed in this review.
