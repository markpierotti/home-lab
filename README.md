# Home lab

Slim’s DNS, monitoring, alerting and operating configuration: Pi-hole with Unbound,
Prometheus, Grafana, private backups, an external heartbeat and a restricted Hermes
operator. The ASUS collector is a pinned dependency maintained in
[ASUS Router Telemetry](https://github.com/markpierotti/asus-router-telemetry).

The overview, Pi-hole and Router dashboards are deployed and checked on Slim at
desktop and 400-pixel widths. The root-run backup/rollback helper has privileged
regression tests. ASUS logs use a persistent filesystem with a fixed 256 MiB budget;
exhaustion and recovery were checked in isolated Linux namespaces. These are dated
acceptance observations, not a whole-host disaster-recovery guarantee.

- [Deployment examples](deploy/slim/README.md)
- [Operations and rollback](docs/slim-operations.md)
- [Dashboard acceptance](docs/slim-dashboards-20261019.md)
- [Roadmap](docs/home-lab-roadmap.md)
- [Incident observations](docs/incidents/README.md)
- [Repository split and source provenance](docs/repository-split-20261019.md)

## Collector dependency

`upstream/collector.lock.json` pins collector 1.6.2 to an immutable upstream commit
and records source hashes. Collector/reporter development stays upstream. For a new
installation, prepare `/home/rtax/app` as the dedicated `rtax` user:

```sh
git clone https://github.com/markpierotti/asus-router-telemetry.git /home/rtax/app
git -C /home/rtax/app checkout --detach 28fa4126aaa3b1f8ad1a2c6e28ab8a66d70816ab
python3 scripts/verify-collector.py /home/rtax/app
```

An existing installation needs a backup and reviewed upgrade procedure; do not clone
over it. Verification requires a pristine checkout, including no ignored or untracked
files; verify before building or running Python there. Build and independently verify the ARM reporter using upstream’s build
instructions, then configure private target identity and artifact pins. This source
verifier checks the checkout; it does not authenticate a router or approve a binary.

## Checks

Run `make test` with Python 3.11+. Tests use fixtures and contact no live devices.
Root-only rollback cases run in disposable directories and skip without root; the
Linux CI job also runs the suite as root. The opt-in filesystem exhaustion test is
documented in the operations runbook and never targets the production listener.

Examples use documentation addresses. Real credentials, private device inventory,
backups, DNS history and rendered Pi-hole screenshots must stay private.
