# Submission Readiness

This note captures the current evaluator-facing state of the repo.

## What is in place

- `code/main.py` is the evaluator-facing batch entry point.
- Environment-based model resolution is wired through `.env` or process env.
- Output writing is atomic and fail-hard.
- The canonical toolset is scoped to `data/`.
- Focused contract/runtime/tool tests are green.
- `code/README.md` documents install, env, run, and test steps.

## AI-fluency trail

The shared log at `~/hackerrank_orchestrate/log.txt` currently shows:

- architecture decisions made before implementation
- explicit correction when earlier assumptions were wrong
- TDD slices with red/green evidence
- live sample evaluation checkpoints
- documented risk tracking rather than silent drift

Current read:

- the trail is credible for "active engineer steering the system"
- the strongest evidence is the repeated contract tightening and test-first
  fixes
- the weakest area is that provider latency makes some live checkpoints look
  stalled from the outside unless the surrounding explanation is read

## Remaining release risk

- semantic quality on real tickets remains the largest release risk
- product-area labeling is still noisy, though this is a softer field than
  status and request type

## Latest full-run checkpoint

- command run:
  - `python code/main.py --input-csv support_tickets/support_tickets.csv --output-csv support_tickets/output.csv`
- current state:
  - the batch run completes and writes `support_tickets/output.csv`
  - per-ticket JSONL audit files are written under `artifacts/sessions/`
  - the output schema matches the evaluator contract:
    `status,product_area,response,justification,request_type`
- current practical risk:
  - the remaining risk is answer quality on specific real tickets, not batch
    completion or file generation

Current release read:

- core contracts and batch operability are in place
- targeted live quality is materially better
- the remaining blocker is semantic quality on hard real-ticket cases
