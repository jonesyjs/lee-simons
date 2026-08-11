# ai_docs — Documentation & Solution Architecture

Context the agent loads during builds: solution architecture, design decisions,
conventions, and any hard-won knowledge worth teaching every future agent boot.

## Subfolders

- **`work/`** — reports of work completed by the ADW (what a run built and why).
- **`learnings/`** — learnings from the review stage; the self-improvement loop that feeds
  back into the ADW to improve its own processes.
- **`solution_architecture/`** — the core architecture referenced during artifact builds.

## Principles

- One topic per file. Read frontmatter/summary first, load the full body only when relevant
  (progressive disclosure).
- This is payload, not mechanism — knowledge referenced by prompts and stages, never control flow.
- Failures become docs: when a bug slips a gate, write the lesson back into `learnings/`.
