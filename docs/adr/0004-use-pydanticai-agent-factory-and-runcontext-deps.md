# ADR 0004: Use One PydanticAI Agent Factory And RunContext Deps

## Status

Accepted

## Context

JACA's early evolution is instructive here.

It started with thin `Tool(...)` objects and a `FunctionToolset`, then moved
through workspace-bound tool factories, and later settled on a cleaner
canonical pattern:

- one canonical agent factory
- one deps type
- tools as plain functions using `RunContext[Deps]`

That later pattern keeps assembly explicit without scattering state through
closures.

## Decision

For this repo:

- create one canonical agent factory
- create one ticket-scoped deps type
- implement model-facing tools as plain PydanticAI tool functions using
  `RunContext[TicketDeps]`
- keep the tool registry thin

## Consequences

- agent construction stays centralized
- tool execution context is explicit
- tool code stays easier to test and reason about
- we avoid unnecessary per-ticket closure factories unless a concrete need
  appears
