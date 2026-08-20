# Logger System

**Overview:**
The ADW logger is a central event logger: every stage emits structured events into a single stream, which fans out to many independent, self-filtering sinks.

**Design Principles:**

- [ ] The logger records; the orchestrator decides — logging is passive observation, never intervention
- [ ] Producers are decoupled from sinks — they emit events without knowing or depending on where they land
- [ ] Logging is best-effort — it must never compromise the stage it observes
- [ ] On schema change (event envelope)
  - [ ] additive by default
  - [ ] if the change is breaking → introduce a version discriminator
  - [ ] if it's a true restructuring → apply upcasting
**Guardrails:**

- [ ] The logger records events only; it never decides control flow.
- [ ] All control-flow decisions — retry, abort, continue — belong to the orchestrator.
- [ ] Producers never reference a specific sink.
- [ ] Durability & backpressure
  - [ ] Logging never blocks a stage.
  - [ ] Logging never crashes a stage
  - [ ] logging failures are swallowed, not propagated.
**Policies:**

- **Bounded Queue (backpressure strategy)** — when an event arrives and the queue is full:
  - [ ] **Retry** with exponential backoff *(see Appendix A.1: Exponential Backoff Definition)*
  - [ ] **On exhaustion** (retries or max-elapsed hit) → apply the queue overflow strategy:
    - [ ] `drop_newest` → discard the incoming event and emit a warning *(default)*
    - [ ] `spill_to_disk` → write the event to the local durable stream
**Architecture:**

A three-part pipeline: Logger → Appender → Layout.

- **Logger (entry point) — **exports log(); builds a LogEvent and emits it into the stream.
  - This is the thread boundary - enqueues to stream
  - A background consumer thread reads from the stream and drives everything downstream (filter → layout → sink).
- **Stream —** a single ordered queue holding every emitted event.
- **Appender (handler) —** consumes from the stream, applies its own filter, invokes a layout, writes to a sink. Filtering is decentralised; each appender owns its criteria.
  - Async (bounded queue, never stalls)
  - Routing (per-event key → sink)
  - Failover (primary then secondaries).
- **Layout (formatter) — **transforms the event into the sink's output format.
- **Sink — **the destination (console, file, UI stream).
**Two logging types (architectural distinction, not severity):**

- Audit logging: durable record of what happened and when. Outcomes. Coarse granularity.
- Operational logging: debugging in the moment. Severity-based (ERROR/WARN/INFO/DEBUG).
**Modelling:**

Two event models via inheritance. A shared base carries identity and correlation fields; operational and audit each extend it. A sink is only a destination, not a type — either model can route to any sink.

**Base LogEvent (shared):**

schema_version — envelope schema version

log_id — unique ID for this event (UUID)

adw_id — the run this event belongs to (correlation key)

issue_id — the git issue the run stems from (correlation key)

ts — ISO 8601 UTC timestamp; one clock across all events

description — human-readable summary of the event

payload — flexible, type-specific data

**OperationalLogEvent (extends Base) — in-the-moment debugging:**

level — ERROR | WARN | INFO | DEBUG

stage — plan | build | review | document

type — operational type enum

**AuditLogEvent (extends Base) — durable record of pipeline outcomes:**

stage — plan | build | review | document

outcome — success | failure | state_transition

type — audit type enum

stage cross-cuts State Management — the orchestration script sets it from its own run position (plan / build / review / document). State Management no longer tracks step position, so there is nothing to sync against.

