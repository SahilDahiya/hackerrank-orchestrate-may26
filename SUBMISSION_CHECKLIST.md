# Submission Checklist

This repo's local submission contract requires three files:

1. `code.zip`
2. `support_tickets/output.csv`
3. `~/hackerrank_orchestrate/log.txt`

## 1. Code zip

Zip only the `code/` directory contents needed to run the agent.

Exclude:
- virtualenvs
- `node_modules`
- build artifacts
- `data/`
- `support_tickets/`

Suggested command from repo root:

```bash
zip -r code.zip code
```

## 2. Predictions CSV

Required path:

```text
support_tickets/output.csv
```

Required header:

```csv
status,product_area,response,justification,request_type
```

Before submission:
- confirm the file exists
- confirm the header matches exactly
- confirm it contains one row per ticket in `support_tickets/support_tickets.csv`

Quick check:

```bash
python3 - <<'PY'
import csv
from pathlib import Path
out = Path("support_tickets/output.csv")
with out.open(newline="", encoding="utf-8") as f:
    rows = list(csv.reader(f))
print("rows:", len(rows))
print("header:", ",".join(rows[0]))
PY
```

## 3. Chat transcript

Required path on Linux/macOS:

```text
$HOME/hackerrank_orchestrate/log.txt
```

Quick check:

```bash
ls -l "$HOME/hackerrank_orchestrate/log.txt"
```

## Final pre-submit checks

- `code.zip` exists
- `support_tickets/output.csv` exists and has the exact five-column header
- `log.txt` exists
- no secrets are committed to the repo
- `code/README.md` explains install + run
