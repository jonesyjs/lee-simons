# Workflow

## Overview

The Workflow is the top-level orchestrator of the ADW pipeline.

It is the layer that drives a run end-to-end and composes the three subsystems beneath it — Logging, Client Layer, and State Management — into a single sequenced process.

It owns sequencing and control flow: which step runs, in what order, and what happens between steps.

It explicitly does **not** do the work of the steps themselves, and it explicitly does **not** log.

The orchestration script conducts; the steps and operations one level down do the work and narrate themselves.

Keeping the top level clean of both business logic and logging is a deliberate response to the previous pipeline, where logging bled into the orchestration script and plan/build responsibilities overlapped heavily.

## Design Principles

- **The Workflow is an orchestrator, not a worker.** It sequences steps and fires the operations that run around them. All observable work happens one level down, in the steps and operations.
- **The issue is the work order.** A GitHub issue carries two things: the problem statement (what to solve) and a routing token declaring which workflow slice to run. Problem plus routing — enough for the run to route itself.
- **Plan understands broadly so build can act narrowly.** The plan step does the wide-context discovery once and scopes the work into the spec. Build runs on rails against that spec. This kills the plan/build context overlap that bloated the old pipeline.
- **No logging at the orchestration layer.** Every step and every operation owns its own logging. The orchestration script stays clean; the units that do the work narrate themselves.
- **A step's failure is a debugging concern, not an audit one.** When a step itself fails, its exception goes to operational logs and the run stops. Full failure handling (halt vs escalate vs branch teardown) is deliberately not designed for the first pass — see Open Decisions.
- **Core 4 payload discipline.** Every agent invocation is composed of the four payload aspects — prompt, model, context/memory, tools. Each piece lives where its aspect belongs: prompts as slash commands, context as docs the agent reads. Placement is principled, not arbitrary.
- **Modular orchestration slices.** The pipeline is composable. Plan+build+review is a runnable slice, individual steps run in isolation, or the whole pipeline end-to-end. The issue's routing token selects the slice.
- **Human-in-the-loop at the high-stakes points.** Review failure escalates to a person; the learnings→plan feedback loop is human-gated. Automation stops where a bad inference would compound.
## Guardrails

Hard build-time never/always constraints.

- No logging code ever lives at the orchestration layer. Steps and operations log; the orchestrator does not.
- Logging failures are always swallowed, never propagated — external client failures (e.g. a failed comment post) included. Logging never blocks or crashes the step it observes.
- The pipeline's own issue comments never re-trigger a run. The trigger ignores any body carrying the bot identifier (loop guard) — necessary because audit and review both write comments, and comment-created events are a trigger.
- Dependent slices (build, test, review, document, ship in isolation) are never cold-started from a webhook. They require an existing worktree/ADW ID; attempting a fresh start posts an error comment instead.
- A step's own failure goes to operational logs, never the audit/GitHub stream. GitHub sees outcomes, not exceptions.
- create-branch is always the first pipeline action. Everything after it — spec, code, reports, docs — lives natively in that branch's work tree.
- No delete-branch operation exists. A run never tears down its own branch mid-pipeline; branch cleanup happens outside the pipeline, after the fact.
- Build reads only the spec. It never re-primes or re-reads the codebase. If build needs context the spec doesn't carry, the plan was incomplete — that is not licence for build to wander.
## Policies

If-then runtime behaviour.

- On a valid trigger → mint/load the ADW ID, persist run state, post an acknowledgment comment, launch the workflow as a detached background subprocess, and return HTTP 200 immediately. Never block the webhook response on the run.
- On operational log → default sink is the local logging file.
- On audit log → default sink is GitHub comments, posted via the shared GitHub client.
- On sink or comment-post failure → catch at whatever layer failed, log it operationally, bury it, and continue. Never propagate.
- On step failure → log operationally (local file) and stop the run. Full failure handling is deferred.
- On review `success = true` → proceed to document.
- On review `success = false` → escalate to human-in-the-loop.
- On document step → if the run created new files, update the conditional routing table to reflect them.
## Architecture

A run is a self-contained work order executed through a sequence of steps, with supporting operations running around and inside them.

**Trigger and entry.** The canonical trigger is a webhook server — a FastAPI app exposing a single endpoint, `POST /gh-webhook` (port from `PORT`, default 8001), that GitHub calls on issue events. The handler is the connection between a GitHub issue and the pipeline:

