from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent, RetryPromptPart
from pydantic_ai.usage import RunUsage

from schemas import RunTicketRequest, TicketResult

RESULT_PREVIEW_LIMIT = 1200


def _json_default(value: Any) -> str:
    return str(value)


def _serialize_result_preview(content: Any) -> str:
    if isinstance(content, str):
        return content[:RESULT_PREVIEW_LIMIT]
    serialized = json.dumps(content, ensure_ascii=True, default=_json_default)
    return serialized[:RESULT_PREVIEW_LIMIT]


class TicketAuditWriter:
    def __init__(self, *, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def append(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=True, default=_json_default))
            f.write("\n")


@dataclass
class TicketAuditRecorder:
    writer: TicketAuditWriter
    pending_calls: dict[str, dict[str, Any]] = field(default_factory=dict)

    def write_ticket(self, request: RunTicketRequest) -> None:
        self.writer.append(
            {
                "type": "ticket",
                "ticket_id": request.ticket_id,
                "company": request.company,
                "subject": request.subject,
                "issue": request.issue,
            }
        )

    def record_tool_call(self, event: FunctionToolCallEvent) -> None:
        self.pending_calls[event.tool_call_id] = {
            "tool_name": event.part.tool_name,
            "args": event.part.args,
        }

    def record_tool_result(self, event: FunctionToolResultEvent) -> None:
        call = self.pending_calls.pop(event.tool_call_id, {})
        tool_name = call.get("tool_name", getattr(event.result, "tool_name", None))
        args = call.get("args")
        result = event.result
        content = result.content if not isinstance(result, RetryPromptPart) else result.content
        self.writer.append(
            {
                "type": "tool",
                "tool_name": tool_name,
                "args": args,
                "result_preview": _serialize_result_preview(content),
            }
        )

    def write_final_result(self, result: TicketResult, usage: RunUsage) -> None:
        record = {"type": "final_result"}
        record.update(result.model_dump(mode="json"))
        record["usage"] = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "requests": usage.requests,
            "tool_calls": usage.tool_calls,
        }
        self.writer.append(record)

    def write_error(self, error: Exception) -> None:
        self.writer.append(
            {
                "type": "error",
                "error_type": type(error).__name__,
                "message": str(error),
            }
        )