**Type enums** — criteria for adding a type (keep the list lean; don't let it bloat):

- it represents a distinct, repeatable event or state change in the pipeline
- it isn't already expressible as a payload variation of an existing type
- operational: a debugging concern worth distinguishing; audit: a durable outcome or milestone worth recording
- if it's only a variation in detail, put it in the payload, not a new type
- operational and audit never share a type; each domain owns its own enum
Appendix A.1 — Exponential Backoff Definition

| **Parameter** | **Value** | **Notes** |
| --- | --- | --- |
| Initial delay | 100 ms | Delay before the first retry |
| Multiplier | 2× | Each delay doubles: 100 → 200 → 400 → 800 → 1600 ms |
| Max retries | 5 | Attempts before giving up |
| Max delay cap | 2000 ms | Delays never exceed this, even as the multiplier compounds |
| Jitter | ±20% | Randomised per attempt; prevents synchronised retry storms across sinks |
| Total max elapsed | ~5 s | Ceiling on total retry time before exhaustion |
| On exhaustion | apply overflow strategy | Hand off to the sink's drop_newest (default) or spill_to_disk |

Appendix A.2 — Bounded Queue Definition

| **Parameter** | **Value** | **Notes** |
| --- | --- | --- |
| Max capacity | 10,000 events | Queue holds up to this many events; when full, backpressure activates (retry per A.1, then overflow strategy) |

Appendix A.3 — Spill to Disk Location

| **Field** | **Format** | **Example** |
| --- | --- | --- |
| Spill path | logs/{adw_id}/overflow.jsonl | logs/adw-2026-07-08-abc123/overflow.jsonl |
| File format | JSON Lines (one event per line) | {"schema_version": "1.0", "adw_id": "...", ...} |
| Rotation | None (single file per run) | File grows until run ends, then archive |

| **Term** | **Definition** |
| --- | --- |
| Logger | The central event-logging service and entry point. Exports log(), builds a LogEvent from each call, and emits it into the stream. |
| Producer | Any code that calls log() — a stage, agent, or tool. Emits events without knowing or depending on where they land. |
| Orchestrator | The pipeline's workflow engine. Consumes logged events and owns all control-flow decisions (retry, abort, continue). Distinct from the logger, which only records. |
| Stream | The single ordered queue holding every emitted event before it fans out to appenders. |
| Appender | A handler that consumes from the stream, applies its own filter, invokes a layout, and writes to a sink. Filtering is decentralised — each appender owns its criteria. |
| Layout | The formatter that transforms an event into a sink's output format. |
| Sink | The destination an appender writes to — console, file, or UI stream. |
| LogEvent | The structured event object the logger builds and emits, shaped by the event schema (envelope + payload). |
| Event Envelope | The fixed outer metadata wrapping every event. Shared base: schema_version, log_id, adw_id, issue_id, ts, description, payload. Operational adds level, stage, type; audit adds stage, outcome, type. Versioned as a unit; the payload inside it evolves freely. |
| Payload | The flexible, event-type-specific data carried inside the envelope (e.g. an llm_call carries model and tokens). |
| Design Principle | A governing idea explaining why the system is shaped as it is. Few, high-level, rarely change; everything traces back to one. |
| Guardrail | A hard build-time constraint on what may be constructed — a binary never/always, no default, no exceptions. |
| Policy | A runtime if-then the system executes when a situation arises. Carries a default, often configurable. |
| Bounded Queue | A queue with a fixed maximum size. On overflow it must apply a backpressure strategy rather than grow unbounded. |
| Backpressure Strategy | The runtime rule for a full bounded queue: retry with exponential backoff, then on exhaustion apply the sink's overflow strategy. |
| Overflow Strategy | The per-sink action taken once retries are exhausted — drop_newest (default) or spill_to_disk. |
| drop_newest | Overflow action: discard the incoming event and emit a warning. |
| spill_to_disk | Overflow action: write the event to the local durable stream instead of discarding it. |
| Exponential Backoff | The retry timing definition (Appendix A.1): 100 ms initial delay, 2× multiplier, 5 max retries, 2000 ms cap, ±20% jitter, ~5 s total max elapsed. |
| Async Appender | Appender backed by a bounded queue that never stalls the producer. |
| Routing Appender | Appender that maps each event to a sink by a per-event key. |
| Failover Appender | Appender that writes to a primary sink, falling back to secondaries on failure. |
| Audit Logging | Durable record of what happened and when — outcomes, coarse granularity. One of two logging types (an architectural distinction, not severity). |
| Operational Logging | In-the-moment debugging output, severity-based (ERROR/WARN/INFO/DEBUG). The second logging type. |
| Version Discriminator | A field introduced on a breaking envelope schema change so consumers know which schema version they're reading. |
| Upcasting | Transforming old-schema events into the current schema, reserved for true restructuring beyond additive change or versioning. |
| Schema Version | The envelope field marking which version of the event schema an event conforms to. |

Enqueue-or-drop — the non-blocking behaviour of log() on the caller’s thread: it attempts to place the event into the queue and returns immediately. If the queue has room, the event is enqueued; if the queue is full, the event is handed to the overflow strategy (drop_newest / spill_to_disk)
