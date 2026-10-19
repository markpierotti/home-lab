# Repository split — 19 October 2026

This repository owns the broader Slim/home-lab deployment. The reporter, collector,
firmware analysis and supervised router trials remain in ASUS Router Telemetry.
The boundary follows independent deployment and testing: this repository consumes
the collector revision in `upstream/collector.lock.json`; it does not fork its code.

Initial deployment/documentation source was copied from
[ASUS Router Telemetry at b43e8cf](https://github.com/markpierotti/asus-router-telemetry/tree/b43e8cf58fcdc16a43f93096a9d2bee0984a30b6),
including PR #5 service/security work and PR #6 dashboards. Existing commit history
and original review discussions remain upstream; this repository starts with an
attributed snapshot rather than claiming a rewritten history. The MIT license is
retained. Collector source is pinned to upstream’s merged PR #5 revision.

The split changes source ownership and links. It does not move live configuration,
credentials, telemetry, DNS history, systemd services or Grafana data. Historical
records keep their original dates and limitations; the current dashboard acceptance
record supersedes the earlier source-only dashboard status.

The reconciled deployment suite passed all 81 tests as root on Slim. The syslog
filesystem guard, isolated exhaustion/recovery test and live service/mount restart
checks passed. No whole-host restore, power-loss or endurance test is claimed.
