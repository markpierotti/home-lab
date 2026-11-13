---
title: "Runbook"
created: 2026-10-20
updated: 2026-10-20
type: summary
tags: [slim, operations, backup]
sources: []
confidence: high
contested: false
contradictions: []
---

# Runbook

## Inspect on Slim

```sh
sudo systemctl status slim-vault-capture.timer slim-vault-capture.service
sudo cat /var/lib/slim-telemetry-vault/capture-status.json
sudo journalctl -u slim-vault-capture.service --since today
sudo /usr/local/lib/slim-vault/capture.py verify
```

Read one raw object with `/usr/local/lib/slim-vault/capture.py read <sha256>` as Hermes or root. This emits the captured private content; do not send it to public tools. For a SQLite restore, redirect a verified object's bytes to a new private file, run `PRAGMA quick_check`, and inspect the copy rather than overwriting the live database.

## Capture and mirror

Capture runs every ten minutes through a systemd timer; it also runs once at installation. Mac mirroring runs every ten minutes while its detached runner is alive, for up to eight days, with no deletion synchronization. Each pull checks the capture-status receipt and writes a local mirror-status receipt. If the Mac is off or asleep it cannot pull; later pulls catch up with retained raw objects. iCloud sync itself is outside this helper's control.

The Mac vault is a read copy. Edit canonical notes through Hermes on Slim. Do not assume Obsidian edits on the Mac reach Slim. Mirror conflicts are kept in `.sync-conflicts/` and require manual reconciliation.

## Failure handling

A storage guard, unreadable source or SQLite error is recorded in a receipt and fails the capture service. The next timer attempts again; existing evidence is never deleted to fix the error. The Mac mirror reports capture failures or stale captures through Hermes Telegram, retrying notification after connectivity returns. It cannot report while both paths are unavailable.

If raw history approaches 2 GiB, review capacity and move an explicitly verified copy to appropriate long-term storage before changing limits. Do not remove archived evidence automatically.

## Rollback

Stop and disable `slim-vault-capture.timer`. Stop the Mac mirror runner using its saved PID only after confirming the command matches `mirror.py`. Remove only the marked Slim-vault section appended to Hermes SOUL.md and its installed `slim-telemetry-vault` skill. Existing services and retention were not modified. Keep both vaults and the initial snapshot until Mark explicitly authorizes removal.

Related: [[architecture]] · [[SYSTEM]] · [[review-plan]]
