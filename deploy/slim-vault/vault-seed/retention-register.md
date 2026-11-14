---
title: "Live retention and archive coverage"
created: 2026-10-20
updated: 2026-10-20
type: summary
tags: [slim, retention, evidence]
sources: []
confidence: high
contested: false
contradictions: []
---

# Live retention and archive coverage

Observed read-only on Slim, 20 October 2026. These are live-source rules, not guarantees about the new archive.

| Source | Live retention | Vault treatment |
|---|---|---|
| ASUS watcher run outputs | Latest 50; about 50 minutes at one/minute | Capture available outputs every ten minutes |
| Morning digest outputs | Latest 50; about 50 days at one/day | Capture available outputs |
| Completed one-shot jobs | Eligible for sweep after 7 days | Execution/delivery database snapshots; not a full job-config archive |
| Hermes conversations | No automatic pruning/archiving enabled in current config | SQLite-safe state.db snapshots |
| Hermes memory | No expiry found; selective 2,200-character MEMORY limit | Capture changed Markdown revisions |
| Scratch | Eligible after 24 idle hours; cleanup activity-triggered and throttled | Not copied wholesale; do not leave durable findings there |
| Agent/gateway logs | 5 MiB plus three rotated files | Capture selected changed files |
| Hermes error log | 2 MiB plus two rotated files | Capture selected changed files |
| Router samples | 1,440 and 256 MiB; about 24 hours at one/minute | Capture available samples, preserving older objects |
| Collection outcomes | 5,000 and 32 MiB; about 3.5 days at one/minute | Capture changed outcomes file |
| Pending cleanup | Collector never auto-prunes | Capture revisions |
| Event/alert JSONL | On crossing 1 MB, retain last 30 days and newest 5,000 entries | Capture revisions |
| ASUS syslog | Daily; 30 rotated files; maxsize 50 MB when rotation runs | Capture current and rotated files; underlying syslog filesystem is only ~224 MiB |
| Prometheus | 30 days or 2 GB, whichever removes data first | Selected exported metric files only; no full TSDB archive |
| Pi-hole query DB | 91-day max age | Not continuously archived by this vault |
| Pi-hole text DNS log | Daily, five rotated files | Not continuously archived by this vault |
| Pi-hole FTL/web logs | Weekly, three rotated files | Not continuously archived by this vault |
| System journal | No explicit time cap; size/disk-pressure limits apply | Not continuously archived by this vault |
| Slim system backups | Nightly ~03:30–03:45; newest 14 backups | Separate policy; existing backup does not include Hermes memory/history |

Rotation does not immediately delete the rotated file; deletion happens when the retained count is exceeded. Size-triggered windows cannot honestly be expressed as a fixed number of days. The new archive has no automatic expiry, but capture pauses at storage guards. No completeness claim is made for data already pruned before setup.

Related: [[architecture]] · [[review-plan]] · [[runbook]]
