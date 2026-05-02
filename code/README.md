# Support Agent

This directory contains the HackerRank Orchestrate challenge solution.

## Current shape

- `main.py` is the evaluator-facing batch CLI.
- `runtime.py` runs one ticket at a time.
- `agent.py` builds the canonical PydanticAI agent.
- `tool_registry.py` exposes the scoped read-only corpus tools.
- `schemas.py` defines the runtime and final-output contracts.
- `audit.py` writes a minimal per-ticket JSONL audit trail.

## Install

From the repo root:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r code/requirements.txt
```

## Environment

Read secrets from environment variables only.

Supported provider env:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

Optional:

- `ORCHESTRATE_MODEL` to override the default model selection

You may also place these in a repo-root `.env` file. `main.py` will load that
file at runtime unless `--dotenv` points elsewhere.

## Run

Run the challenge input:

```bash
.venv/bin/python code/main.py \
  --input-csv support_tickets/support_tickets.csv \
  --output-csv support_tickets/output.csv
```

Run the sample input:

```bash
.venv/bin/python code/main.py \
  --input-csv support_tickets/sample_support_tickets.csv \
  --output-csv /tmp/sample-output.csv
```

Use an explicit model:

```bash
.venv/bin/python code/main.py \
  --model openai:gpt-4.1-mini \
  --input-csv support_tickets/support_tickets.csv \
  --output-csv support_tickets/output.csv
```

## Test

Focused tests:

```bash
.venv/bin/python -m unittest \
  tests.test_main \
  tests.test_tools \
  tests.test_runtime \
  tests.test_agent_contracts \
  tests.test_model_resolver \
  tests.test_tool_errors
```

## Current behavior notes

- The host is fail-hard. It does not synthesize fallback rows.
- Output is written atomically through a temporary file and replaced only on
  full success.
- Known company labels narrow the corpus root:
  - `Claude` -> `data/claude`
  - `HackerRank` -> `data/hackerrank`
  - `Visa` -> `data/visa`
- `None` and unexpected company labels stay at the shared `data/` root.
- Tools are read-only and explicit:
  - `read(path, offset, limit)`
  - `grep(pattern, path, ignore_case, literal, limit)`
  - `find(pattern, path=None)`
  - `ls(path=None)`
- The runtime does not apply host-side semantic post-processing to ticket
  meaning.
- Each ticket run writes a coarse JSONL audit file under
  `artifacts/sessions/<timestamp>__<input_csv_stem>__<ticket_id>.jsonl` with:
  - one `ticket` record
  - zero or more `tool` records
  - one `final_result` or `error` record
- Successful `final_result` records include a small `usage` object with:
  - `input_tokens`
  - `output_tokens`
  - `requests`
  - `tool_calls`
