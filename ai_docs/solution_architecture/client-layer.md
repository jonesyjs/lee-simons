# Client Layer — Solution Architecture

## Overview

The Client Layer sits between the ADW pipeline and every backend it calls — the Claude Headless CLI, the GitHub CLI, and later APIs and MCP servers. It owns one responsibility: performing the raw call to an external system and returning its response.

It does not know why the call is being made. Intent lives one level up, in the Operations layer: an operation such as `create-branch` knows it is creating a branch and composes two client calls to do it — one to a model to generate the name, one to GitHub to cut the branch. Neither client knows it is part of "creating a branch". Each executes its own command, blind to the goal.

The layer explicitly does **not** own domain logic, control flow, orchestration, or caching. It owns the mechanics of the call and the reliability of that call — nothing else.

This document is written to be enforced by an agent building a client. Its job is to make the boundary unambiguous: what may be built inside the Client Layer, and what must be pushed up.

## Design Principles

- **Intent-based separation.** Operations expose the goal; clients are blind to it. The operation knows *what and why*; the client knows *how*. This is the governing principle — every guardrail and policy below traces back to it.
- **Clients are reusable because they are dumb to intent.** The same model client that generates a branch name can generate a commit message. It has no opinion about either. Any knowledge of the problem being solved is leakage upward into Operations.
- **Ports & Adapters (Hexagonal).** The core (pipeline + operations) calls a *port* — an interface expressed in a vocabulary of action. An *adapter* in the Client Layer implements that port against the real tool. The core depends on the port, never on the adapter.
- **Every call is an RPC.** Request → response. Every call to a model or a tool is structurally identical, which is what makes a uniform client interface possible.
- **Infrastructure belongs in the base class.** Retry, timeout, deadline, and the RPC contract recur regardless of backend. They are infrastructure code, written once in the abstract base and inherited — never re-implemented per client, and never a separate layer or subsystem of their own.
- **Extensibility is designed in, not retrofitted.** The access mechanism is what defines the child class: subprocess to cli, http for API and rpc for MCP as examples. The hierarchy exists from the first line of code so that adding a transport is a new child, not a rewrite of the base.
## Guardrails

Hard build-time never/always constraints. No defaults, no exceptions.

**Boundary:**

- A client never references the goal of the operation calling it. No parameter, branch, or comment in a client may encode why the call is happening.
- A client never decides control flow. It performs its call and returns; retry-vs-abort-vs-continue belongs to the operation and the orchestrator.
- A client never composes two backend calls. Composition is an operation's job (`create-branch` composes two client calls; neither client knows about the other).
**Class hierarchy:**

- The base Client class is never instantiated. It is abstract and agnostic of every access mechanism. Callers always instantiate a concrete child chosen by access type.
- No access mechanism is ever implemented in the base class. Subprocess invocation, HTTP, and MCP each belong to their own child.
- Infrastructure is never re-implemented in a child. Retry, backoff, timeout, deadline, and the RPC contract come from the base by inheritance.
**Helper Pattern (the three rules):**

A helper is a transformation utility that lives inside the Client Layer — an extension-style function that reshapes a response. Helpers exist to keep the client's own mechanics tidy, and they are the most likely back door for domain logic to enter the layer.

They are therefore bounded by three rules:

1. **No dependency on the core system.** A helper must not import, reference, or know anything about the domain or the calling operation's intent.
2. **No core-system rule implementation.** Even with no dependency, a helper must never *implement* a domain rule. Domain calculations and domain transformations belong in the service (operation) layer. Absence of a dependency is not permission to reimplement the rule locally.
3. **System-level rules are acceptable.** Universal, cross-cutting rules — normalising all timestamps to UTC, unit conversion, schema translation — are permitted in a helper. They are system logic, not domain logic, and therefore do not fall inside the domain-logic threshold.
**One function, one command - Subprocess Type Implementation Detail:**

- A client function exposes exactly one command. Variation is applied through inputs, never through branching inside the client.
- Any logic that *changes* those inputs runs in the Operations layer. The client never decides which flag, mode, or variant to use; it is told.

## Policies

If-then runtime behaviour.

### Transformation Escalation

