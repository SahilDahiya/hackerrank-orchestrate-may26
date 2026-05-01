# Contracts

These are the canonical boundaries we should preserve as the code appears.

## 0. Contract Layers

There are two different contract layers in this repo.

### External submission contract

This is the evaluator-facing contract:

- `code/main.py` is the known entry point
- it reads the challenge input CSV
- it writes the challenge output CSV

### Internal runtime contracts

These are our implementation contracts:

- `RunTicketRequest`
- `TicketDeps`
- tool signatures
- agent return shape

They exist behind `code/main.py` and are allowed to evolve as long as the
external submission contract remains intact.

## 1. Ticket Runtime Contract

The runtime should accept one ticket request and return one final result.

Suggested shape:

```text
RunTicketRequest
- ticket_id
- subject
- issue
- company
- data_root

RunTicketResult
- status
- product_area
- response
- justification
- request_type
```

The exact implementation type can change. The contract idea should not.

The first implementation should keep `RunTicketResult` limited to these final
row fields only. Internal audit metadata can be added later if there is a
clear need, but it should not expand the initial boundary by default.

`RunTicketResult` should be produced as structured Pydantic model output
directly by the agent runtime.

## 1.1 Canonical Agent Contract

There is one canonical model-facing agent for this repo.

That agent should be constructed in one place through one factory.

Suggested shape:

```text
build_canonical_agent(...) -> Agent[TicketDeps, ...]
```

This keeps tool surface, instructions, and deps wiring consistent.

## 1.2 Deps Contract

The agent should run against one ticket-scoped deps object.

Suggested shape:

```text
TicketDeps
- data_root
- ticket_id
- company
```

Tools should receive that context through `RunContext[TicketDeps]`.

## 2. Session Contract

One ticket creates one fresh session.

The session must not carry memory from prior tickets.

Session state is for:

- model-visible progress inside the ticket
- tool interaction history inside the ticket
- bounded traceability inside the ticket

## 3. Tool Contract

Canonical model-facing tools are read-only.

Initial tool names:

- `read`
- `grep`
- `find`
- `ls`

Shared rules:

- input and output shapes must be explicit
- paths must resolve under `data/`
- failures must be returned predictably
- no tool may silently broaden its scope
- tool functions should use `RunContext[TicketDeps]` rather than ad hoc
  captured state where possible
- the registry should be a thin selector/assembler, not a second policy layer

### Initial canonical signatures

The first implementation should start with these signatures:

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

These are the initial contracts, not a promise that they will never change.

If implementation shows a concrete need for arguments such as pagination,
offsets, limits, or stricter result shaping, we should revise the contract
deliberately rather than accreting ad hoc parameters.

Tool usage policy for the canonical agent:

- use tools before any grounded reply
- inspect the local corpus with tools when evidence is needed to answer or
  confirm escalation
- self-evident unsupported, outage-like, invalid, or not-answerable tickets
  may escalate without forced tool calls
- use tools against the provided corpus only
- preserve enough source breadcrumb context for grounded `product_area` and
  `justification`
- all paths resolve explicitly from `data_root`
- there is no remembered current-directory state between tool calls

### Evidence formatting

Where a tool returns evidence text rather than simple navigation output, it
should use one common breadcrumb shape:

```text
Path: ...
Title: ...        # if available
Section: ...      # if available

<content or excerpt>
```

Missing metadata lines should be omitted.

First-pass tool result expectations:

- `read` always uses the breadcrumb header
- `grep` returns grouped file-level evidence blocks with the breadcrumb header
- `find` returns paths only
- `ls` returns simple directory listings only

## 4. Output Contract

The final row written by the host must match the challenge contract exactly:

- `status`
- `product_area`
- `response`
- `justification`
- `request_type`

Allowed `status` values:

- `replied`
- `escalated`

Allowed `request_type` values:

- `product_issue`
- `feature_request`
- `bug`
- `invalid`

`product_area` remains free-form, but it should be a short support-domain label
grounded in corpus breadcrumbs where possible.

`response` is user-facing and should not expose raw repo or filesystem paths.

`justification` must cite evidence from `data/` or explicitly state that
escalation was chosen because the corpus did not provide sufficient grounded
support.

The agent should escalate not only for risky cases, but also when the evidence
base is weak, insufficient, or conflicting.

## 5. Ownership Contract

This repo should preserve one clear rule:

- model chooses within the allowed surface
- host verifies and commits the result

That is why CSV writing remains host-owned.
