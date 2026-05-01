from __future__ import annotations

from collections.abc import AsyncIterable
from typing import Any
from pathlib import Path

from agent import build_canonical_agent
from audit import TicketAuditRecorder, TicketAuditWriter
from pydantic_ai.messages import AgentStreamEvent, FunctionToolCallEvent, FunctionToolResultEvent
from pydantic_ai.usage import UsageLimits
from schemas import RunTicketRequest, TicketDeps, TicketResult

RUN_REQUEST_LIMIT = 200


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
    audit_path: Path | None = None,
) -> TicketResult:
    agent = build_canonical_agent(model=model)
    prompt = build_ticket_prompt(request)
    recorder: TicketAuditRecorder | None = None
    event_stream_handler = None
    if audit_path is not None:
        recorder = TicketAuditRecorder(
            writer=TicketAuditWriter(path=audit_path)
        )
        recorder.write_ticket(request)

        async def handle_events(
            _: Any,
            events: AsyncIterable[AgentStreamEvent],
        ) -> None:
            assert recorder is not None
            async for event in events:
                if isinstance(event, FunctionToolCallEvent):
                    recorder.record_tool_call(event)
                elif isinstance(event, FunctionToolResultEvent):
                    recorder.record_tool_result(event)

        event_stream_handler = handle_events

    try:
        result = agent.run_sync(
            prompt,
            deps=TicketDeps.from_request(request),
            usage_limits=UsageLimits(request_limit=RUN_REQUEST_LIMIT),
            event_stream_handler=event_stream_handler,
        )
        output = result.output
        if not isinstance(output, TicketResult):
            raise TypeError(f"expected TicketResult output, got {type(output).__name__}")
        if recorder is not None:
            recorder.write_final_result(output, result.usage())
        return output
    except Exception as error:
        if recorder is not None:
            recorder.write_error(error)
        raise
