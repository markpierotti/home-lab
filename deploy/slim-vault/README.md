# Slim telemetry vault

A private, filesystem-first Obsidian evidence vault for Slim, Hermes and router
telemetry. The design follows Mark's existing Voltron capture and Raw → Review →
Wiki workflow. Capture and mirroring make no model calls.

## Components

| Component | Purpose |
|---|---|
| `capture.py` | Preserve selected changing files and SQLite-safe database snapshots as hashed, compressed objects |
| `slim-vault-capture.*` | Run capture every ten minutes on Slim |
| `mirror.py` | Pull a one-way Mac reading copy, retaining overwritten local files and never synchronizing deletion |
| `learning-loop/` | Adapted Voltron recorder for scoped lessons, outcome review and bounded optimisation experiments |
| `SKILL.md` and `learning-references/` | Hermes instructions for evidence capture, retrieval and review |
| `vault-seed/` | Initial Obsidian orientation notes and review templates; no live captures |

The canonical vault is `/var/lib/slim-telemetry-vault`. Root owns the raw capture
objects and manifests; Hermes can read them and write its Inbox, review proposals
and curated Wiki. The learning bridge has a separate writable raw subdirectory.
These permissions and hashes are not forensic WORM storage or source authentication.

## Selected records

The recorder captures current Hermes memory Markdown, its conversation and cron
databases, retained cron outputs, selected diagnostic logs, network event/alert
histories, router samples/outcomes/state/cleanup records and raw ASUS syslog.
Credential files, `.env`, live configuration secrets, the full Prometheus TSDB and
complete Pi-hole/system journals are outside the capture set.

An initial snapshot cannot recover records that were already pruned. Ten-minute
capture reduces loss risk but cannot establish complete coverage during outages,
concurrent rotation or failed reads. Failed sources are recorded and the service
exits unsuccessfully. SQLite `mode=ro` backup reads application data without changing
rows; the cron directory write exception permits SQLite WAL shared-memory coordination.

No archive expiry or automatic deletion is configured. At 2 GiB of raw archive
storage or less than 2 GiB free, capture pauses and preserves existing data. A new
capacity/retention decision is required; the helper does not reclaim space silently.

## Install deliberately

Review this directory and run the tests before copying the bundle to Slim. The
Linux installer requires root and refuses to overwrite an existing vault or skill:

```sh
sudo python3 install.py
```

It creates the private vault and state directory, installs the helper and systemd
units, appends a marked Hermes SOUL reminder with a backup, runs the first capture,
then enables the timer. It changes no existing collector, DNS, firewall, alert rule
or retention setting. If the initial capture fails, inspect its receipt and journal
before enabling the timer; this is not a transactional installer.

On the Mac, create a separate `slim-telemetry` vault and copy `mirror.py` into
`~/Library/Application Support/SlimVaultMirror`. Create private `config.json` there
using `mirror-config.example.json`; use your existing trusted SSH target. Do not
commit that configuration. The pull uses privileged remote rsync over SSH to read
the private canonical vault.

```sh
python3 mirror.py          # one pull and receipt check
python3 mirror.py --loop   # every ten minutes, for the initial eight-day review period
```

The Mac loop is a detached user process in the recorded deployment, not a persistent
login service. It does not survive reboot and cannot pull while the Mac is asleep or
offline. Slim capture is independent and continues. Restart the loop after reboot;
later pulls retrieve retained objects. Existing overwritten Mac files are preserved
under `.sync-conflicts/`. Mac edits are not pushed back to Slim. iCloud sync is not
an independently verified backup or restore guarantee.

## Evidence-backed learning

The adaptation starts with an empty Slim register: no studio lessons, private
evidence, reviewer identities or performance claims are imported. It retains:

- exact cited excerpts and content hashes;
- project/role-scoped retrieval, at most five lessons and exposure receipts;
- pass/fail/not-applicable/unknown outcomes;
- failure suspension and trial/active expiry;
- two independently reviewed later-task passes plus explicit review before promotion;
- Raw/Review exports that cannot publish trusted Wiki pages by themselves;
- predeclared experiments, comparable cohorts, unknown measurements and quality gates.

Added operational metrics are DNS latency, packet loss percentage, false-alert
count, capture-gap duration and disk growth. A successful comparison still grants
no authority to change the network. Review identities are declared, not authenticated.
The studio Kanban closeout hook and correction-scoring watcher are not installed on
Slim. Retrieval and closeout are instructed through Hermes guidance; skipped checks
remain possible and must be reported honestly. No model retraining is performed.

Adapted code provenance is in `learning-loop/source-manifest.json`. Tests use
temporary synthetic stores, never the real Voltron or Slim register.

## Verify and recover

```sh
sudo systemctl status slim-vault-capture.timer slim-vault-capture.service
sudo cat /var/lib/slim-telemetry-vault/capture-status.json
sudo /usr/local/lib/slim-vault/capture.py verify
sudo -u hermes python3 /var/lib/slim-telemetry-vault/learning-loop/loop.py report
```

`capture.py read <sha256>` verifies and emits one private object. Restore a SQLite
object into a new private file and run `PRAGMA quick_check`; do not overwrite a live
database. Stop/disable the capture timer and stop the identified mirror process to
roll back scheduling. Remove only the marked SOUL reminder and installed skill.
Keep preserved evidence until its owner explicitly approves removal.

Keep raw objects, transcripts, live registers, credentials, backup archives and
private machine configuration out of public Git. The repository stores tooling,
templates, synthetic tests and documentation only.
