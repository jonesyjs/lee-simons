# spec — Specifications

Generated specs: the deterministic artifact that carries intent from planning into code.
The plan stage writes a spec here; the build stage (`/implement`) consumes it.

- One spec per task. Vague spec in, vague code out.
- The spec is the unit of review — review the spec, not just the diff.
- Universal skeleton: Title → Context/Why → Goal → Constraints → Inputs → Steps →
  Output contract → Verification → Out-of-scope.