- It reads the event type (`X-GitHub-Event` header) and the action. Two combinations trigger a run: `issues`/`opened` (inspects the issue body) and `issue_comment`/`created` (inspects the comment body).
- **Loop guard** — if the body carries the bot identifier, it is ignored, so the pipeline's own write-back comments never re-trigger it.
- **Routing token** — the body must contain `adw_` (case-insensitive); the handler parses which workflow to run (e.g. `adw_plan_build_review_iso`), plus an optional ADW ID and model set. This is the work order's routing, realised.
- **Dependent-workflow guard** — slices needing an existing worktree/ADW ID (build, test, review, document, ship in isolation) cannot be cold-started from a webhook; attempting it posts an error comment.
On a valid trigger the handler mints or loads an ADW ID, persists run state (issue number, model set), posts an acknowledgment comment back to the issue, then launches the workflow as a **detached background subprocess** (`uv run adws/<workflow>.py <issue> <adw_id>`) and returns immediately. It deliberately responds fast and always returns HTTP 200 — even on error — to beat GitHub's ~10-second webhook timeout and stop GitHub retrying.

The subprocess is the same script that runs by hand from the terminal; the webhook is just an automated caller. The write-back channel to the issue is the shared GitHub client (`adw_modules/github.py`, e.g. `make_issue_comment()`, `fetch_issue()`), the same module the audit sink and the review step use. A tunnel script exposes the local server to GitHub; alternative triggers exist in the same family (a cron poller, an AEA server variant), but the webhook is canonical. The canonical trigger lives at `adws/adw_triggers/trigger_webhook.py`.

**Orchestration layers.** Two layers sit above the work:

- The **pipeline script** — the stepwise driver. It sequences the steps and drives the transitions between them. It carries no business logic and no logging.
- The **steps** — the individual units of work: Plan, Build, Review, Document. Each owns its own work and its own logging.
Because orchestration is built as modular slices, a script can run the full pipeline or any composable subset. The `_iso` workflow slices exposed in the codebase (e.g. test, ship) are exactly these composite combinations of the four core steps — not additional steps.

**Operations vs utils.** Around and inside the steps sit **operations** — composed, meaningful units of work (e.g. create-branch, classify-issue). Operations are a shared library, called from wherever they logically belong: the orchestration boundary (create-branch) or inside a step (classify-issue). They are distinct from **utils**, which are low-level recurring helpers operations may draw on. An operation owns its own logging, so the caller stays clean.

**create-branch.** The first action of every pipeline. A composite operation: it generates a branch name (a client-layer call to a model, e.g. Sonnet) and then cuts the branch (a call out to the GitHub CLI). The pipeline sees one unit, `create-branch`; the two client calls are hidden inside it. The name-generation is a thick, value-making operation and therefore sits in the operation, above the client — the client only performs the raw RPC.

**Step 1 — Plan.** Produces the spec. In sequence:

1. **classify-issue** (operation) — reads the problem statement and names the problem class. That class does double duty: it selects the meta-prompt and it routes priming.
2. **prime** (slash command) — the priming prompt pushed into the agent's context window before the plan prompt. A thin instruction wrapper that reads a conditional routing table to load a scoped slice of context, not the whole codebase. It routes across the three context layers by classification.
3. **plan generation** — the problem-class meta-prompt runs against the issue and the primed context, producing the spec into the spec folder.
The plan agent takes broad context so it can canvass the codebase and scope the work; the spec it emits carries that scoping forward.

**The three context layers.** Any codebase presents three: the **README** (introduces the other two), the **solution architecture docs** (design-level truth), and the **codebase itself** (implementation truth). Prime routes across all three, conditionally, by classification.

**Step 2 — Build.** Build is just build plus logging. It reads the lean spec — which already names the files, the places to look, and the acceptance criteria — and implements it. No priming, no codebase discovery; the spec is its entire world. This is the deliberate separation that removes the old plan/build overlap.

**Step 3 — Review.** Takes two inputs: the git diff (what was built) and the spec (the criteria), and scores the build against the spec's use cases. It returns a minimal **review result** — a `success` boolean plus a bullet-point summary — and posts that summary to the issue as a GitHub comment via the shared GitHub client. It is not a stored branch artefact. Two outcomes:

