---
name: document
description: Write the run's change doc — one entry per use case, sourced from the /review verdict and detailed by reading the diff at each cited line. Works for any issue class (chore, bug, feature). Use as the final pipeline step after an approved review. Writes one markdown file and emits a JSON verdict; it does not edit code.
argument-hint: <spec-path> <adw-id> <verdict-path>
---

# Document

Write the run's change documentation. The run may have been a chore, a bug fix, or a feature — the spec's class determines the framing, not this command's defaults. You are a **recorder, not an author** — you describe what the diff actually contains. You never infer intent that isn't in the spec, and you never describe a change you haven't read.

`/review` has already traced the work: its verdict names every use case, its outcome, and the `file:line` that implements it. You do not re-derive that. You take it as given and go read what it points at.

## Variables

- `verdict` — `$3`, path to the JSON verdict emitted by `/review`. Its `use_cases[]` is the spine of the doc: one entry per element, in order. `out_of_scope[]` and `review_summary` frame the run's outcome.
- `spec` — `$1`, path to the plan spec, written from a `/templates:{class}` template. Supplies the class and the root cause for the *Overview*; it is not re-traced.
- `class` — the issue class, read from the spec: `chore`, `bug`, or `feature`. Sets the doc's framing.
- `adw_id` — `$2`, the run id; names the output file and stamps the doc.
- `diff` — read on demand, at the `file:line` each use case cites. Never swept whole.
- `doc` — the output path, `app_docs/{class}-{adw_id}-{slug}.md`, where `slug` is a 2–3 word kebab-case name taken from the spec title.

## Instructions

- **The verdict says where; the diff says what.** Each use case arrives with an `evidence` citation. Read the code at that citation and describe how the use case was implemented.
- **Add, never restate.** Every entry must say something the verdict did not. Reformatting `name` / `verdict` / `evidence` into markdown is a failed entry — if you have not opened the cited file, you have nothing to write.
- **Read narrowly.** Open only what the citations point at. This command does not survey the diff, count hunks, or catalogue supporting changes.
- **Walk in verdict order** — `use_cases[]` first → last; never reorder.
- **Frame to the class** — a bug doc leads with the defect and its root cause, a chore doc with the maintenance goal, a feature doc with the capability added. Never describe a chore or a bug fix as a feature.
- **Carry the caveats.** Any use case whose verdict is not `Satisfied`, and any `out_of_scope` entry, is recorded as-is. Documentation does not launder a partial result into a clean one.
- **Write only the doc** — this command produces one markdown file and touches nothing else.
- **Emit valid JSON only** — the output is parsed with `json.loads`; return the `Report` object and nothing else.

## Phases

| Phase | Action | Gate — pass to advance | Failure |
|---|---|---|---|
| **Read** | Parse `verdict` for `use_cases[]`, `out_of_scope[]` and `review_summary`. Read `spec` for the class and root cause. | Is the verdict parseable with a non-empty `use_cases[]`, and is the class resolved? | `EXIT_NO_VERDICT` / `EXIT_NO_SPEC` |
| **Describe** | For each use case in verdict order: open the file at its `evidence` citation, read the implementing change, and write the entry — what it does and how, in 1–2 sentences. Record any non-`Satisfied` verdict inline. | Does every entry state something absent from the verdict JSON? | `EXIT_UNREADABLE_EVIDENCE` |
| **Write** | Write `doc` in the Documentation Format below. Create `app_docs/` if absent. | Does the file exist on disk at `doc`? | `EXIT_WRITE_FAILED` |

### Failure Modes

| Exit Code | Meaning | Recommended Action |
|---|---|---|
| `EXIT_NO_VERDICT` | The verdict file is missing, not valid JSON, or carries no use cases | Re-run `/review`, or check that its verdict was persisted |
| `EXIT_NO_SPEC` | The spec is missing or its class cannot be resolved | Inspect the plan step |
| `EXIT_UNREADABLE_EVIDENCE` | A citation points at a file or line that cannot be read | Report which citation failed — the verdict and the tree disagree |
| `EXIT_WRITE_FAILED` | The doc could not be written | Check `app_docs/` permissions and the resolved path |

## Documentation Format

```md
# <Title — names the change, not its class>

**Class:** <chore | bug | feature>
**ADW ID:** <adw_id>
**Date:** <YYYY-MM-DD>
**Spec:** <spec>
**Review:** <APPROVED | CHANGES_REQUESTED>

## Overview

<2–3 sentences, framed to the class: for a bug, the defect and its root cause; for a chore, the maintenance goal; for a feature, the capability added.>

## What Was Built

<One entry per use case, in verdict order.>

### <use_cases[].name, verbatim>

<1–2 sentences on what the change does and how, from reading the cited code.> — `<use_cases[].evidence>`

<If the verdict is not Satisfied:>
> **<Partial | Missing>** — <what the review found outstanding.>

## Out of Scope

<One line per out_of_scope entry. Omit the section if the array is empty.>

- <change> — `<evidence>`

## How to Use

<Steps for exercising the change. Omit if it has no user-facing surface — most chores won't.>

## Configuration

<Env vars, settings, flags introduced by the changes read above. Omit if none.>

## Testing

<How to run the tests covering these use cases, by path.>
```

## Report

Return **JSON only** — no preamble, no markdown fences. On success:

```json
{
  "success": true,
  "verdict": "DOCUMENTED",
  "doc_path": "app_docs/<class>-<adw_id>-<slug>.md",
  "use_cases_documented": 4,
  "out_of_scope_recorded": 0,
  "document_summary": "1–2 sentences: what the doc covers and the single most useful thing it records."
}
```

Field rules:

| Field | Values / Rule |
|---|---|
| `success` | `true` iff the doc exists at `doc_path` and every use case in the verdict has an entry |
| `verdict` | `DOCUMENTED` when `success` is `true`; else the exit code |
| `doc_path` | path relative to the project root |
| `use_cases_documented` | must equal the length of the verdict's `use_cases[]` |

On a gate failure, return the exit object instead (still valid JSON):

```json
{
  "success": false,
  "verdict": "EXIT_NO_VERDICT",
  "error": "<what was read, and what is missing or malformed that prevents writing the doc>"
}
```
