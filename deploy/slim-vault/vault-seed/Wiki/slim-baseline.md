---
title: "Slim baseline"
created: 2026-10-20
updated: 2026-10-20
type: summary
tags: [slim, telemetry, operations]
sources: []
confidence: high
contested: false
contradictions: []
---

# Slim baseline

## Observed on 20 October 2026

Slim runs Ubuntu with Hermes gateway, Pi-hole, Prometheus/Grafana, native router collection and ASUS syslog processing. The existing collector records a nominal 60-second interval and retains 1,440 samples. Hermes has two recurring jobs: ASUS log watcher once per minute and morning digest at 08:00 Australia/Brisbane.

Slim has about 13 GiB free at setup; raw ASUS syslog is on a separate approximately 224 MiB filesystem. The existing system backup runs nightly and retains 14 archives. Its selected sources omit Hermes's conversation database, memories and job outputs; this vault adds those selected records without changing that backup job.

## Limits

This baseline records observed configuration, not proof that every configured timer ran on schedule. A first capture and mirror check are acceptance evidence for the archive only. Neither the monitoring stack nor the archive has completed a seven-day acceptance period through this setup.

Related: [[architecture]] · [[retention-register]] · [[review-plan]]
