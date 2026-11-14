# Operations-plan review dispositions — 20 October 2026

Owner-supplied advisory reviews from Argon and Claude considered the plan at
`c0deef6`. This disposition records source-supported changes and qualifications;
it is not certification of live deployment or approval to repair production.
The private review artifact and household evidence are not republished here.

**Direction:** preserve the full systems/network/recovery/platform/security operations
remit. Start with one operator and domain playbooks plus deterministic sensors and
verification. The earlier fixed six-specialist rollout was premature. Additional
profiles remain an option after workload, access and quality evidence supports them.
The [revised plan](../plans/autonomous-operations-20261020.md) names enforceable
ownership and keeps privileged execution outside the first milestone.

## Inspection and limits

Re-read the actual repository role/configuration, alert rules and notifications,
three Hermes scripts, syslog metrics, rsyslog timestamp template, sandbox, exporter
defaults, backup producer and Mac pull script. This extends the reviewers' stated
coverage where they had only documentation or headers. No runtime source edits,
new tests, live host commands, model jobs or privilege changes were made for this
review round. Private live configuration still needs the safe reconciliation export
in the [coverage review](../plans/operations-coverage-20261020.md).

Also read six upstream Hermes files at the immutable commit
[`d923a5eb487a17c0a68801bba9ef0f56c81040a8`](https://github.com/NousResearch/hermes-agent/tree/d923a5eb487a17c0a68801bba9ef0f56c81040a8),
target of the annotated `v0.22.2` tag: approval, webhook, coalescer, cron jobs,
cron executions and task board. This verifies selected tagged-source capabilities,
not Slim's installed bytes or complete runtime behavior.

## Argon findings

| ID | Disposition | Source-supported conclusion and qualification |
| --- | --- | --- |
| F1 — topology Critical | **Accept simplification; reject Critical defect classification.** | The old proposal explicitly said roles/profiles are not permission boundaries and gated runtime compatibility. Disabled delegation prevents assuming the proposed routing already works; it does not make a future role catalogue a current critical vulnerability. Remote model calls are not local model inference, so RAM/model reasoning settings alone do not prove incapacity. Begin with one operator; give trusted sensors/verifiers ownership outside its writable home. Keep the wider professional remit. |
| F2 — false healthy/state reset | **Accept core correctness findings.** | Snapshot command failures and unreadable histories can become empty/“none”; non-finite Prometheus output is another uncovered path. Watcher state-load failure can invoke first-run suppression. Syslog metrics does not validate its own `SLIM_IP`, although the example service supplies it. A reset can replay counts, not necessarily leave every counter at zero. Distinguish explicit bootstrap, corrupt/lost state, partial coverage and counter epoch; do not assume file-not-found always means no events. |
| F3 — clock cascades/reboot query | **Accept clock/reboot work; do not adopt the proposed query.** | The present reboot rule reacts to one-second shifts; wall-clock ages and retention need uncertainty handling. The proposed five-minute offset can miss events after a scrape gap or during short successive uptimes. Claude's `resets()` alternative is also only a candidate until gauge/rollback/freshness cases are tested. The checked-in rsyslog template uses Slim arrival time, so its outer timestamp is not the ASUS clock; confirm deployed template before attributing remote skew. |
| F4 — upstream-bypass annotation | **Accept removal in a scoped source fix.** | The Unbound alert explicitly recommends public resolver substitution. That conflicts with the intended sole-Unbound path and should be replaced by reviewed diagnostics. It is not itself evidence that a bypass occurred or that an agent can change it. Alert text must not authorise a repair. `dig +dnssec` alone is not a full DNSSEC-validation test. |
| F5 — dispatch/delivery/coalescing | **Accept dispatch/delivery distinction and bounded retry work.** | Transform dedupe is persisted before agent completion; a resolved-only payload does not refresh pending firing context. Tagged upstream confirms in-memory coalescing, early HTTP 202 and a cron execution ledger. Neither a `cron_job` flag nor a self-written completed field is durable end-to-end delivery. See the compatibility constraint below. A new `--alerts` flag must be implemented/tested before a prompt relies on it; current snapshot has no such interface. |
| F6 — rewrite amplification | **Accept byte-bounded retention with hysteresis.** | Keeping 5,000 lines may leave the file above its rewrite threshold, causing repeated full rewrites on later events. A 2,000-line cap also cannot guarantee a byte limit. Define actual byte high/low watermarks, bounded record size and observable overflow. Flash endurance harm has not been measured; do not treat that consequence as established. |
| F7 — PS5 coverage | **Accept a privacy-gated requirement, not automatic new access.** | No narrow Sony-query detector appears in reviewed source. Observability/Security/DNS own the proposal. Counting a lookup does not enforce isolation or prove connectivity; parental controls and DNS restrictions remain independently necessary. The suggested SQL wildcard predicates are not an accepted domain classification policy. Match explicit approved names/suffix boundaries and handle database rotation/cursors without exposing household history. |
| F8 — no-data settings | **Accept rule-by-rule contracts; reject blanket replacement.** | Seven rules use `noDataState: OK`. Review expected series, absent metrics, scrape health, query errors and retired inventory separately. `up` does not cover every missing metric and is itself unable to represent a target removed entirely from discovery. Route unknown/failure explicitly without multiplying redundant alerts. |
| F9 — backup success | **Accept and elevate source completeness work.** | Inspection of the producer confirms the inner configuration tar command uses `--ignore-failed-read`, suppresses diagnostics and ends with `|| true`; an outer archive and success timestamp can therefore be published despite incomplete configuration capture. The Mac pull script logs transfer failures but need not exit nonzero overall. No claim is made that a particular live archive is corrupt. Require mandatory-member/completeness results, separate local/off-host/restore states and receiver-confirmed receipts; preserve the read-only backup key. |
| F10 — parser/batch/heartbeat | **Accept bounded follow-ups with more precise fixes.** | Generic IP matching can confuse source and destination and omits IPv6. Alert batches are truncated before full state handling; merely sorting firing first can instead lose important resolutions. Preserve transition accounting or signal explicit overflow. A successful Pi-hole cache answer does not establish Unbound/recursive availability; expose those capabilities separately rather than promise an uncached end-to-end DNS check. |

## Additional Claude findings incorporated

- **Actual authority:** the service sandbox protects system writes but the operator
  can write within its own home. Root ownership of scripts under a replaceable
  parent is not by itself sufficient. Place trusted code/evidence outside operator
  write access or enforce and validate read-only mounts. The tagged
  [approval implementation](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/tools/approval.py#L1072)
  passes commands not matched as dangerous; an empty `command_allowlist` is not a
  deny-all shell policy. No enforced destination allowlist appears in the reviewed
  service drop-in; current firewall reachability was not tested here.
- **Communication dependency:** direct Grafana notifications are model-independent,
  not independent of Telegram/WAN/clock failure. Verify existing Healthchecks email
  delivery and notification-stage health. Endpoint acceptance does not guarantee
  human receipt; an off-host heartbeat is not an unconditional delivery guarantee.
- **Watcher delivery:** advancing state before stdout/delivery can lose the owner
  notice even though local event history remains. Include watcher output in delivery
  outcome accounting, not just webhook investigations.
- **Interim command safety:** while Mark is the only executor, cite reviewed
  runbooks/action IDs. Model-authored privileged commands require review before
  becoming copy/paste instructions. A complex broker is not justified in milestone one.
- **Arithmetic and missing data:** pre-compute converted timestamps/deltas and reject
  NaN/Inf; distinguish query/parse errors from service DOWN and unavailable history
  from no events. The screenshot's conversion error is corrected in incident PR #2.
- **Coverage and operating objectives:** name ownership for narrow privacy bridges,
  host/Grafana authentication, possible gateway logs, provisioning drift, off-host
  copies and restored function. Add explicit maintenance scope/expiry and graded
  severity. Do not invent human deputies.
- **Resources:** measure Hermes RSS/process use and session growth before setting
  limits. Coalescing is not a global concurrency lock; terminal timeout is not an
  agent deadline. Reviewer dollar estimates, wake counts and turn limits are
  proposals, not validated price/budget guarantees. A “wake” may involve multiple
  model invocations, and retries still need budget authorisation.

## A newly checked compatibility constraint

The tagged
[coalescer validator](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/gateway/platforms/webhook_coalesce.py#L27)
rejects combining `cron_job` with `coalesce`. The
[webhook cron trigger](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/gateway/platforms/webhook.py#L568)
returns 202 while a background task starts the job. The
[execution ledger](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/cron/executions.py#L1)
explicitly is not a retry queue. Its job records distinguish `delivery_failed`.

Thus a migration must define durable intake before acknowledgement, correlation
outside the incompatible coalescer, job identity, claim/lease, bounded retry and
separate delivery outcome. It must check installed compatibility and exercise the
pre-claim crash window. Tagged board code offers coordination primitives, but an
agent-writable board can never approve a privileged action. No route migration is
performed or represented as complete by this review.

## Next implementation slices

1. **Reconcile live metadata safely:** obtain the existing operator/Grafana export
   without secrets. `node_timex_sync_status` is already independently observed on
   Slim; timex error metrics and exact live routing remain to check.
2. **Correct observation truth and safety:** explicit unknown/error/non-finite
   handling; state validation/bootstrap; byte retention; valid source parsing;
   reviewed alert guidance and a per-rule no-data matrix. Treat backup completeness
   as its own urgent source fix, not as a later dashboard enhancement.
3. **Add focused health coverage:** NTP and automation-stage freshness first;
   compare reboot candidates with fixtures; baseline Wi-Fi and degradation in shadow
   mode. Inspect authentication/security requirements without granting private-data
   access automatically.
4. **Make follow-up work recoverable:** validate the supported execution path,
   durable intake/delivery receipts, actual concurrency and authorised retry/spend
   limits. Retain the same owner-facing operator and add domain playbooks.
5. **Consider supervised repair later:** owner-approved playbook, restricted action
   identity and deterministic independent verification. No sudo-capable agent,
   polkit restart permission or automatic repair is introduced now.

The owner has already chosen the broader operations-team scope; do not ask him to
reconfirm it. Decisions needed before their corresponding implementation are new
private-query access, egress/identity changes, live maintenance, additional model
spend and any action-specific repair authority. Existing approved notification
channels should be verified before asking to choose replacements. Role/profile
counts and arbitrary thresholds do not need to block the first correctness work.
