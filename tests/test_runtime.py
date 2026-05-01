from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import runtime  # noqa: E402
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
                self.calls: list[tuple[str, object]] = []

            def run_sync(self, prompt: str, *, deps: object) -> SimpleNamespace:
                self.calls.append((prompt, deps))
                return SimpleNamespace(output=expected)

        fake_agent = FakeAgent()
        with patch.object(runtime, "build_canonical_agent", return_value=fake_agent):
            result = runtime.run_ticket_sync(request=self.request, model="fake:model")

        self.assertEqual(result, expected)
        self.assertEqual(len(fake_agent.calls), 1)
        prompt, deps = fake_agent.calls[0]
        self.assertEqual(prompt, runtime.build_ticket_prompt(self.request))
        self.assertEqual(deps.data_root, self.request.data_root)
        self.assertEqual(deps.ticket_id, self.request.ticket_id)
        self.assertEqual(deps.company, self.request.company)

    def test_run_ticket_sync_fails_hard_on_non_ticket_result_output(self) -> None:
        class FakeAgent:
            def run_sync(self, prompt: str, *, deps: object) -> SimpleNamespace:
                return SimpleNamespace(output={"status": "replied"})

        with patch.object(runtime, "build_canonical_agent", return_value=FakeAgent()):
            with self.assertRaises(TypeError):
                runtime.run_ticket_sync(request=self.request, model="fake:model")


if __name__ == "__main__":
    unittest.main()