The escalation ladder governs how much a client is permitted to do to a response. Start at the bottom; climb only when required, and stop at the domain-logic threshold.

| **Level** | **What it does** | **Permitted in the Client Layer** |
| --- | --- | --- |
| 1. Pass-through | Ships the payload out, returns the response unchanged. No transformation. | Always. This is the default. |
| 2. Facade | Simplifies the interface to a complex subsystem — unwrapping a nested response, renaming a key, converting a unit. Same value restated. | Yes, up to the domain-logic threshold. |
| 3. Service | Makes new values, or applies rules that only make sense in-domain. | No. Escalates out of the layer into Operations. |

**The domain-logic threshold** — the test applied at every step up the ladder:

Does understanding this rule require knowing what problem we are solving?

- **No** → it is system logic. It may live in the client, in a helper.
- **Yes** → it is domain logic. It escalates to the service (operation) layer.
**Helper → Service boundary:**

- Helper = the client's side of the line. Mechanical reshaping, no domain knowledge. Bounded by the three helper rules above.
- Service = the operations side of the line. The generic term for operations, scripts, and anything holding domain-specific logic. Owns intent and every rule that depends on it.
On any uncertainty about which side a transformation falls on → place it in the service. The cost of a rule sitting one level too high is redundancy; the cost of a rule sitting one level too low is a client that has silently become domain-aware.

### Resilience

Infrastructure behaviour, owned by the base Client class and inherited by every child regardless of access type.

- **On a transient failure** → retry, 3 attempts standard.
- **Backoff** → exponential with jitter (see Appendix A.1).
- **Retryable** → transient errors only: timeouts, and the per-transport equivalents of a transient fault.
- **Not retryable** → caller errors and any deterministic failure. Retrying them repeats the same failure.
- **Timeout per attempt** → short and fixed, 5–10 seconds.
- **Deadline for the whole operation** → set by the caller; the client respects it and does not extend it with retries.
- **On error-rate spike** → circuit breaker, optional.
- **On any response** → never cache it.
Each child maps its transport's failures onto the transient/deterministic split; the retry behaviour itself is never re-implemented.

## Architecture

The Client Layer is the adapter ring of a Ports & Adapters (Hexagonal) arrangement, realised as a class hierarchy.

- **Core** — the pipeline and its Operations layer. Holds all intent and all domain rules.
- **Port** — the interface the core calls, expressed in a vocabulary of action. The core depends on this and nothing more.
- **Adapter** — the Client Layer implementation of that port against a real tool. Swappable without the core noticing.
### The class hierarchy

There is no separate shared layer, and no infrastructure subsystem sitting beside the clients. The Client Layer **is** the base class, and the infrastructure lives inside it.

**Base Client (abstract).** Holds the infrastructure code: the RPC contract, retry, backoff, per-attempt timeout, deadline enforcement, and the optional circuit breaker. It is agnostic of *every* access mechanism — it holds no subprocess code, no HTTP code, no MCP code. It is never instantiated.

**Concrete children, one per access type.** Each child implements how the call is actually made, and inherits everything else:

| **Client** | **Access point** | **Status** |
| --- | --- | --- |
| SubprocessClient | A local CLI, invoked as a subprocess | The only implementation in the first pipeline |
| HttpClient | An HTTP API | Anticipated, not built |
| McpClient | An MCP server | Anticipated, not built |

Choosing a client is choosing an access point. An operation that needs a CLI takes a SubprocessClient; one that later needs an API takes an HttpClient. The operation's own code does not change — the port it calls is the same.

**Why the hierarchy exists from day one.** Subprocess is the first access mechanism, not the permanent one — APIs and MCP servers are expected. Baking subprocess into the base would make the first new transport a rewrite of the base class rather than an addition beside it. The abstraction is therefore built up front, when it costs nothing, rather than extracted later under pressure.

### Flow

`Operation (knows the goal)`

`  → Port (vocabulary of action)`

`    → Concrete Client, e.g. SubprocessClient (blind to the goal)`

`      ↑ inherits infrastructure from Base Client (RPC, retry, timeout, deadline)`

`      → Helper (mechanical reshaping only)`

