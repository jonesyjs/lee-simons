# adw — Agentic Developer Workflow

The agentic layer for this project: deterministic Python that wraps non-deterministic
agent calls into a gated pipeline (plan → build → review → integrate).

## Layout

- **`*.py` at root** — the main pipeline scripts. One responsibility each; the
  orchestration/control flow lives here.
- **`modules/`** — everything the pipeline imports, kept flat: runners (subprocess
  wrappers for `claude`, `gh`, `git`), run state, logging, config, helpers.

## Related folders (project root)

- **`../spec/`** — generated specs; the plan→build handoff artifact.
- **`../ai_docs/`** — documentation + solution architecture; context referenced during builds.
- **`../.claude/commands/`** — the prompts (plan meta-prompts, the build HOP, the reviewer).
  The harness reads these; it never inlines prompt text.

## Principles

- Deterministic wrapper, non-deterministic stages — control returns to code at every boundary.
- State holds metadata (run id, type, branch), not artifacts. Artifacts live in the git tree.
- Keep the engine thin; the you-specific loadout is prompts + `ai_docs` + tools.
