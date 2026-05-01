from __future__ import annotations

import argparse
import csv
from pathlib import Path

from model_resolver import load_dotenv_file, resolve_model_name
from runtime import run_ticket_sync
from schemas import RunTicketRequest, TicketResult

OUTPUT_FIELDNAMES = [
    "status",
    "product_area",
    "response",
    "justification",
    "request_type",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the HackerRank Orchestrate support agent over a ticket CSV."
    )
    parser.add_argument(
        "--input-csv",
        default="support_tickets/support_tickets.csv",
        help="Input CSV path. Defaults to support_tickets/support_tickets.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="support_tickets/output.csv",
        help="Output CSV path. Defaults to support_tickets/output.csv",
    )
    parser.add_argument(
        "--data-root",
        default="data",
        help="Support corpus root. Defaults to data",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional explicit PydanticAI model path, e.g. openai:gpt-4.1-mini",
    )
    parser.add_argument(
        "--dotenv",
        default=".env",
        help="Optional dotenv file path to preload env vars from. Defaults to .env",
    )
    return parser.parse_args()


def build_request(
    *,
    row: dict[str, str],
    row_index: int,
    data_root: Path,
) -> RunTicketRequest:
    return RunTicketRequest(
        ticket_id=f"ticket-{row_index}",
        company=(row.get("Company") or "").strip() or "None",
        subject=(row.get("Subject") or "").strip() or "(no subject)",
        issue=(row.get("Issue") or "").strip(),
        data_root=data_root,
    )


def row_from_result(result: TicketResult) -> dict[str, str]:
    return {
        "status": result.status.value,
        "product_area": result.product_area,
        "response": result.response,
        "justification": result.justification,
        "request_type": result.request_type.value,
    }


def run_batch(
    *,
    input_csv: Path,
    output_csv: Path,
    data_root: Path,
    model_name: str,
) -> None:
    with input_csv.open(newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_csv.with_suffix(output_csv.suffix + ".tmp")
    with temp_output.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()

        for row_index, row in enumerate(rows, start=1):
            request = build_request(row=row, row_index=row_index, data_root=data_root)
            result = run_ticket_sync(request=request, model=model_name)
            writer.writerow(row_from_result(result))
    temp_output.replace(output_csv)


def main() -> None:
    args = parse_args()
    load_dotenv_file(Path(args.dotenv))
    model_name = resolve_model_name(explicit_model=args.model)

    input_csv = Path(args.input_csv).resolve()
    output_csv = Path(args.output_csv).resolve()
    data_root = Path(args.data_root).resolve()

    run_batch(
        input_csv=input_csv,
        output_csv=output_csv,
        data_root=data_root,
        model_name=model_name,
    )


if __name__ == "__main__":
    main()