`      → Backend (CLI now; API, MCP server later)`

An operation may call several clients; a client never calls another client, and never calls back into the core.

### Initial implementations

Both backends in the first pipeline are local CLIs on the machine running the pipeline, and are therefore reached through the same child, SubprocessClient:

| **Backend** | **Access point** | **Client** | **Example use** |
| --- | --- | --- | --- |
| GitHub CLI | Local CLI | SubprocessClient | Cut a branch; post an issue comment |
| Claude Headless CLI | Local CLI | SubprocessClient | Generate a branch name; run an agent step |

The one-function-one-command rule follows directly from this shape: a client function maps to exactly one command, and every variant of that command is expressed as an input the operation supplies.

**Worked example — **`create-branch`**.** The operation owns the intent. It calls the Claude client to generate a name (one command, inputs supplied by the operation), then calls the GitHub client to cut the branch (one command, name supplied as an input). The name-generation is a thick, value-making step, so it sits in the operation, above the clients. The pipeline sees one unit; both client calls are hidden inside it, and neither client knows a branch is being created.

## Modelling

**Call contract.** Every client call is an RPC: request → response. The interface is uniform because every model call and every tool call is structurally identical. The contract is defined once on the base class and holds for every child.

| **Element** | **Shape** | **Notes** |
| --- | --- | --- |
| Request | Command identifier + inputs | One command per function. All variation carried in inputs, supplied by the operation. |
| Response | The backend's result, unchanged or facade-simplified | Never a new value computed from others. |
| Failure | Transient vs deterministic | Only transient is retryable. Each child maps its transport's faults onto this split; the client surfaces the failure, the operation decides what it means. |

**Responsibility split across the hierarchy.**

| **Concern** | **Base Client (abstract)** | **Concrete child** |
| --- | --- | --- |
| RPC contract | Owns | Inherits |
| Retry, backoff, timeout, deadline | Owns | Inherits |
| Circuit breaker (optional) | Owns | Inherits |
| Access mechanism (subprocess / HTTP / MCP) | None — agnostic | Owns |
| Transient-vs-deterministic mapping | Defines the split | Maps its own transport onto it |
| Instantiation | Never | Always |

**Helper signature shape.** A helper takes a response (or a fragment of one) and returns a reshaped response. It takes no domain object, returns no domain object, and holds no reference to the calling operation.

## Assumptions

- Operations own all intent and all domain rules. A client can be blind to the goal only because something above it is not.
- The orchestrator owns control flow, per the Workflow SA doc. Clients surface failures rather than deciding on them.
- The initial backends are reachable as local CLIs on the machine running the pipeline, invoked as subprocesses.
- The access mechanism will change. APIs and MCP servers are expected, which is why the hierarchy is built before it is needed.
- Every backend call is expressible as request → response. A backend that is not RPC-shaped (a long-lived stream, a callback) is outside the current design.
- Caching, if ever needed, is handled above the Client Layer.
## Open Decisions

- **Per-backend client structure.** Both initial backends run through SubprocessClient. Whether GitHub and Claude Headless are further subclasses of it, or command modules composed on top of a single SubprocessClient, is unsettled. The hierarchy is fixed by access type; how a specific backend hangs off its access type is not.
- **Transient classification for subprocess.** SubprocessClient must map CLI failures onto the transient/deterministic split, but which exit codes and stderr signatures count as transient is undefined. Needs a mapping per CLI before the resilience policy is mechanically enforceable.
- **Circuit breaker.** Marked optional, with no trigger threshold, open duration, or half-open probe defined. Deferred until real error-rate data exists.
- **Auto-generated children.** Children can in principle be generated from a machine-readable spec, and MCP standardises runtime discovery and invocation. Neither is used in the first pipeline; revisit when McpClient is actually built.
- **Where the deadline is set.** The caller sets the whole-operation deadline, but whether that is the operation or the orchestration script is not pinned.
- **Enforcement of the domain-logic threshold.** The three helper rules are stated as build-time guardrails. Whether any is mechanically checkable (e.g. an import lint on helpers) versus semantic-only — and therefore examiner-judged per the LLM Judge notes — is undecided.
## Appendices

