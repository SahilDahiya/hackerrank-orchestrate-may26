from __future__ import annotations

from typing import Any

from agent import build_canonical_agent
from schemas import RunTicketRequest, TicketDeps, TicketResult


def build_ticket_prompt(request: RunTicketRequest) -> str:
    return "\n".join(
        [
            f"Ticket ID: {request.ticket_id}",
            f"Company: {request.company}",
            f"Subject: {request.subject}",
            "Issue:",
            request.issue,
        ]
    )


def run_ticket_sync(
    *,
    request: RunTicketRequest,
    model: Any,
) -> TicketResult:
    agent = build_canonical_agent(model=model)
    result = agent.run_sync(
        build_ticket_prompt(request),
        deps=TicketDeps.from_request(request),
    )
    output = result.output
    if not isinstance(output, TicketResult):
        raise TypeError(f"expected TicketResult output, got {type(output).__name__}")
    return output
