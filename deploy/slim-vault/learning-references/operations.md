# Local operations

Runner: `/var/lib/slim-telemetry-vault/learning-loop/loop.py`

Use `python3 "<runner path>" ACTION --input /path/to/input.json`.

**Write each input JSON with the file-writing tool, then run the runner as one plain command.** Put the file at `/tmp/hermes-learning/<task-id>/<name>.json` (for example `start.json`, `obs-1.json`), outside the repository so the worktree stays clean. Evidence text is data, not shell: inside a heredoc or `echo` it breaks on quotes and newlines, and the governed-action gate cannot tell quoted prose from an operation, so it correctly stops for Mark. A plain `python3 "<runner path>" ACTION --input <file>` is a command both gates can read in full. This is not a way around approval. Both calls are still checked, and if either one stops for approval, wait for Mark; never rephrase a command to get past a prompt. Don't embed evidence in shell arguments. The default register is shared by the installed studio and delivery roles and protected by a local file lock. Do not use `--store` for real work; that switch isolates tests only. Register changes are local and never update kanban, credentials, policies or model settings.

## Start

`start` input:
```json
{"project":"slim-home-lab","role":"slim-home-lab","task":"actual-session-or-card-id","actor":"profile/session-id","actor_family":"anthropic"}
```
Use `slim-home-lab` for portfolio project scope. Role is the actual profile name, including `slim-hermes`, `slim-hermes`, or `slim-home-lab-lead` where applicable. For new intake use project `intake:<slug>` until an approved project exists. Unknown model family is `unknown`, never guessed. Preserve the returned exposure ID for closeout.

## Capture candidate

`add` input:
```json
{
  "title":"Concrete recurring failure",
  "cause":"harness",
  "projects":["slim-home-lab"],
  "roles":["slim-home-lab","executor","reviewer"],
  "trigger":"A specific situation",
  "guard":"A narrow preventive check within existing authorization",
  "check":"Observable evidence that would show the check worked",
  "author":"actual-profile/session-id",
  "author_family":"anthropic",
  "evidence":[{"path":"/absolute/path/to/evidence.md","quote":"Exact short excerpt"}]
}
```
The recorder requires matching excerpts and records source/excerpt hashes. It stores only excerpts, not entire files. Common credential patterns are rejected, but manually remove personal or sensitive data before capture. No raw databases, environment files or credential files. Historical snapshots establish what was cited at capture, not whether the whole source is currently authoritative. Re-read current requirements before applying any lesson.

Causes: `model_judgment`, `requirements`, `harness`, `quota`, `mixed`, `unknown`.

## Trial or retirement

`transition --id L-…` input:
```json
{"state":"trial","reason":"Source checked; bounded guard is relevant","reviewer":"actual-profile/session-id","evidence":[{"path":"/absolute/path/to/review.md","quote":"Actual evidence-review conclusion"}]}
```
A trial lasts 14 days. For `suspended` or `retired`, only state and reason are needed. Revisions create a new candidate; include the predecessor ID in its evidence/review note. Do not remove old history.

## Outcome

`observe` input:
```json
{"exposure":"E-…","lesson":"L-…","outcome":"unknown","note":"What happened and what is unverified","evidence":[{"path":"/absolute/path/to/task-evidence.md","quote":"Exact observed result"}]}
```
Valid outcomes: pass, fail, not_applicable, unknown. Retried attempts on the same card are not independent tasks. A failure suspends the lesson immediately. Missing outcomes never count as passes.

## Independent review and promotion

`review-observation --id O-…` input:
```json
{"review_kind":"independent_model","reviewer":"actual-reviewer-session","reviewer_family":"openai","evidence":[{"path":"/absolute/path/to/review.md","quote":"Actual review of the observed preventive check"}]}
```
Reviewer must differ from task actor and lesson author; an independent model must differ in family from both. For real human review use `review_kind: human`, the actual person's identity and `reviewer_family: human`. Merely writing these fields does not establish independence: verify provenance and quote the actual review. Never impersonate Mark.

After two independently reviewed passes on distinct later tasks, use `transition --id L-…` with `state: active`, `reason`, and the same independent-review fields. Active guidance lasts 30 days. Promotion is explicit, never a side effect of a successful test.

## Reports and evaluator bridge

- `report`: counts and limitations, without model rankings.
- `show --id L-…`: one lesson including its evidence.
- `import-evaluator --evaluator "<Voltron>/performance-evaluator/data"`: idempotently imports completed-attempt metadata as diagnostic signals, never executable guidance. A failed citation check is a runner/review diagnostic, not a substantive delivery finding.

The bridge is manual/local. No daemon or schedule is installed. Do not rerun paid evaluations under this skill.
