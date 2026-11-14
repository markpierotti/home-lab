# Measuring pipeline improvements

Use the same `loop.py` runner and temporary JSON inputs as `operations.md`. This recorder stores proposals and reviewed measurements; it never changes the pipeline.

## Plan before changing anything

`plan-experiment`:
```json
{
  "title":"Reduce clarification rework with a decision-source checklist",
  "hypothesis":"A short source check will reduce avoidable corrections without weakening acceptance",
  "change":"One bounded change to the handoff checklist",
  "rollback":"Remove the trial checklist and suspend its associated lesson",
  "cohort":"small-doc-handoff-tier1",
  "role":"slim-hermes",
  "owner":"actual-profile/session-id",
  "projects":["actual-project-slug"],
  "metric":"user_corrections",
  "target_reduction_percent":25,
  "evidence":[{"path":"/absolute/path/to/baseline-evidence.md","quote":"Exact evidence motivating the change"}]
}
```
Cohort must specify comparable task type, size/risk, quality gates and material environment/model conditions. Hold those conditions stable. Do not compare a large regulated build to a landing-page copy fix. Use one meaningful change at a time. `projects` lists actual eligible slugs; before project creation, use a stable `intake:<slug>` identifier.

Available primary metrics: `user_corrections`, `handoff_failures`, `rework_rounds`, `cost_usd`, `elapsed_minutes`. Cost must be task-exclusive actual reported cost, not summed overlapping sessions. Unknown or subscription allocation is null. Elapsed time includes waiting; never describe it as active work. Do not invent baseline measurements.

The experiment begins as a proposal. Record existing explicit scoped authorization with `authorize-experiment --id X-…` using actor, scope and exact evidence. If authorization already covers the trial, cite it rather than asking again. This record does not grant permissions; any governed change must still pass its applicable gate. No budget/model/hook/service change is performed by the recorder.

## Measure comparable real tasks

`measure`:
```json
{
  "experiment":"X-…","phase":"baseline","cohort":"small-doc-handoff-tier1","role":"slim-hermes",
  "project":"actual-project-slug","task":"actual-card-or-session-id","actor":"actual-actor/session","actor_family":"anthropic",
  "user_corrections":2,"handoff_failures":0,"rework_rounds":1,"cost_usd":null,"elapsed_minutes":null,"quality_pass":true,
  "evidence":[{"path":"/absolute/path/to/observations.md","quote":"The independently checkable counts and acceptance outcome"}],
  "review":{"review_kind":"human","reviewer":"actual-reviewer","reviewer_family":"human","evidence":[{"path":"/absolute/path/to/review.md","quote":"Actual review of the measurements and quality"}]}
}
```
Use `phase: trial` only after scoped authorization is recorded. Human or independent-family review must be real, not impersonated. Unknowns remain null. Retried runs on one task are one sample; a task cannot appear in both groups. Record an observed quality failure even if cost improved; the assessment flags it as a reason to stop the trial. The runner cannot stop live workers, so surface that outcome to the task owner through the normal permitted workflow.

`experiment-report --id X-…` compares medians only with at least three distinct tasks per group, complete primary metrics and known quality outcomes. This small sample is a screening signal, not statistical/causal proof. Matching cohort labels are not proof of comparable work; the reviewer must check them. A positive result is `target_observed_review_required`, never automatic policy adoption. Apply a retained improvement only within current authorization and keep its rollback and affected artifact paths in the project decision record.

## Second-brain bridge

Production mutations automatically call `sync-brain` after capture, review, outcomes or measurements. Start/read operations do not publish. The bridge writes immutable, hashed snapshots under `raw/learning-loop/` and exact pending proposals under `Review/`. It never writes compiled Wiki pages, index or log. Unchanged content is not duplicated. A sync problem does not erase the learning event; retry `sync-brain` after fixing it.

To publish trusted knowledge, use the existing `llm-wiki-review` workflow. Before applying an explicitly approved proposal, run `validate-brain --proposal <path>` to check register freshness, target hash and exact proposed-content hash. If stale, prepare a new snapshot and review it. Do not impersonate approval or treat independent-model lesson review as human Wiki approval. Maintain the Wiki schema, links, index and log after the approved write.

Studios load live scoped guidance, not copied Wiki instructions. Read the Wiki for rationale and reusable context. Project-specific product rules stay in their authoritative decision logs. A lesson that should transfer to other projects is a new candidate with an explicitly generalized trigger, review and scope; don't silently widen an existing lesson. Scope `*` is only for reviewed platform procedures, never project business rules.

Future project bootstrap should retain the shared learning skill copied from Venture Studio, add the current startup reminder to the final lead brief, and verify retrieval using the actual project slug. This is a bootstrap requirement in the studio learning workflow, not permission to create a project before its existing approval.
