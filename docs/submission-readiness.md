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

- full-batch provider-backed runtime latency remains the largest operational
  risk
- semantic quality is much improved on targeted sample rows

## Latest full-run checkpoint

- command attempted:
  - `python code/main.py --input-csv support_tickets/support_tickets.csv --output-csv support_tickets/output.csv`
- first failure found and fixed:
  - PydanticAI default `request_limit=50` caused a real `UsageLimitExceeded`
    failure on the 29-row run
- current blocker after that fix:
  - the full 29-row run no longer fails immediately on request limit, but it
    still does not complete within a practical checkpoint window, so
    evaluator-facing operability is not yet strong

Current release read:

- core contracts and correctness checks are in place
- targeted live quality is materially better
- full submission throughput is still the remaining blocker
