---
name: review
description: Review a build's diff against the use cases in its spec — verify each use case (first→last) is satisfied and flag out-of-scope drift. Use after a build step to gate whether the changes match what was planned. Emits a JSON verdict; it does not edit code.
argument-hint: <spec-path>
---

# Review

Review a build's diff against the use cases in its spec. You are a **reviewer, not an author** — you assess whether the implementation satisfies each use case and whether it stayed in scope. You judge against the spec's use cases only; you never edit code.

## Variables

- `spec` — `$1`, path to the plan spec whose use cases are the review requirements.
- `diff` — the changes under review: the build commit's diff, obtained with `git diff HEAD~1 HEAD -- . ':(exclude)adw/data'`. The build lands as a single commit atop the branch point, so `HEAD~1` is the base; `adw/data` holds pipeline bookkeeping (spec, state, logs), not reviewable work, so it is excluded.

## Instructions

- **Judge against the use cases only** — the spec's use cases are the requirements; don't invent new ones or drop any.
- **Cite evidence** — every verdict names the `file:line` in the diff that supports it; no unsupported verdicts.
- **Walk in spec order** — process use cases first → last (simplest → complex); never reorder.
- **Separate the two findings** — a *Missing* use case (required, unimplemented) is distinct from an *Out-of-scope* change (diff content no use case requires).
- **Scope to the diff** — assess what changed, not the whole codebase.
- **Review only, never edit** — this command emits a verdict, not a fix.
- **Emit valid JSON only** — the output is parsed with `json.loads`; return the `Report` object and nothing else.

## Phases

| Phase | Action | Gate — pass to advance | Failure |
|---|---|---|---|
| **Extract** | Read `spec`; extract its use cases verbatim as an ordered requirements list, first → last. | Is every use case captured as a discrete, checkable requirement? | `EXIT_NO_USE_CASES` |
| **Review** | For each use case in order, verify it against `diff`: find the change that implements it, assign a verdict (`Satisfied` / `Partial` / `Missing`) with `file:line` evidence, and record which diff hunks it consumes. Loop until every use case is judged. | Is there a non-empty diff, and does every use case carry an evidenced verdict? | `EXIT_EMPTY_DIFF` |
| **Scope** | Reconcile both directions: a use case with no implementing change → `Missing` (gap); a diff hunk consumed by no use case → out-of-scope (drift). | Is every diff hunk either traced to a use case or flagged out-of-scope? | — |

### Failure Modes

| Exit Code | Meaning | Recommended Action |
|---|---|---|
| `EXIT_NO_USE_CASES` | The spec contains no extractable use cases to review against | Return to planning — there is nothing to review |
| `EXIT_EMPTY_DIFF` | There are no changes to review | The build produced no diff; re-run or fail the build step |

## Report

Return **JSON only** — no preamble, no markdown fences. On success:

```json
{
  "success": true,
  "verdict": "APPROVED",
  "use_cases": [
    { "name": "<use case, verbatim from spec>", "verdict": "Satisfied", "evidence": "path/to/file.py:42" }
  ],
  "out_of_scope": [
    { "change": "<what changed that no use case requires>", "evidence": "path/to/file.py:99" }
  ],
  "review_summary": "1–3 sentences: what holds, what doesn't, the single most important thing to fix."
}
```

Field rules:

| Field | Values / Rule |
|---|---|
| `success` | `true` iff every use case is `Satisfied` and `out_of_scope` is empty; otherwise `false` |
| `verdict` | `APPROVED` when `success` is `true`; else `CHANGES_REQUESTED` |
| `use_cases[].verdict` | one of `Satisfied` / `Partial` / `Missing` |
| `use_cases[].evidence` | `file:line` from the diff, or `""` when `Missing` |
| `out_of_scope` | `[]` when there is no drift |

On a gate failure, return the exit object instead (still valid JSON):

```json
{
  "success": false,
  "verdict": "EXIT_NO_USE_CASES",
  "error": "<what was reviewed, and what is missing or malformed that prevents a verdict>"
}
```
