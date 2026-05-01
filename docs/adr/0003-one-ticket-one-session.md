# ADR 0003: One Ticket, One Fresh Session

## Status

Accepted

## Context

The evaluator feeds the system a batch of already-created support tickets.

We do not want prior tickets to bias later ones, and we do not need a
long-lived cross-ticket conversation model.

## Decision

Start a fresh session for every ticket.

Session memory is local to that single ticket run.

## Consequences

- no cross-ticket memory leakage
- simpler debugging and replay
- cleaner evaluation behavior
