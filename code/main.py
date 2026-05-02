from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from model_resolver import load_dotenv_file, resolve_model_name
from runtime import run_ticket_sync
from schemas import RunTicketRequest, TicketResult

AUDIT_ROOT = Path("artifacts/sessions")
OUTPUT_FIELDNAMES = [
    "status",
    "product_area",
    "response",
    "justification",
    "request_type",
]

COMPANY_DATA_DIRS = {
    "Claude": "claude",
    "HackerRank": "hackerrank",
    "Visa": "visa",
}


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
    company = (row.get("Company") or "").strip() or "None"
    scoped_root = resolve_ticket_data_root(data_root=data_root, company=company)
    return RunTicketRequest(
        ticket_id=f"ticket-{row_index}",
        company=company,
        subject=(row.get("Subject") or "").strip() or "(no subject)",
        issue=(row.get("Issue") or "").strip(),
        data_root=scoped_root,
    )


def resolve_ticket_data_root(*, data_root: Path, company: str) -> Path:
    normalized = company.strip()
    if not normalized or normalized == "None":
        return data_root
    try:
        return data_root / COMPANY_DATA_DIRS[normalized]
    except KeyError:
        return data_root


def row_from_result(result: TicketResult) -> dict[str, str]:
    return {
        "status": result.status.value,
        "product_area": result.product_area,
        "response": result.response,
        "justification": result.justification,
        "request_type": result.request_type.value,
    }


def build_audit_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def audit_path_for_ticket(
    *,
    audit_root: Path,
    input_csv: Path,
    run_id: str,
    ticket_id: str,
) -> Path:
    return audit_root / f"{run_id}__{input_csv.stem}__{ticket_id}.jsonl"


def run_batch(
    *,
    input_csv: Path,
    output_csv: Path,
    data_root: Path,
    model_name: str,
    audit_root: Path = AUDIT_ROOT,
) -> None:
    with input_csv.open(newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)

    run_id = build_audit_run_id()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_csv.with_suffix(output_csv.suffix + ".tmp")
    try:
        with temp_output.open("w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
            writer.writeheader()

            for row_index, row in enumerate(rows, start=1):
                request = build_request(row=row, row_index=row_index, data_root=data_root)
                result = run_ticket_sync(
                    request=request,
                    model=model_name,
                    audit_path=audit_path_for_ticket(
                        audit_root=audit_root,
                        input_csv=input_csv,
                        run_id=run_id,
                        ticket_id=request.ticket_id,
                    ),
                )
                writer.writerow(row_from_result(result))
        temp_output.replace(output_csv)
    except Exception:
        if temp_output.exists():
            temp_output.unlink()
        raise


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
        audit_root=AUDIT_ROOT.resolve(),
    )


if __name__ == "__main__":
    main()
