from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import main  # noqa: E402
from schemas import RunTicketRequest, TicketResult, TicketStatus, RequestType  # noqa: E402


class MainBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data_root = Path("data").resolve()

    def test_run_batch_does_not_write_partial_output_when_runtime_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_csv = tmp_path / "input.csv"
            output_csv = tmp_path / "output.csv"
            with input_csv.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["Issue", "Subject", "Company"])
                writer.writeheader()
                writer.writerow(
                    {
                        "Issue": "First issue",
                        "Subject": "First subject",
                        "Company": "Claude",
                    }
                )
                writer.writerow(
                    {
                        "Issue": "Second issue",
                        "Subject": "Second subject",
                        "Company": "Visa",
                    }
                )

            call_count = 0

            def fake_run_ticket_sync(
                *,
                request: RunTicketRequest,
                model: str,
                audit_path: Path | None = None,
            ) -> TicketResult:
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise RuntimeError("boom")
                return TicketResult.model_validate(
                    {
                        "status": "replied",
                        "product_area": "Claude Code",
                        "response": "Grounded response.",
                        "justification": "Grounded in local corpus.",
                        "request_type": "product_issue",
                    }
                )

            with patch.object(main, "run_ticket_sync", side_effect=fake_run_ticket_sync):
                with self.assertRaises(RuntimeError):
                    main.run_batch(
                        input_csv=input_csv,
                        output_csv=output_csv,
                        data_root=self.data_root,
                        model_name="fake:model",
                    )

            self.assertFalse(output_csv.exists(), "batch failure should not leave durable output")
            self.assertFalse(
                output_csv.with_suffix(".csv.tmp").exists(),
                "batch failure should not leave a partial temp output behind",
            )

    def test_ticket_result_accepts_canonical_string_values(self) -> None:
        result = TicketResult.model_validate(
            {
                "status": "replied",
                "product_area": "Claude Code",
                "response": "Grounded response.",
                "justification": "Grounded in local corpus.",
                "request_type": "product_issue",
            }
        )
        self.assertEqual(result.status, TicketStatus.REPLIED)
        self.assertEqual(result.request_type, RequestType.PRODUCT_ISSUE)

    def test_build_request_scopes_known_company_to_company_subtree(self) -> None:
        request = main.build_request(
            row={
                "Issue": "Issue body",
                "Subject": "Subject text",
                "Company": "Claude",
            },
            row_index=1,
            data_root=self.data_root,
        )
        self.assertEqual(request.company, "Claude")
        self.assertEqual(request.data_root, self.data_root / "claude")

    def test_build_request_keeps_none_company_at_shared_root(self) -> None:
        request = main.build_request(
            row={
                "Issue": "Issue body",
                "Subject": "Subject text",
                "Company": "None",
            },
            row_index=2,
            data_root=self.data_root,
        )
        self.assertEqual(request.company, "None")
        self.assertEqual(request.data_root, self.data_root)

    def test_build_request_keeps_unknown_company_label_at_shared_root(self) -> None:
        request = main.build_request(
            row={
                "Issue": "Issue body",
                "Subject": "Subject text",
                "Company": "Acme",
            },
            row_index=3,
            data_root=self.data_root,
        )
        self.assertEqual(request.company, "Acme")
        self.assertEqual(request.data_root, self.data_root)

    def test_audit_path_for_ticket_flattens_sessions_into_one_directory(self) -> None:
        input_csv = Path("/tmp/sample_support_tickets.csv")
        audit_path = main.audit_path_for_ticket(
            audit_root=main.AUDIT_ROOT,
            input_csv=input_csv,
            run_id="20260501T154233Z",
            ticket_id="ticket-7",
        )
        self.assertEqual(
            audit_path,
            main.AUDIT_ROOT / "20260501T154233Z__sample_support_tickets__ticket-7.jsonl",
        )


if __name__ == "__main__":
    unittest.main()
