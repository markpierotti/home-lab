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

No archive expiry or automatic deletion is configured. At 3 GiB of raw archive
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

The current Mac deployment uses an existing Hermes job every thirty minutes,
calling `~/.hermes/scripts/slim-vault-mirror.sh`; `cron-entry.sh` is its source.
Copy `run-mirror.sh` beside the deployed mirror. These wrappers preserve failed
exit status and do not perform prolonged iCloud hydration retries. `--loop` remains
available for a foreground review period; do not run competing loops deliberately.
An exclusive lock skips overlapping invocations without replacing their receipts.

The pull uses a private local receiver under
`~/Library/Application Support/SlimVaultMirror/receiver`, outside iCloud. The
earlier `-W`-only repair still allowed openrsync to mmap an old iCloud file and
failed on 29 October at 12:00. rsync now receives into this local folder; the
publisher reads only local source files, writes new temporary destination files
and replaces changed copies by rename. Existing overwritten Mac files are moved
under `.sync-conflicts/` without reading their contents. Local-only files remain,
and edits are not pushed to Slim. Metadata-matching copies are skipped. The capture
status marker is published last. The local receiver consumes additional disk space
and contains private evidence; do not put it in Git or treat it as a separate backup.

The mirror checks capture age/errors and the referenced local manifest before
publication; a good transfer does not prove complete capture history. Notifications
distinguish copy failures, source-receipt problems and delivery errors.
`--no-notify` supports manual checks.

The Mac cannot pull while asleep or offline, and its scheduler must be running.
Slim capture continues independently; later pulls retrieve retained objects.
iCloud permissions may still prevent an unattended run, so inspect its receipt.
iCloud sync is not an independently verified backup or restore guarantee.

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

The active `agent.log` and `asus.log` start a new
`log-base` on the first capture of each Brisbane day, on inode changes, or
when the previous byte prefix no longer matches. Subsequent `log-append`
records store only new bytes and link to the previous manifest for that
source. Rotated files already matched by source discovery are still captured
as whole files. For rename rotation, the whole rotated file preserves the unread tail while
it remains available and within capture limits. A tail can be lost if the
rotated file disappears before capture or rotation uses copytruncate.
The collector rewrites `outcomes.jsonl` as a rolling window, so it remains a
whole-file snapshot. The prefix check reads the whole active log, which remains
subject to the 64 MiB source limit.

`executions.db` and `state.db` use the first successful SQLite backup of each
Brisbane day. Changes between snapshots can be missed. The manifest counts
cadence skips under `deferred`.

To reconstruct a log version, pass a manifest that recorded that source:

```sh
sudo /usr/local/lib/slim-vault/capture.py restore-log   "raw/captures/<date>/<capture>.json" /home/hermes/.hermes/logs/agent.log
```

Restoring checks byte ranges, object hashes and the resulting file hash.
Keep every referenced manifest and object when retaining or copying a log
chain. Historical manifests and objects are left as they were. If older objects
were pruned from Slim, use the verified off-host copy for those references.
The mirror copies files and checks the receipt. Its success does not establish
chain completeness. `verify` checks hashes of objects present on disk.

`capture.py read <sha256>` verifies and emits one private object. Restore a SQLite
object into a new private file and run `PRAGMA quick_check`; do not overwrite a live
database. Stop/disable the capture timer and stop the identified mirror process to
roll back scheduling. Remove only the marked SOUL reminder and installed skill.
Keep preserved evidence until its owner explicitly approves removal.

Keep raw objects, transcripts, live registers, credentials, backup archives and
private machine configuration out of public Git. The repository stores tooling,
templates, synthetic tests and documentation only.
