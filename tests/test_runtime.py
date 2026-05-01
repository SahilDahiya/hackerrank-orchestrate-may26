from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import runtime  # noqa: E402
from pydantic_ai.messages import (  # noqa: E402
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.usage import RunUsage  # noqa: E402
from schemas import RequestType, RunTicketRequest, TicketResult, TicketStatus  # noqa: E402


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = RunTicketRequest(
            ticket_id="ticket-1",
            company="Claude",
            subject="Need workspace access",
            issue="Please restore access to my workspace.",
            data_root=Path("data").resolve(),
        )

    def test_build_ticket_prompt_includes_canonical_fields(self) -> None:
        prompt = runtime.build_ticket_prompt(self.request)
        self.assertIn("Ticket ID: ticket-1", prompt)
        self.assertIn("Company: Claude", prompt)
        self.assertIn("Subject: Need workspace access", prompt)
        self.assertIn("Issue:\nPlease restore access to my workspace.", prompt)

    def test_run_ticket_sync_passes_prompt_and_request_derived_deps(self) -> None:
        expected = TicketResult(
            status=TicketStatus.REPLIED,
            product_area="Workspace Access",
            response="Grounded response.",
            justification="Grounded in corpus.",
            request_type=RequestType.PRODUCT_ISSUE,
        )

        class FakeAgent:
            def __init__(self) -> None:
                self.calls: list[tuple[str, object, object]] = []

            def run_sync(
                self,
                prompt: str,
                *,
                deps: object,
                usage_limits: object | None = None,
                event_stream_handler: object | None = None,
            ) -> SimpleNamespace:
                self.calls.append((prompt, deps, usage_limits))
                return SimpleNamespace(output=expected)

        fake_agent = FakeAgent()
        with patch.object(runtime, "build_canonical_agent", return_value=fake_agent):
            result = runtime.run_ticket_sync(request=self.request, model="fake:model")

        self.assertEqual(result, expected)
        self.assertEqual(len(fake_agent.calls), 1)
        prompt, deps, usage_limits = fake_agent.calls[0]
        self.assertEqual(prompt, runtime.build_ticket_prompt(self.request))
        self.assertEqual(deps.data_root, self.request.data_root)
        self.assertEqual(deps.ticket_id, self.request.ticket_id)
        self.assertEqual(deps.company, self.request.company)
        self.assertIsNotNone(usage_limits)
        self.assertEqual(usage_limits.request_limit, runtime.RUN_REQUEST_LIMIT)

    def test_run_ticket_sync_fails_hard_on_non_ticket_result_output(self) -> None:
        class FakeAgent:
            def run_sync(
                self,
                prompt: str,
                *,
                deps: object,
                event_stream_handler: object | None = None,
            ) -> SimpleNamespace:
                return SimpleNamespace(output={"status": "replied"})

        with patch.object(runtime, "build_canonical_agent", return_value=FakeAgent()):
            with self.assertRaises(TypeError):
                runtime.run_ticket_sync(request=self.request, model="fake:model")

    def test_ticket_result_allows_blank_product_area_for_invalid_reply(self) -> None:
        result = TicketResult.model_validate(
            {
                "status": "replied",
                "product_area": "",
                "response": "There is no actionable support request in the ticket.",
                "justification": "The ticket does not ask for product help and no grounded area applies.",
                "request_type": "invalid",
            }
        )
        self.assertEqual(result.product_area, "")

    def test_ticket_result_rejects_blank_product_area_for_grounded_reply(self) -> None:
        with self.assertRaises(ValueError):
            TicketResult.model_validate(
                {
                    "status": "replied",
                    "product_area": "",
                    "response": "Grounded response.",
                    "justification": "Grounded in corpus.",
                    "request_type": "product_issue",
                }
            )

    def test_run_ticket_sync_writes_jsonl_audit_trail_on_success(self) -> None:
        expected = TicketResult(
            status=TicketStatus.REPLIED,
            product_area="community",
            response="Grounded response.",
            justification="Grounded in corpus.",
            request_type=RequestType.PRODUCT_ISSUE,
        )
        usage = RunUsage(input_tokens=1234, output_tokens=210, requests=4, tool_calls=7)

        class FakeAgent:
            def run_sync(
                self,
                prompt: str,
                *,
                deps: object,
                usage_limits: object | None = None,
                event_stream_handler: object | None = None,
            ) -> SimpleNamespace:
                async def emit():
                    yield FunctionToolCallEvent(
                        part=ToolCallPart(
                            tool_name="grep",
                            args={"pattern": "delete account"},
                            tool_call_id="call-1",
                        )
                    )
                    yield FunctionToolResultEvent(
                        result=ToolReturnPart(
                            tool_name="grep",
                            content="Path: hackerrank_community/.../delete-an-account.md",
                            tool_call_id="call-1",
                        )
                    )

                asyncio.run(event_stream_handler(None, emit()))
                return SimpleNamespace(output=expected, usage=lambda: usage)

        with tempfile.TemporaryDirectory() as tmpdir:
            audit_root = Path(tmpdir)
            with patch.object(runtime, "build_canonical_agent", return_value=FakeAgent()):
                result = runtime.run_ticket_sync(
                    request=self.request,
                    model="fake:model",
                    audit_path=audit_root / "ticket-1.jsonl",
                )

            self.assertEqual(result, expected)
            audit_file = audit_root / "ticket-1.jsonl"
            self.assertTrue(audit_file.exists())
            records = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["type"] for record in records], ["ticket", "tool", "final_result"])
            self.assertEqual(records[0]["ticket_id"], "ticket-1")
            self.assertEqual(records[1]["tool_name"], "grep")
            self.assertEqual(records[1]["args"], {"pattern": "delete account"})
            self.assertIn("delete-an-account", records[1]["result_preview"])
            self.assertEqual(records[2]["status"], "replied")
            self.assertEqual(records[2]["product_area"], "community")
            self.assertEqual(
                records[2]["usage"],
                {
                    "input_tokens": 1234,
                    "output_tokens": 210,
                    "requests": 4,
                    "tool_calls": 7,
                },
            )

    def test_run_ticket_sync_writes_jsonl_audit_error_then_reraises(self) -> None:
        class FakeAgent:
            def run_sync(
                self,
                prompt: str,
                *,
                deps: object,
                usage_limits: object | None = None,
                event_stream_handler: object | None = None,
            ) -> SimpleNamespace:
                raise RuntimeError("boom")

        with tempfile.TemporaryDirectory() as tmpdir:
            audit_root = Path(tmpdir)
            with patch.object(runtime, "build_canonical_agent", return_value=FakeAgent()):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    runtime.run_ticket_sync(
                        request=self.request,
                        model="fake:model",
                        audit_path=audit_root / "ticket-1.jsonl",
                    )

            audit_file = audit_root / "ticket-1.jsonl"
            self.assertTrue(audit_file.exists())
            records = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["type"] for record in records], ["ticket", "error"])
            self.assertEqual(records[1]["error_type"], "RuntimeError")
            self.assertEqual(records[1]["message"], "boom")


if __name__ == "__main__":
    unittest.main()
