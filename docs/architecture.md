# Architecture

## System Overview

The architecture is intentionally thin.

Use PydanticAI as the runtime engine for a tool-using agent. Keep the repo's
own architecture centered on explicit ownership boundaries.

## External Vs Internal Contracts

The challenge-facing contract is the `code/main.py` entry point.

That external contract is responsible for:

- reading the required input CSV
- running the batch flow
- writing the required output CSV

Behind that, we keep separate internal contracts for:

- `RunTicketRequest`
- `TicketDeps`
- canonical tool signatures
- the agent return object

Those internal contracts exist to keep implementation boundaries explicit. They
do not replace the submission contract.

## Main Shape

```text
code/main.py
  -> batch host loop
  -> per-ticket session setup
  -> runtime.run_ticket(request)
  -> validated result
  -> append row to support_tickets/output.csv
```

Inside the runtime:

```text
run_ticket(request)
  -> create ticket-scoped deps
  -> assemble canonical read-only toolset
  -> run canonical PydanticAI agent with structured output
  -> return final result object
```

## Canonical Agent Assembly

There should be one canonical agent factory.

Its job is to assemble:

- model
- instructions
- deps type
- canonical toolset

The important rule is that agent construction should not be scattered across
the repo.

Suggested shape:

```text
build_canonical_agent(...) -> Agent[TicketDeps, ...]
```

That agent's instruction set should stay small and tool-oriented rather than
becoming a long policy document.

## Deps And Tools

The runtime should create one ticket-scoped deps object for each ticket run.

That deps object is the canonical way tools learn their execution context.

Suggested shape:

```text
TicketDeps
- data_root
- ticket metadata needed by tools
- session-local runtime context if needed
```

Model-facing tools should be plain PydanticAI tool functions that accept
`RunContext[TicketDeps]`.

That is the preferred pattern over per-ticket closure factories.

In other words, prefer:

```text
tool(ctx: RunContext[TicketDeps], ...)
```

over:

```text
create_tool(ticket_specific_state) -> Tool(...)
```

unless there is a concrete reason to do otherwise.

The runtime should preserve enough breadcrumb context from the corpus for the
agent to ground `product_area` in evidence such as directory structure,
document title, or section hierarchy, rather than inventing broad labels from
scratch.

## Ownership

### Host owns

- CSV input/output
- ticket iteration
- fresh session per ticket
- `RunTicketRequest` creation
- final validation
- deterministic failure handling

### Runtime owns

- `TicketDeps` creation
- agent construction
- session-local execution
- prompt/instruction assembly
- tool registration
  - ticket result production

### Tools own

- read-only access to scoped corpus data
- concise, predictable results
- no hidden mutation

## Internal RPC-Shaped Boundary

We want function-call boundaries that are explicit enough to become contracts.

Example shape:

```text
RunTicketRequest -> run_ticket(...) -> RunTicketResult
```

This is internal RPC in shape, not a separate transport protocol.

## Tool Policy

Canonical initial tools:

- `read`
- `grep`
- `find`
- `ls`

Rules:

- all tool reads are scoped to `data/`
- read-only tools may run in parallel
- mutating actions do not belong to the model-facing toolset by default
- the registry should stay thin and return the canonical toolset, not own
  product semantics

Initial function signatures should stay minimal and may evolve if actual usage
shows a better boundary. We should prefer deliberate contract updates over
guessing every future parameter up front.

The first-pass signatures are:

```python
read(
    ctx: RunContext[TicketDeps],
    path: str,
    offset: int | None = None,
    limit: int | None = None,
) -> str

grep(
    ctx: RunContext[TicketDeps],
    pattern: str,
    path: str | None = None,
    ignore_case: bool = False,
    literal: bool = False,
    limit: int = ...,
) -> str

find(
    ctx: RunContext[TicketDeps],
    pattern: str,
    path: str | None = None,
) -> str

ls(
    ctx: RunContext[TicketDeps],
    path: str | None = None,
) -> str
```

All paths resolve explicitly from `data_root`. There is no remembered
current-directory state between tool calls.

## Prompt And Output Policy

The canonical agent should use tools before any grounded reply and inspect the
local corpus when evidence is needed to answer or confirm escalation. A
self-evident unsupported, outage-like, invalid, or not-answerable ticket may
escalate without forced tool calls.

The prompt should explicitly enforce:

- use only the provided corpus as evidence
- do not invent policies, product behavior, or unsupported steps
- `status` must be one of `replied` or `escalated`
- `request_type` must be one of `product_issue`, `feature_request`, `bug`, or
  `invalid`
- `product_area` should be a short label, preferably derived from corpus
  breadcrumbs
- escalate when the ticket is risky, unsupported, ambiguous, or when the
  evidence is weak, insufficient, or conflicting

The final output split should stay clear:

- `response` is user-facing support guidance and should not expose raw repo or
  filesystem paths
- `justification` is evidence-facing and must cite support from `data/` or
  clearly state that escalation was chosen because the corpus was insufficient

The final agent return should be structured Pydantic output for the exact final
row fields, not plain text followed by host-side parsing.

## Evidence Formatting Policy

Evidence-oriented tool output should use one common breadcrumb shape where it
applies:

- `Path`
- `Title` if available
- `Section` if available
- blank line
- content or excerpt

Missing metadata lines should be omitted rather than replaced with placeholder
values.

Tool-specific expectations:

- `read` always emits the breadcrumb header
- `grep` returns grouped file-level evidence blocks rather than one block per
  raw match
- `find` returns matching paths only
- `ls` remains a simple directory listing tool

## Future Helper Boundary

If needed later, a narrow read-only helper in Go is acceptable for performance.

If that happens, the boundary remains:

- helper owns execution speed
- Python owns semantics

That helper is an internal seam, not a second architecture.
