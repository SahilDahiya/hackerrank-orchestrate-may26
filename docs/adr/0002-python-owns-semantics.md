# ADR 0002: Python Owns Product Semantics

## Status

Accepted

## Context

We may later introduce an execution helper for fast read-only tools. JACA shows
that this can work when the ownership boundary is explicit.

The risk is semantic drift across languages or processes.

## Decision

Python remains the canonical owner of:

- tool meaning
- session meaning
- runtime meaning
- validation
- final output meaning

Any later helper in another language is an internal execution seam only.

## Consequences

- helper processes can improve performance without owning behavior
- tool schemas and validation stay centralized
- architecture stays explainable in the interview
