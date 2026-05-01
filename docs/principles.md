# Principles

These principles are the working rules for this repo. They are influenced by
JACA's design stance, but adapted to this challenge's simpler CLI contract.

## 1. The contract is the product surface

Anything that crosses a boundary must have a clear shape.

In this repo, the important boundaries are:

- evaluator -> `code/main.py`
- host loop -> ticket runtime
- runtime -> tools
- runtime -> final output row

If a boundary is ambiguous, the implementation will drift.

There are two contract layers:

- external submission contract
- internal runtime contracts

The external submission contract is fixed by the challenge.
The internal runtime contracts are ours to design well.

## 2. Python owns semantics

Python is the canonical owner of:

- session meaning
- tool names and tool schemas
- escalation/reply meaning
- final CSV row meaning
- validation and recovery policy

If we later add a helper in another language, it is an execution seam only. It
must not become a second owner of product semantics.

## 3. Internal RPC shape, not public RPC transport

We want RPC-like clarity inside the codebase:

- request object in
- typed result out
- explicit session boundary
- explicit tool registry

But the challenge entry point is still one batch CLI. We do not introduce a
separate public RPC transport unless a real external consumer appears.

## 4. One ticket, one fresh session

Each ticket starts a new session.

Session memory exists only inside that ticket run. There is no cross-ticket
memory and no cross-ticket contamination.

This keeps the system auditable and makes failure analysis tractable.

## 5. Canonical tools stay small and explicit

The agent should have a small tool surface.

Initial canonical read-only tools:

- `read`
- `grep`
- `find`
- `ls`

Tool scope is restricted to `data/`.

The host, not the model, owns final CSV writing.

## 6. Read-only exploration may be parallel

High-frequency read-only tools are parallel-eligible.
Anything that mutates state stays serialized.

For this challenge, the important serial mutation is output writing, and it
should remain host-owned.

## 7. Use PydanticAI as the engine, not the architecture

PydanticAI provides:

- the agent runtime
- tool calling
- session-local model interaction
- structured boundaries where useful

But the repo still owns:

- runtime contracts
- per-ticket session lifecycle
- tool registry meaning
- output validation

## 8. Prefer direct framework primitives before local abstraction

Do not build wrappers just to have wrappers.

Use the framework directly until a local seam is justified by one of:

- repeated complexity
- a contract boundary
- a testability need
- a real ownership rule

## 9. Backend-owned validation beats model-owned hope

The model may decide. The host must verify.

That applies to:

- allowed output values
- row completeness
- tool result shape
- file access scope

## 10. Optimize only after the boundary is correct

If we later need a fast read-only helper, that is a narrow execution
optimization.

We do not start with:

- a separate backend process
- generic RPC transport
- a helper that owns product behavior

## 11. Be explicit without becoming brittle

These docs define the current intended contracts.

They are meant to make implementation clearer, not freeze the design
prematurely.

If implementation or evaluation exposes a better boundary, we should update the
docs and the code together.

The rule is:

- be explicit now
- reassess when reality gives new information
- avoid casual churn, but do not cling to a weak design

## 12. Prompt policy should be small and tool-oriented

The system prompt should stay small.

It should state only the rules the model itself must internalize:

- it is handling one support ticket
- it must use the canonical tools
- it must ground decisions in the provided corpus
- it must escalate when evidence or safety requires it
- it must return the required final fields

Anything we can enforce through runtime boundaries, tool scope, validation, or
host ownership should be enforced there first rather than described only in
prompt prose.
