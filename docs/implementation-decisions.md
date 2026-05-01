# Implementation Decisions

This file records implementation-time decisions and active risks so they can be
reviewed explicitly instead of disappearing into code diffs.

When in doubt, prefer the same stance used in JACA:

- keep contracts explicit
- keep runtime ownership in Python
- keep tool surfaces narrow
- fail hard instead of adding fallback behavior

## Locked implementation decisions

### 1. Host failures are fail-hard and non-durable

- `code/main.py` does not synthesize fallback output rows.
- A runtime failure aborts the batch.
- Output is written through a temporary file and only replaced on success.
- Partial durable output must not survive a failed batch run.

Why:

- This follows the repo's current fail-hard direction.
- Silent recovery would hide model/runtime failures and produce misleading
  submission artifacts.

### 2. Structured model output is the runtime contract

- The canonical agent returns `TicketResult` directly.
- The host validates and writes the CSV row.
- The host does not parse final state from plain assistant prose.

Why:

- The challenge contract is strict and row-shaped.
- This keeps the model-facing output contract aligned with the evaluator-facing
  output contract.

### 3. Tools are explicit and stateless between calls

- `read`, `grep`, `find`, and `ls` resolve paths from `data_root`.
- There is no remembered cwd between tool calls.
- Evidence tools use breadcrumbed text output; navigation tools stay simpler.

Why:

- This keeps tool calls self-contained and easier to audit.
- It matches the repo's explicit-boundary design and avoids hidden path state.

### 4. Current prompt policy is intentionally small

- The canonical prompt is tool-oriented.
- It requires tools before any grounded reply.
- It allows obvious unsupported, outage-like, invalid, or not-answerable
  tickets to escalate without forced tool calls.
- It encodes grounding, escalation, enum constraints, and response versus
  justification behavior.

Why:

- This follows the JACA pattern of keeping base instructions small and pushing
  as much meaning as possible into contracts and tool/runtime behavior.

### 5. Known-company tickets now narrow the corpus root

- `Claude` tickets use `data/claude`
- `HackerRank` tickets use `data/hackerrank`
- `Visa` tickets use `data/visa`
- `None` stays at the shared `data/` root
- Unknown company labels fail hard

Why:

- This removes an avoidable source of cross-corpus noise when the domain is
  already known from input.
- It still preserves the shared-root path for `None`, where broader inference
  is part of the task.

### 6. Expected tool misuse is wrapped as an explicit model-visible result

- Path/domain mistakes like `ls` on a file path raise a typed operational
  error.
- The canonical toolset wraps those expected failures into an explicit
  `{ok: false, error_type, message}` result instead of crashing the whole run.
- Unexpected exceptions still fail hard.

Why:

- This follows the same JACA stance: expected tool-operational failures are
  part of the tool contract, not host crashes.
- It keeps the runtime strict without forcing a batch abort for recoverable
  tool misuse inside one model run.

### 7. Evidence breadcrumbs now carry an explicit Area line

- `read` and `grep` return breadcrumb blocks with `Path`, `Area`, `Title`,
  and `Section` when available.
- `Area` is derived from the normalized support path, skipping the top-level
  vendor bucket when present.
- The prompt now tells the agent to prefer the breadcrumb `Area` value for
  `product_area` unless multiple sources support a stronger shared area.

Why:

- Live sample runs showed that title/section alone were not stable enough for
  `product_area`.
- This is still a small-contract fix: we improved the evidence contract rather
  than adding post-hoc host normalization.

### 8. `product_area` guidance lives at the evidence and prompt layer

- `read` and `grep` surface an explicit `Area` breadcrumb alongside `Path`,
  `Title`, and `Section`.
- The canonical prompt tells the agent to prefer that `Area` value when it is
  the stable support-domain label for the retrieved evidence.
- `runtime.py` does not rewrite `product_area` after the model returns it.

Why:

- This keeps ticket meaning on the tool-using agent path rather than moving it
  into host-side semantic post-processing.
- It matches the current repo direction: Python owns infrastructure and
  contracts, while the agent owns the ticket decision through tool use.

### 9. Runtime overrides PydanticAI's default request ceiling

- `run_ticket_sync(...)` now passes an explicit `UsageLimits` with
  `request_limit=200`.
- The runtime no longer depends on PydanticAI's default per-run ceiling of
  `50`, which proved too low on the real 29-row submission flow.

