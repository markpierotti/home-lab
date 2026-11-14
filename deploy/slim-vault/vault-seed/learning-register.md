---
title: Network learning and optimisation register
created: 2026-10-20
updated: 2026-10-20
type: summary
tags: [slim, review, operations, evidence]
sources: [source-register.md]
confidence: high
contested: false
contradictions: []
---

# Network learning and optimisation register

## What improvement means

Mark wants Hermes to improve its network diagnosis and optimisation recommendations over time. This archive supplies durable evidence and retrievable notes; it does not retrain a model or itself prove better performance. The Voltron learning-loop implementation has explicit scope, independent review, outcome evidence and promotion gates. This vault adopts that discipline as a recorded workflow, an adapted executable local recorder with a fresh Slim-only register. The studio Kanban hook and automatic correction-scoring watcher are not installed on Slim.

## Loop

1. Capture an incident, exact evidence, attempted action and observed outcome.
2. Propose a narrow lesson with scope, counterexamples and a future check in `Review/proposals/`.
3. Independently review the source and distinguish an observation from a cause hypothesis.
4. Before a later diagnosis, retrieve at most five relevant approved lessons and record which were used.
5. Record pass, fail, not applicable or unknown, with new evidence. A repeated failure reopens the lesson.
6. Promote only after Mark accepts the evidence; preserve previous versions and contradictions.

## Optimisation proposal requirements

Declare the problem, baseline interval, specific change, target metric, safety/quality constraints, affected devices, trial period and rollback. Measure before and after under comparable load. Include DNS latency/failure, packet loss, availability, capture drops, CPU, memory or disk growth only where relevant. Unknown measurements remain unknown. An improvement in one metric cannot hide a regression in connectivity or isolation.

Live changes to DNS, firewall, VLANs, firmware, SSH/authentication, collectors, alert rules or service configuration require Mark's explicit approval of the concrete change and rollback. Self-improvement is not permission for autonomous network reconfiguration.

## Initial candidates

| Candidate | Evidence status | Outcome |
|---|---|---|
| Correlate boot-time changes with uptime before labelling reboot | User screenshot and attributed Hermes explanation; source correlation pending | No verified follow-up tasks |
| Preserve records before source retention removes them | Retention inspected and archive mechanism tested | Seven-day operation and restore still pending |

## Weekly review

Count confirmed lessons, unknown outcomes, false alerts, repeated mistakes and quality regressions. Keep tool mechanism tests separate from demonstrated diagnostic improvement. Start with zero proven optimisation gains.

Related: [[review-plan]] · [[incident-register]] · [[SYSTEM]]

## Installed mechanism

- Recorder: `learning-loop/loop.py`; canonical state: `learning-loop/data/register.json`.
- Raw/Review bridge: `learning-loop/brain.py`; target `Wiki/network-learning.md` is a proposal until Mark approves it.
- Experiment recorder: `learning-loop/optimise.py`, adapted for operational metrics.
- Fresh register: zero lessons, zero observations, zero proven network gains at installation.
- Startup guidance tells Hermes to retrieve at task start and record outcomes at closeout. This is instructed, not a code-enforced chat gate.
- The studio register inspected at setup had 6 exposure receipts, 14 recorded passes and 0 independently reviewed passes; these counts are not evidence of causal improvement and are not imported into Slim.

The same promotion discipline is useful here; Herbert-specific rules, private evidence and studio trial states are not transferred. Use the local register report for current counts.
