---
title: "Incident register"
created: 2026-10-20
updated: 2026-10-20
type: summary
tags: [slim, incident, evidence]
sources: []
confidence: medium
contested: false
contradictions: []
---

# Incident register

## Reboot alert recurrence — 20 October 2026

- User supplied a Telegram screenshot of an alert firing at 14:12 and resolving at 14:26/14:27. Hermes attributed it to a one-second boot-time shift and reported monotonic uptime.
- Hermes's explanation also references a similar 02:12–02:27 alert. This remains an attributed interpretation, not independently verified by vault setup.
- The earlier source review showed the CPU code treats a changed btime as reboot identity. Do not treat btime as a clock-adjustment-proof identifier without checking kernel behaviour.
- Next: correlate saved samples, alert history and NTP/syslog evidence, then propose a correction that covers the collector and alert rule together.
- Status: **open for evidence review**. No production reboot rule was changed by this setup.

Related: [[Review/proposals/reboot-alert-2026-10-20]] · [[review-plan]] · [[Tasks]]
