# ADR 0005: Use Structured Final Output For Ticket Results

## Status

Accepted

## Context

The external submission contract requires a strict final row shape. The runtime
already uses explicit internal contracts, and the canonical agent is expected to
operate with tools and grounded evidence rather than produce free-form prose.

## Decision

The canonical agent should return the final ticket result as structured
Pydantic output with these fields only:

- `status`
- `product_area`
- `response`
- `justification`
- `request_type`

The host validates that result and writes the CSV row. It does not parse the
final result out of plain text.

## Consequences

- the model-facing output contract matches the submission contract directly
- host-side parsing complexity is avoided
- enum validation and required-field enforcement stay straightforward
