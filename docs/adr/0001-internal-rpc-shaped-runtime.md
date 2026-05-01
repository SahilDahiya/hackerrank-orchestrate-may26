# ADR 0001: Use An Internal RPC-Shaped Runtime

## Status

Accepted

## Context

The challenge requires a batch CLI, but the runtime still needs explicit
boundaries for sessions, tool use, and result production.

JACA's architecture is useful here as a design influence, especially its
emphasis on contracts and ownership boundaries. But this repo does not have the
same need for a public stdio RPC layer.

## Decision

Use an internal RPC-shaped runtime:

- host loop creates a request
- runtime handles one ticket
- runtime returns one result

Do not introduce a separate public RPC transport at the start.

## Consequences

- the code can remain simple and testable
- boundaries stay explicit
- a future transport can be added later if a real consumer appears
- we avoid protocol complexity that the evaluator does not need