- `success = true` → proceed to document.
- `success = false` → escalate to human-in-the-loop.
The first pass has no middle "patch" path and no per-issue breakdown array; both are deferred (see Open Decisions).

**Step 4 — Document.** Reads the git diff and the review summary — not the plan or spec, whose context has already flowed forward into what was built and reviewed. It produces two separate documents: **what was built** (context for the next agent working in this area) and **what was learned** (process knowledge distilled from the review). It also updates the conditional routing table if the run created new files, keeping the priming knowledge current.

The learnings document is the input to a plan-improvement feedback loop, but that loop is deliberately not automated — see Open Decisions.

**The conditional routing table lifecycle.** Read early, written late: classify/prime consult it in step 1 to route priming; document updates it in step 4 to reflect new files. It is context/memory, not a prompt — it lives with the solution architecture docs in the AI docs folder, and the thin prime prompt reads it.

**Logging composition.** The Workflow uses the Logging subsystem throughout, on two architectural streams:

- **Operational logging** — severity-based (ERROR/WARN/INFO/DEBUG), emitted inside steps and operations (e.g. from try/catch blocks, and any step's own failure). Default sink: the local logging file.
- **Audit logging** — process-oriented outcomes and milestones. Default sink: GitHub comments (via the shared GitHub client), giving the run a readable, chronological trail on its originating issue.
Audit logging is lifted out of the step bodies via a **decorator**. The decorator wraps a step or operation; it cannot see the function's internal scope, only what crosses the boundary — arguments in, return value or exception out. So each step and operation returns a structured result — a `description` string plus a `payload` — and the decorator reads that on the way out to emit the audit event (e.g. a `create-branch` returning the name and ID becomes a "branch created" audit comment). This keeps audit uniform and declarative with no audit code in the step body.

The GitHub audit sink wraps the shared GitHub client: when an audit event lands, the sink posts the comment. Because that is a network operation that can fail, the sink swallows its own failures — logging them operationally and burying them — so the pipeline never stalls on a logging concern. Review's summary is **not** an audit event: the review step posts it directly through the same shared GitHub client, bypassing the audit decorator. That direct post still follows the best-effort rule — a failed post is logged operationally and never fails the step. This traces back to the root Logging principle: logging is passive observation and must never compromise the stage it observes.

## Modelling

**Step / operation result (locked).** Every step and operation returns a structured result mirroring the LogEvent envelope one-to-one:

| Field | Type | Notes | | --- | --- | --- | | description | string | Human-readable summary of the outcome (e.g. "branch created"). Read by the audit decorator as the event description. | | payload | object | Flexible, type-specific data (e.g. branch name + ID). Read by the audit decorator as the event payload. |

**Review result (locked).** Review returns a minimal result, posted to the issue via the shared GitHub client rather than stored as an artefact:

| Field | Type | Notes | | --- | --- | --- | | success | boolean | Pass/fail verdict; drives the two-way branch (proceed vs escalate). | | summary | bullet list | 2–4 point human-readable review, posted to the issue as a comment. |

## Assumptions

- The Logging, Client Layer, and State Management subsystems exist and behave per their own SA docs; the Workflow composes them rather than re-implementing their guarantees.
- Every run receives a unique branch (guaranteed upstream, per the State doc), so create-branch as the first action and everything living in the branch work tree is safe.
- Any codebase presents the three context layers — an agent-friendly README, solution architecture docs, and the codebase itself.
- Classification is reliable enough to drive its downstream uses: meta-prompt selection and prime routing.
- Every workflow script is a plain module runnable from the terminal, so the webhook trigger is just an automated caller of a manually-runnable thing.
- The document step is responsible for keeping context artifacts (the conditional routing table) current.
## Open Decisions

- **Patch loop (deferred enhancement).** When review needs a middle path between clean pass and escalation, reintroduce a bounded patch loop: review emits a discrete patch list, and the pipeline reruns the plan+build slice once per patch (classified as a patch problem class) as an in-run course correction on the same branch — never a new pipeline call or issue. The patch list bounds the loop. Deliberately not built for the first pass to avoid over-optimizing before real runs show whether the middle zone is common.
- **Step-failure handling.** Only the principle is set for now (a step's failure logs operationally and stops the run). Halt-vs-escalate-vs-branch-teardown is deferred; State's fatal-failure path (no resume, no rollback, delete the branch, start fresh) is the likely basis.
- **Model set.** The trigger parses an optional model set and persists it to state, but per-step model selection is undefined — which model each step uses, and whether cheaper models run review-type passes while build is routed by complexity (per the LLM Judge notes). Needs a principle at minimum.
- **Problem class vs plan_type.** classify-issue returns a problem class (drives meta-prompt selection and prime routing). State Management carries `plan_type` (e.g. feature, patch). Decide whether these are the same field or two related ones, and pin the closed enum of known classes.
- **Learnings → plan feedback loop.** The learnings document is intended to improve the plan steps, but closing that loop automatically risks cascading failure modes (the system reinforcing its own mistaken conclusions). The loop is therefore human-gated: learnings are reviewed by a person, who then updates the plan steps. The automated pipeline stops at "produce the learnings document." Out of automated scope for now.
## Glossary

| Term | Definition | | --- | --- | | Work order | A GitHub issue that triggers a run, carrying both the problem statement and a routing token declaring the workflow to run. | | Webhook trigger | The canonical entry point: a FastAPI `POST /gh-webhook` handler (`adws/adw_triggers/trigger_webhook.py`) that receives issue events and launches the routed workflow as a detached subprocess, returning HTTP 200 immediately. | | Routing token | The `adw_`-prefixed marker in an issue/comment body naming which workflow slice to run (e.g. `adw_plan_build_review_iso`). | | Loop guard | The rule that bot-authored comments (carrying the bot identifier) never re-trigger a run. | | Shared GitHub client | `adw_modules/github.py` — the read/write channel to issues (`make_issue_comment`, `fetch_issue`); used by the trigger, the audit sink, and the review step. | | Pipeline script | The top-level stepwise driver that sequences the steps and drives transitions. Carries no logging or business logic. | | Step | An individual unit of pipeline work — Plan, Build, Review, or Document. Owns its own work and logging. | | Orchestration slice | A composable subset of the pipeline runnable as its own script. The `_iso` slices (e.g. test, ship) are composite combinations of the four core steps, not extra steps. | | Operation | A composed, meaningful unit of work (e.g. create-branch, classify-issue) in a shared library, called from the orchestration boundary or from inside a step. Owns its own logging. | | Util | A low-level recurring helper function. Distinct from an operation; operations may draw on utils. | | create-branch | The first pipeline action; a composite operation that generates a branch name (client call) then cuts the branch (GitHub CLI). | | classify-issue | The operation that names a problem class from the issue's problem statement. Drives meta-prompt selection and prime routing. | | prime | A slash-command priming prompt run before the plan prompt in the same context window. A thin instruction wrapper that reads the conditional routing table to load a scoped context slice. | | Conditional routing table | Agent-facing context (in the AI docs folder) that routes priming to the relevant slice of the three context layers, keyed by classification. Read in step 1, updated in step 4. | | Three context layers | The README (introduction), the solution architecture docs (design truth), and the codebase (implementation truth). | | Problem class | The classification of an issue, determining meta-prompt selection and prime routing. | | Review result | Review's return: a `success` boolean plus a bullet-point summary, posted to the issue via the shared GitHub client. Not a stored artefact. | | Patch loop | Deferred enhancement: an in-run course correction that reruns the plan+build slice once per patch in a review-generated patch list. See Open Decisions. | | Operational logging | Severity-based in-the-moment debugging (ERROR/WARN/INFO/DEBUG), emitted inside steps/operations. Default sink: local file. | | Audit logging | Process-oriented record of outcomes and milestones, lifted out via decorator. Default sink: GitHub comments via the shared client. | | Audit decorator | A decorator wrapping a step/operation that reads its structured return (description + payload) on the way out and emits the audit event. Sees only the boundary, never internal scope. | | Step result | The structured return of every step/operation — description + payload — mirroring the LogEvent envelope; the channel the audit decorator reads. |

## Appendix — KPIs & Plan Refinement Harness

*Merged from the earlier draft Workflow notes.*

### Agentic coding KPIs

- Size of work at handoff → increase
- Attempts to success → decrease
- Streak of success → increase
- Presence → drive to zero
### Plan Refinement Harness

A factory to stress-test and reform the library itself.

- Plan run against a rubric — low-fidelity validation
- Synthetic personas — generate use cases
- Real artifact — high-fidelity validation
### Execution notes

- One-shot: a new context window per step in the workflow.
- Document step should capture: (1) what was built, (2) a review of the plan outcomes.
