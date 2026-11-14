# Morning digest findings — 2026-10-20

Status: **diagnosed; fixes pending**. This record follows a read-only investigation
of Slim's morning digest. No configuration, service, alert or device inventory was
changed. Household addresses, MACs, queried domains and raw captures are omitted.

## False ASUS reboot alert

The alert fired at **02:12:37 AEST** and resolved at **02:27:37 AEST**. Saved router
telemetry first showed a boot timestamp one second lower at **02:10:53 AEST**.
Prometheus exposed the changed value at **02:11:11 AEST**.

Evidence inspected:

- The reported boot timestamp decreased by one second and remained at that value.
- Router uptime continued increasing; the inspected 24-hour metric series had no
  uptime decreases. Consecutive collector failures remained zero throughout it.
- The saved sample at the change had `derived.cpu_utilisation.state = "reboot"`
  and no aggregate CPU percentage, despite continued uptime.
- Grafana's alert history recorded the firing and resolution above.
- The rule evaluates `changes(rtax_router_boot_time_seconds[15m]) > 0`. Any change
  qualifies; resolution follows when the change leaves that window.
- Upstream `cpu.detect_reboot()` returns true whenever two available `boot_time`
  values differ, before considering uptime.

This is a false reboot classification in both the collector and the alert rule.
The digest's suggested collector blip is unsupported: collection failures were not
observed. The cause of the one-second timestamp adjustment was not established;
NTP or another clock adjustment was not independently demonstrated.

The claim that `/proc/stat`'s `btime` is an immutable, clock-independent boot
identity is contradicted by these saved observations. This finding does not
invalidate the counts or version boundaries of earlier acceptance trials.

## Known device reported as unknown

The DNS client labelled `UNKNOWN` had the **same MAC address as the existing
phone entry** in the private inventory, but its observed IP differed from the
saved IP. Pi-hole's network record and Slim's neighbor entry agreed on the MAC;
Pi-hole also reported an Apple vendor. The inventory match identified the recorded
phone without relying on its DNS queries.

`slim-snapshot.py` builds its client-name lookup from saved IPs only. It does not
join a currently observed address to the inventory's MAC, so this address mismatch
caused a false unknown-device label. The investigation did not establish why the
address changed or when the saved mapping became stale. Query volume alone was
not evidence of a new or malicious device.

## Pending work and acceptance criteria

1. **ASUS Router Telemetry:** correct reboot detection and its clock-independent
   identity claims. Add a regression for a one-second `btime` change with rising
   uptime and CPU counters, alongside genuine reboot and counter-reset cases.
   The companion finding is `docs/reboot-detection-20261020.md` in
   [ASUS Router Telemetry](https://github.com/markpierotti/asus-router-telemetry).
2. **Home lab:** revise the Grafana reboot rule to use corroborating evidence;
   changing the collector alone does not fix this rule. Check both the observed
   false-positive case and a genuine reboot case before claiming resolution.
3. **Home lab:** resolve DNS clients using current address-to-MAC evidence and the
   private known-device inventory. Test changed IPs, missing or ambiguous identity
   information and genuinely unknown devices. Preserve uncertainty where the
   available mapping is insufficient; do not silently rewrite the inventory.
4. **Digest guidance:** distinguish observations from hypotheses and pending
   defects. An alert that resolves is not proof that its detection logic was sound.
5. Review and test source changes before a separately authorized deployment; record
   live verification separately. No fix or deployment is claimed by this note.

## Evidence limits

The investigation read saved collector samples, Prometheus history, the local
Grafana alert ledger, private inventory, Pi-hole network metadata and Slim's
neighbor entry. Raw evidence remains private and is not imported into Git. This
sanitized summary is not independent authentication of those private records.
No induced reboot, outage, endurance test or notification-delivery test was run.
