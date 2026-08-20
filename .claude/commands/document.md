---
name: document
description: Write the run's change doc — what was built (diff traced to the spec's use cases) and what was learnt (grounded in the review verdict and spec-vs-diff deltas). Works for any issue class (chore, bug, feature). Use as the final pipeline step after an approved review. Writes one markdown file and emits a JSON verdict; it does not edit code.
argument-hint: <spec-path> <adw-id> <verdict-path>
---

# Document

Write the run's change documentation. The run may have been a chore, a bug fix, or a feature — the spec's class determines the framing, not this command's defaults. You are a **recorder, not an author** — you describe what the diff actually contains and what the run actually surfaced. You never infer intent that isn't in the spec, and you never write a learning you cannot point at.

## Variables

- `spec` — `$1`, path to the plan spec, written from a `/templates:{class}` template. Its use cases are the frame for *What Was Built*.
- `class` — the issue class, read from the spec: `chore`, `bug`, or `feature`. Sets the doc's title verb and the *Overview* framing.
- `adw_id` — `$2`, the run id; names the output file and stamps the doc.
- `verdict` — `$3`, path to the JSON verdict emitted by `/review`. Its `use_cases[]`, `out_of_scope[]` and `review_summary` are the evidence base for *What We Learnt*.
- `diff` — the run's shipped work, obtained with `git diff origin/main -- . ':(exclude)adw/data'`. `adw/data` holds pipeline bookkeeping, not shipped work, so it is excluded.
- `doc` — the output path, `app_docs/{class}-{adw_id}-{slug}.md`, where `slug` is a 2–3 word kebab-case name taken from the spec title.

## Instructions

- **Trace, don't summarise** — every claim in *What Was Built* names the `file:line` in the diff that supports it.
- **Ground every learning** — a learning cites a concrete artefact: a `use_cases[].verdict` that wasn't `Satisfied`, an `out_of_scope` entry, or a diff hunk that contradicts the spec's stated root cause or file list. No artefact, no learning.
- **Omit over invent** — if a learning category has no evidence, drop the heading. An empty *What We Learnt* is a valid outcome; a plausible-sounding one is a defect.
- **Learnings are about the run, not the change** — "the spec's root cause was one layer too shallow" is a learning; "it handles empty input" is a built detail.
- **Frame to the class** — a bug doc leads with the defect and its root cause, a chore doc with the maintenance goal, a feature doc with the capability added. Never describe a chore or a bug fix as a feature.
- **Walk in spec order** — process use cases first → last; never reorder.
- **Write only the doc** — this command produces one markdown file and touches nothing else.
- **Emit valid JSON only** — the output is parsed with `json.loads`; return the `Report` object and nothing else.

## Phases

| Phase | Action | Gate — pass to advance | Failure |
|---|---|---|---|
| **Read** | Read `spec` (class, use cases, root cause, fix direction, files) and `verdict` (per-use-case verdicts, out-of-scope entries, review summary). Obtain `diff`. | Is the class resolved, are the spec's use cases extractable, the verdict parseable, and the diff non-empty? | `EXIT_NO_SPEC` / `EXIT_NO_VERDICT` / `EXIT_EMPTY_DIFF` |
| **Trace** | For each use case in spec order, find the change in `diff` that implements it and record it with `file:line`. Then sweep the remaining hunks: group unclaimed changes into supporting work (config, tests, deps). | Is every diff hunk either traced to a use case or grouped as supporting work? | — |
| **Learn** | Derive learnings from the evidence base only, across four categories: spec accuracy (root cause / file list vs what the diff touched), scope (`out_of_scope` entries), review corrections (any `Partial` / `Missing` verdict and how it resolved), and residual risk (anything the review summary flags as unresolved). Drop any category with no artefact behind it. | Does every learning cite a specific artefact? | — |
| **Write** | Write `doc` in the Documentation Format below. Create `app_docs/` if absent. | Does the file exist on disk at `doc`? | `EXIT_WRITE_FAILED` |

### Failure Modes

| Exit Code | Meaning | Recommended Action |
|---|---|---|
| `EXIT_NO_SPEC` | The spec is missing or has no extractable use cases | Nothing to document against — inspect the plan step |
| `EXIT_NO_VERDICT` | The verdict file is missing or not valid JSON | Re-run `/review`, or check that its verdict was persisted |
| `EXIT_EMPTY_DIFF` | There is no shipped work to describe | The build produced no diff; fail the run rather than writing an empty doc |
| `EXIT_WRITE_FAILED` | The doc could not be written | Check `app_docs/` permissions and the resolved path |

## Documentation Format

```md
# <Title — names the change, not its class>

**Class:** <chore | bug | feature>
**ADW ID:** <adw_id>
**Date:** <YYYY-MM-DD>
**Spec:** <spec>
**Review:** <verdict of the run — APPROVED / CHANGES_REQUESTED>

## Overview

<2–3 sentences, framed to the class: for a bug, the defect and its root cause; for a chore, the maintenance goal; for a feature, the capability added.>

## What Was Built

<One entry per use case, in spec order.>

### <Use case, verbatim from spec>

<1–2 sentences on how it was implemented.> — `path/to/file.ts:42`

### Supporting Changes

<Unclaimed hunks grouped by kind: config, tests, dependencies.>

- `path/to/file.ts:12` — <what changed>

## What We Learnt

<Only categories with evidence. Drop the rest. Drop the whole section if none.>

### Spec Accuracy

<Where the spec held or didn't — root cause depth, file list completeness.> — evidence: <artefact>

### Scope

<Drift the review flagged and why it happened.> — evidence: <artefact>

### Review Corrections

<Use cases that came back Partial or Missing, and what closed them.> — evidence: <artefact>

### Residual Risk

<What the review summary left open.> — evidence: <artefact>

## How to Use

<Steps for exercising the change. Omit if it has no user-facing surface — most chores won't.>

## Configuration

<Env vars, settings, flags introduced by the diff. Omit if none.>

## Testing

<How to run the tests the diff added, by path.>
```

## Report

Return **JSON only** — no preamble, no markdown fences. On success:

```json
{
  "success": true,
  "verdict": "DOCUMENTED",
  "doc_path": "app_docs/<class>-<adw_id>-<slug>.md",
  "use_cases_traced": 4,
  "supporting_changes": 3,
  "learnings": 2,
  "document_summary": "1–2 sentences: what the doc covers and the single most useful thing it records."
}
```

Field rules:

| Field | Values / Rule |
|---|---|
| `success` | `true` iff the doc exists at `doc_path` and every use case was traced |
| `verdict` | `DOCUMENTED` when `success` is `true`; else the exit code |
| `doc_path` | path relative to the project root |
| `learnings` | count of evidenced learnings written; `0` is valid |

On a gate failure, return the exit object instead (still valid JSON):

```json
{
  "success": false,
  "verdict": "EXIT_EMPTY_DIFF",
  "error": "<what was read, and what is missing or malformed that prevents writing the doc>"
}
```