Why:

- A real evaluator-facing run failed with `UsageLimitExceeded` at the library
  default before the ticket was complete.
- This is runtime policy, so it belongs in Python rather than being left as an
  implicit third-party default.

### 10. Runtime does not short-circuit ticket meaning

- `run_ticket_sync(...)` does not preflight or short-circuit business meaning
  before the agent runs.
- Ticket meaning is expected to flow through:
  - ticket input
  - canonical agent
  - canonical tools over `data/`
  - structured `TicketResult`

Why:

- This matches the current agreed architecture for the repo.
- It avoids host-side semantic branches that bypass the tool-using agent path.

### 11. Auditability uses one coarse JSONL file per ticket

- Successful and failed ticket runs now write
  `artifacts/sessions/<ticket_id>.jsonl`.
- The audit trail is observability-only, not resumability infrastructure.
- The file contains only coarse records:
  - `ticket`
  - `tool`
  - `final_result`
  - `error`
- Tool records keep the surface small:
  - `tool_name`
  - `args`
  - `result_preview`
- Successful `final_result` records also include a small `usage` object with:
  - `input_tokens`
  - `output_tokens`
  - `requests`
  - `tool_calls`

Why:

- This gives us a durable audit trail for one ticket run without introducing a
  session engine or event-sourcing architecture.
- It matches the repo's current preference for explicit, inspectable runtime
  artifacts over hidden in-memory behavior.

## Live checkpoint

Latest provider-backed checkpoint:

- focused tests: `27/27` passing
- sample batch: `support_tickets/sample_support_tickets.csv`
- exact match score on currently compared fields:
  - `status`: `9 / 10`
  - `product_area`: `2 / 10`
  - `request_type`: `9 / 10`

Observed mismatch pattern:

- The host/runtime seam is behaving correctly.
- The largest miss surface is `product_area` normalization.
- The next miss surface is semantic escalation/invalid classification on a
  small number of tickets.
- The live batch completed successfully, but runtime latency is still high
  enough to treat as a tracked risk.

Latest targeted row work since that checkpoint:

- row 5 was traced end to end through the actual tool-using agent path
- the useful change was at the prompt layer: the agent was told to read top
  level notes and follow prerequisite or linked procedures before answering
- no host-side semantic rewrite was added to make that ticket pass

Current interpretation:

- the main remaining quality work is still agent behavior over retrieved
  evidence, not host-side semantic normalization
- the remaining meaningful unresolved risk is full-batch runtime latency

## Current risks

### 1. `product_area` is still semantically noisy

Current state:

- The runtime now emits an explicit `Area` breadcrumb.
- Exact sample scoring still shows only `2 / 10` `product_area` matches.
- Misses are not random; they cluster around path-shaped labels that are too
  specific or use the wrong abstraction level.

Risk:

- The agent can stay grounded in the right documents and still lose points by
  returning path-flavored labels instead of the expected support-domain label.

Planned action:

- Tighten the product-area instruction and evidence shape on the tool/evidence
  path rather than adding host-side normalization.

### 2. Escalation and invalid-request boundaries are still underfit

Current state:

- The sample run now misses one clear escalation case and one clear invalid
  classification boundary.
- Status and request type both score `9 / 10`, so the issue is narrow rather
  than systemic.

Risk:

- The agent is still slightly too willing to answer from adjacent guidance
  rather than escalating when the corpus support is indirect or when the
  request should be treated as invalid.

Planned action:

- Tighten the prompt on unsupported/outage/fix-my-account style requests and
  invalid-ticket handling, then re-run the live checkpoint.

### 3. Batch latency is a real runtime risk

Current state:

- The latest ten-row sample batch completed successfully.
- The run time was still long enough that it looked hung from the outside
  until completion.

Risk:

- Slow model/tool loops will make iteration and evaluator confidence worse
  even when correctness is acceptable.

Planned action:

- Keep the current correctness-first shape, but treat latency as a first-class
  review item before declaring submission readiness.

### 4. Corpus metadata extraction remains intentionally shallow

Current state:

- Title extraction relies on frontmatter and leading markdown headings.
- Section extraction relies on nearby markdown headings.

Risk:

- Some documents may still not expose the best support-area label through the
  current breadcrumb contract.

Planned action:

- Only deepen metadata extraction if prompt/evidence refinements stop moving
  the sample score.