### Appendix A.1 — Exponential Backoff Definition

Owned by the base Client class; inherited by every child.

| **Parameter** | **Value** | **Notes** |
| --- | --- | --- |
| Initial delay | 100 ms | Delay before the first retry |
| Multiplier | 2× | Each delay doubles: 100 → 200 → 400 ms |
| Max retries | 3 | Attempts before giving up |
| Max delay cap | 2000 ms | Delays never exceed this, even as the multiplier compounds |
| Jitter | ±20% | Randomised per attempt; prevents synchronised retry storms |
| On exhaustion | Surface the failure | The client reports; the operation decides. Never retried past the caller's deadline. |

### Appendix A.2 — Pattern Reference

Prior-art patterns considered while shaping the layer. Reference only — the layer's actual position is the escalation ladder in Policies.

| **Pattern** | **Definition** | **Relation to this layer** |
| --- | --- | --- |
| Adapter | Protocol/format translation. Thinnest; pass-through, no simplification. | Level 1 of the escalation ladder. |
| Facade | Simplified interface over a complex subsystem; hides complexity. | Level 2, bounded by the domain-logic threshold. |
| Gateway | Encapsulates access to an external system; adds policy (retry, timeout). | The resilience infrastructure on the base class. |
| Anti-Corruption Layer | Translator at a border crossing — adapter + translator + facade composed. | Not adopted; its translation step would cross the domain-logic threshold. |

## Glossary

| **Term** | **Definition** |
| --- | --- |
| Client Layer | The adapter ring between the pipeline and its backends, realised as the Client class hierarchy. Performs raw calls; blind to the goal. |
| Base Client | The abstract class at the root of the hierarchy. Holds the infrastructure code; agnostic of every access mechanism; never instantiated. |
| Concrete child | A subclass of Base Client implementing one access mechanism (SubprocessClient, HttpClient, McpClient). Always what a caller instantiates. |
| Infrastructure code | The RPC contract, retry, backoff, timeout, deadline, and circuit breaker. Lives in the base class and is inherited — not a shared layer, not a subsystem. |
| Access point | The kind of thing being called — a local CLI, an HTTP API, an MCP server. Selecting an access point selects a child. |
| SubprocessClient | The child that invokes a local CLI as a subprocess. The only implementation in the first pipeline; serves both GitHub CLI and Claude Headless CLI. |
| Operations layer | The service layer above the clients. Owns intent, composes client calls into meaningful units (e.g. create-branch). |
| Intent-based separation | The governing principle: operations expose the goal, clients are blind to it. |
| Port | The interface the core calls, expressed in a vocabulary of action. |
| Adapter | A Client Layer implementation of a port against a real tool. In this design, a concrete child. |
| Core | The pipeline and its operations — everything holding intent and domain rules. |
| Helper Pattern | A transformation utility inside the Client Layer. Mechanical reshaping only; bounded by the three helper rules. |
| Service Pattern | The generic term for operations, scripts, and anything holding domain-specific logic. The operations side of the boundary. |
| Helper → Service boundary | The line between mechanical reshaping (client) and domain logic (operations). |
| Domain-logic threshold | The test for that line: does understanding this rule require knowing what problem we are solving? Yes → service. No → helper. |
| Transformation Escalation | The policy ladder — pass-through → facade → service — governing how much a client may do to a response. |
| Pass-through | Level 1: payload out, response back unchanged. The default. |
| Thin (extraction) | Pulling a value out of a response unchanged — key rename, nested access, unit conversion. Same value restated. |
| Thick (transformation) | Making a new value from others — concatenating, summing, computing. Belongs above the client. |
| One function, one command | The rule that a client function exposes exactly one command; variation comes through inputs from the operation. |
| RPC contract | The uniform call shape: request → response. Defined on the base class; holds for every child. |
| Transient failure | A retryable error — a timeout or a transport's equivalent transient fault. Distinct from a deterministic failure, which is never retried. |
| Deadline | The caller-set ceiling on a whole operation. The client respects it and never extends it with retries. |
| Circuit breaker | Optional resilience mechanism for error-rate spikes. Not specified in the first pass. |
