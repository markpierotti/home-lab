# Home Lab — project overview and portfolio copy

Updated 14 November 2026. Deployment claims below refer to the dated records
linked here; this page is not a fresh live-health report.

## Project card

### Operating a Linux home lab with observable failures

I run a Linux home lab combining DNS filtering, router telemetry, monitoring,
alert delivery and private backup/evidence workflows. I use AI-assisted
implementation and review, with human decisions, explicit acceptance checks and
documented recovery limits.

**Stack:** Ubuntu · Python · systemd · Pi-hole · Unbound · Prometheus · Grafana ·
SQLite · OpenSSH.

**Evidence:** an external missing-heartbeat alert received on Telegram; a restored
Mac backup pull with 14 archives checked; private log capture with reconstruction
and integrity checks. A full restore onto a clean host remains to be demonstrated.

## Engineering work and evidence

| Work | Demonstrated result and boundary | Source |
| --- | --- | --- |
| Router integration | Pinned ASUS collector on a dedicated Linux service account; collector development and its hardware trials stay upstream | [Repository boundary](repository-split-20261019.md) |
| DNS and monitoring | Pi-hole/Unbound, Prometheus and three Grafana dashboards; desktop and narrow-layout acceptance is dated | [Dashboard record](slim-dashboards-20261019.md) |
| External alerting | Operator confirmed a Telegram down alert after the heartbeat was deliberately stopped on 13 November; no actual power or gateway failure tested | [Alert validation](slim-alerts-20261018.md#outage-validation--2026-11-13) |
| Off-host backup pull | Restored restricted SSH pull; fixed stdin consumption in the download loop; 14 archives and two SQLite databases checked | [Backup validation](slim-backup-validation-20261113.md) |
| Evidence preservation | Hashed compressed objects, log base/append chains, daily snapshots for two SQLite sources, storage guards and a one-way Mac reading copy | [Capture and mirror design](../deploy/slim-vault/README.md) |

## Reusable CV bullets

- Operated a Linux home lab integrating Pi-hole/Unbound, router telemetry,
  Prometheus and Grafana, with documented service, alerting and recovery checks.
- Validated an external missing-heartbeat alert through operator-confirmed Telegram
  receipt and restored a restricted SSH backup pull; checked 14 archives and the
  integrity of Grafana and Pi-hole database snapshots.
- Directed AI-assisted development of private evidence-capture and mirroring tools,
  with hashed log reconstruction, storage guards, synthetic regression tests and
  explicit limits on retention and recovery claims.

## Scope and next evidence

Mark owns the lab, sets scope and authorizes live changes. AI coding assistants
helped implement, review, test and document the tooling. Capture and mirroring make
no model calls; the learning recorder does not retrain a model or automatically
change the network.

A missing-heartbeat test is not a power-loss test. An intact archive is not a
successful service restore. The Mac evidence mirror is a reading copy, not an
independently tested backup. Segmentation, Project Limbo and detection/investigation
exercises remain planned; this is not presented as a deployed SOC.

The next recovery milestone is a full restore onto a clean host, followed by
controlled restart and power-recovery checks. See the [roadmap](home-lab-roadmap.md).
Raw telemetry, device inventory, credentials and backup contents remain private.
