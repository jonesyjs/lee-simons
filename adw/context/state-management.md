# State Management — Solution Architecture

## Overview

State management for the ADW pipeline holds the metadata for a workflow run — not the artifacts the steps produce. Artifacts (spec, code changes, review report, documentation) live in the codebase within the run's git branch. State management tracks only what's needed to identify a run: the run's IDs, its type, and its branch. It does **not** track pipeline position — the step a run is on is implicit in the orchestration script running it, not something state records.

The pipeline runs per-branch in a GitHub work tree. Each run owns one state file, and everything else the pipeline needs — artifact names and locations — is computed deterministically from that state.

## Design Principles

Governing "why".

- **State holds metadata, not artifacts.** The spec, code diff, review report, and docs are artifacts in the codebase. State only tracks identifiers, never the raw inputs/outputs of steps.
- **State is a typed data contract, not ad-hoc dicts.** The run state is a defined object with typed fields.
- **Prefer computed values over stored values.** Where a value can be deterministically derived (artifact locations from IDs + branch + step name), compute it rather than persisting it. This keeps state lean and eliminates redundancy.
- **State is write-once.** Every field is set during run start-up and frozen thereafter. The run's position in the pipeline is not held in state, so there is no field that changes step to step. If a genuinely mutable field ever emerges, revisit the mutable/immutable split then — don't pre-split.
- **Keep it lean; don't defensively code against system-guaranteed invariants.** The pipeline's design guarantees unique runs per branch. State code should assume those guarantees rather than re-checking them everywhere.
## Guardrails

Hard never/always invariants.

- All RunState fields (adw_id, issue_id, plan_type, branch_name) are immutable once set at run start. branch_name is the last to be set (after branch generation), then frozen; nothing mutates thereafter.
- The DAL exposes Create, Read, Update only — never Delete. Cleanup happens via branch deletion, not a delete operation. (Update exists only to set branch_name once after generation.)
- Operation responsibilities never overlap: Read never creates, Create never checks-then-branches, Update only ever touches an existing file. Each function has one job.
## Policies

If-then runtime behaviour.

- On branch generation → write branch_name into the run's JSON file (write-once, then frozen).
- On write failure → retry N times with exponential backoff; if retries are exhausted, fail the run.
- On read of a missing file → return an error state. Never auto-create on read.
- On malformed JSON → return an "invalid state" error (parse only; no deeper schema validation).
- On Update → write atomically (write to temp file, then rename) to avoid corruption mid-write.
- On fatal run failure → no resume, no rollback. Delete the branch and start a new run with a fresh adw_id and branch. The orphaned state file is cleaned up by that branch deletion.
## Architecture

State lives as one JSON file per run, stored in the run's branch work tree at adw-{adw_id}/run-state.json. There is no database and no snapshot history — the file is written at run start, branch_name is set once after branch generation, and then the file is immutable for the rest of the run.

Two components:

- **RunState** — the typed object holding the run's metadata (fields below).
- **Data Access Layer (DAL)** — a thin CRU interface over the JSON file, owning existence checks, retries, and atomic writes.
DAL function design:

| Function | Input | Behaviour | Failure handling | | --- | --- | --- | --- | | Create | RunState object | Writes RunState as JSON to the run's path. Overwrites silently if a file exists (no existence check — uniqueness is guaranteed upstream). | Retry N times with exponential backoff on write failure; fail the run if exhausted. (Appendix A.1) | | Read | adw_id | Loads and parses the JSON into a RunState object. | Missing file → not-found error. Unparseable JSON → invalid-state error. Retry N times with backoff on I/O failure. (Appendix A.1) | | Update | adw_id, branch_name | Reads the file, sets branch_name once after generation, writes back. File must already exist. | Missing file → not-found error. Atomic write (temp → rename). Retry N times with backoff on write failure. (Appendix A.1) |

## Modelling

A single RunState object. All fields are set during run start-up; branch_name is the last to be set (after generation), and nothing changes after that.

| Field | Mutability | Source | Notes | | --- | --- | --- | --- | | adw_id | Immutable | Set at run start | Unique run identifier. | | issue_id | Immutable | Set at run start | The git issue the run stems from. | | plan_type | Immutable | Set at run start | Classifies the run (e.g. feature, patch). Determines which workflow steps execute. | | branch_name | Immutable (after generation) | Generated early via AI → GitHub | Generated once by the branch-generation step, then frozen. Used with the IDs to compute unique artifact names. |

Computed values (not stored): all artifact locations — spec, review report, documentation — are derived from adw_id + issue_id + plan_type + branch_name + the step name supplied by the pipeline. Because each run's branch is unique, these names are always unique. The step name comes from the orchestration script (which knows its own position), not from state. If a new location is needed, program a new naming pattern rather than adding a stored field.

## Assumptions

- Every new ADW run receives a unique adw_id and branch name, guaranteed upstream. State code therefore does not defend against ID collisions; a collision indicates a failure elsewhere in the system.
- Because runs are unique per branch, a write can never conflict with an existing unrelated run's state.
- The filesystem is reliable enough that temp-file-then-rename atomic writes succeed.
- Orphaned branches and their state files from failed runs are cleaned up automatically when the branch is deleted and never merged to main. No separate cleanup process is required.
- JSON serialization / deserialization is deterministic.
- The pipeline knows its own step position, so state does not need to track it. Resume-from-step is not a design goal.
## Open Decisions

- **Escalation fields.** Whether RunState needs to carry escalation-related data (e.g. a needs_escalation flag) is deferred to the Workflow SA doc. The Workflow now escalates on review success = false; if that needs to persist in state rather than stay runtime, add the field then.
- **Whether Update is still needed.** With current_step removed, the only post-Create write is branch_name. If branch_name is instead set at Create time, the DAL collapses to Create + Read. Deferred until the run start-up sequence is finalised.

## Definition

### Appendix A.1 — Exponential Backoff Definition

| Parameter | Value | Notes | | --- | --- | --- | | Initial delay | 100 ms | Delay before the first retry | | Multiplier | 2× | Each delay doubles: 100 → 200 → 400 → 800 → 1600 ms | | Max retries | 5 | Attempts before giving up | | Max delay cap | 2000 ms | Delays never exceed this, even as the multiplier compounds | | Jitter | ±20% | Randomised per attempt; prevents synchronised retry storms across sinks | | Total max elapsed | ~5 s | Ceiling on total retry time before exhaustion | | On exhaustion | apply overflow strategy | Hand off to the sink's drop_newest (default) or spill_to_disk |

## Glossary

| Term | Definition | | --- | --- | | RunState | The typed object holding a run's metadata: adw_id, issue_id, plan_type, and branch_name. The single state contract for a pipeline run. | | Data Access Layer (DAL) | The thin interface over the run's JSON state file. Exposes Create, Read, Update; owns existence checks, retries, and atomic writes. | | adw_id | Unique identifier for a pipeline run. Immutable, set at run start. Guaranteed unique upstream. | | issue_id | The git issue a run stems from. Immutable, set at run start. | | plan_type | Classifies a run (e.g. feature, patch) and determines which workflow steps execute. Immutable, set at run start. | | branch_name | The git branch for the run, generated once via AI to GitHub, then frozen. Combined with the IDs to compute unique artifact names. | | Computed value | An artifact location derived on demand from the IDs, branch, and a pipeline-supplied step name rather than stored in state. Always unique because the branch is unique. | | Artifact | A step's output (spec, code changes, review report, documentation). Lives in the codebase/branch, never in state. | | Work tree | The per-branch GitHub checkout a run operates in. Holds the run's state file and artifacts; deleted on fatal failure. |
