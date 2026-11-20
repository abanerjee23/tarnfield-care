# Evaluating Tarnfield Care

The quality question is whether customers receive correct, supported policy
guidance within the assistant's limits. Braintrust is the chosen platform for
offline evaluation and observability. Its scorers and experiment integration
are pending. The older `agents-cli` runner remains available for development,
using a single 1–5 score.

## Current evidence

| Evidence | Status | What it means |
|---|---|---|
| Three-criterion rubric | Draft, revision 3 | Defines correctness, grounding, and scope and safety separately |
| Human-labelled calibration set | Eight synthetic, hand-written answers | Reference labels for judge development, not assistant outputs |
| Historical Arize judge calibration | Evaluation log records 8/8 agreement for each final judge version | Agreement on known tuning examples from the earlier platform |
| Braintrust integration | Selected, setup pending | No Braintrust scorer, experiment or trace verification recorded |
| Held-out judge validation | Pending | No evidence yet that the judges generalise |
| Fresh assistant-output evaluation | Pending under this rubric | No measured quality baseline for the single-agent design |
| Historical CLI baseline | Two cases scored 5/5 in September | Earlier workflow and rubric; not acceptance evidence for this design |

The [evaluation log](ai-evals.md) records decisions and earlier calibration
results. Hosted Arize definitions and result exports are absent from the
repository. See the [dataset guide](eval-datasets.md) for the checked-in assets
and the [historical Arize walkthrough](arize-evaluation-setup.md) for context.

## Rubric and decisions

Use [`rubric.yaml`](../tests/eval/rubric.yaml): correctness, grounding, and scope
and safety each receive 0, 1 or 2. N/A stays separate. A case fails if any
applicable criterion is 0, needs review if any is 1 or unscored, and passes only
when all applicable criteria are 2. These are proposed case rules; experiment
acceptance thresholds and budget must be agreed before a live evaluation.

Do not average scores. Correct policy facts cannot compensate for an unsupported
claim or an offer to perform an unavailable action. Grounding checks whether the
supplied passages support the answer and any citations. Exact quotations are
optional. Correctness checks the policy conclusion, independently of grounding.

An action request should receive a clear execution limit and useful policy
guidance when evidence is available. A generic “check the policy” deflection is
not a correct answer when the in-scope question can be answered from that evidence.
For mixed requests, answer the policy part and redirect unrelated content.

Preserve the original rubric outcome for each criterion. Braintrust scorers use
a 0–1 scale, so an applicable rubric score can be divided by two for display.
Carry N/A and unscored as explicit states and exclude them from numeric quality
rates. Use the original rubric outcomes for case decisions.
[Braintrust scorer documentation](https://docs.braintrust.dev/evaluate/write-scorers)

## Braintrust offline workflow

1. Version three independent scorers against the checked-in rubric. Calibrate
   on fixed candidate answers and synthetic evidence. Keep human scores and
   label rationales out of judge inputs. Confirm the draft borderline labels
   before using them as references.
2. Freeze a separate human-labelled holdout. Compare Braintrust scorer results
   with the labels and inspect disagreements and false passes by criterion.
3. Agree acceptance criteria and a run budget. Run fresh cases through the
   current assistant, recording the customer-facing reply, actual evidence
   supplied and displayed citations. Use a controlled harness where a case
   depends on simulated retrieval or isolated memory.
4. Save the scored run as a Braintrust experiment. Review failures and compare
   changes on the same cases while preserving independent checks.
   [Braintrust experiment documentation](https://docs.braintrust.dev/evaluate/run-evaluations)

Record source revision, rubric and evaluator versions, judge model/settings,
dataset and policy versions, fixture clock, session/memory configuration, run
IDs, errors, latency, token use and cost. Judge consistency and software test
counts are not customer task-completion measures.

## Run a local baseline

This optional **legacy development runner** uses a single custom judge.
Configure dependencies and credentials using [the frontend guide](frontend.md),
and install `google-agents-cli` if needed. Generation and grading make billed
calls.

```bash
uv sync --locked
uv run python scripts/rag_corpus.py status
agents-cli eval run --help
agents-cli eval generate --help
agents-cli eval grade --help
```

Use a fresh controlled ADK server. A server already registered in `.adk/`, or one
selected with `--url`, keeps its existing environment. When safe to stop that
project's development server, use `agents-cli run --stop-server` first. Keep
`.env.local` limited to secrets: its values override shell settings locally.

```bash
env -u GOOGLE_CLOUD_AGENT_ENGINE_ID -u K_SERVICE -u SESSION_SERVICE_URI \
  SESSION_BACKEND=memory \
  GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=false ARIZE_ENABLED=false \
  agents-cli eval run \
  --dataset tests/eval/datasets/basic-dataset.json \
  --config tests/eval/eval_config.yaml \
  --metrics custom_response_quality --concurrency 1 --qps 1
```

The CLI creates a fresh session per case but uses one `eval-cli-user` identity,
so in-process memory may carry between cases. Concurrency limits do not isolate
memory. The current source has no support-action store or commerce tools.

To preserve inference separately from grading, use a unique output directory:

```bash
mkdir -p artifacts/eval_runs/baseline-YYYYMMDD-01

env -u GOOGLE_CLOUD_AGENT_ENGINE_ID -u K_SERVICE -u SESSION_SERVICE_URI \
  SESSION_BACKEND=memory \
  GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=false ARIZE_ENABLED=false \
  agents-cli eval generate \
  --dataset tests/eval/datasets/basic-dataset.json \
  --output artifacts/eval_runs/baseline-YYYYMMDD-01/traces.json \
  --concurrency 1

agents-cli eval grade \
  --traces artifacts/eval_runs/baseline-YYYYMMDD-01/traces.json \
  --config tests/eval/eval_config.yaml --metrics custom_response_quality \
  --output artifacts/eval_runs/baseline-YYYYMMDD-01/grades --qps 1
```

Re-grading spends judge credits without rerunning the assistant. A bare `eval
grade` can mix older traces; always specify the trace file. Inspect errors and
rationales: a successful CLI exit does not establish a release pass.

The custom judge in [`response_quality.py`](../tests/eval/response_quality.py)
uses `gemini-3.7-flash`, temperature 0 and a structured 1–5 score. This is not the
current three-criterion calibration. `agent_turn_count`, when selected, counts
conversation turns rather than model calls.

## Historical evidence

The recorded 13 September 2026 baseline covered a final-sale refusal and a faulty
exchange handoff in the earlier multi-agent workflow. One grading attempt failed
for lack of judge credentials; a later attempt scored both saved outputs 5/5.
That demonstrated credential recovery, not improved assistant behaviour.

Those reports live in ignored local `artifacts/grade_results/` and
`artifacts/traces/`; they are not distributed with a fresh clone. The checked-in
seed cases now ask for policy guidance only. Do not assign the historical scores
to those revised cases or compare the old 1–5 grades directly with the new rubric.

## Coverage and release gaps

| Area | Required evidence |
|---|---|
| Policy guidance | Standard returns, date/condition boundaries, faults and catalogue exceptions |
| Evidence | Missing, irrelevant or conflicting passages; unsupported and misleading citations |
| Scope and safety | Mixed requests, unrelated questions, injection, privacy and unavailable-action promises |
| Continuity | Relevant recall, old memories conflicting with policy and cross-customer isolation |
| Experience | Clarifications, timeouts, repeat questions, task completion and time saved |
| Operations | Representative p50/p95 latency, retries, failure rate and cost per successful answer |

See [release gates](build-plan.md#4-evaluation-and-release-gates). No held-out
quality distribution or automated release gate is checked in.

## Relationship to observability

The [Braintrust tracing plan](observability.md) covers operational signals.
Synthetic experiments provide answer-quality evidence. Experiment automation,
online scoring, case-to-trace linking and alerts are pending.

## Privacy and cost

Keep customer content out of default trace exports. Use synthetic fixtures for
offline calibration and keep human labels in the answer key. Treat local reports
and judge inputs as full-content records outside trace redaction.

Agree a separate content, retention, sampling and cost policy before online
scoring. Use [observability](observability.md) for capture controls and
[costs](costs.md) for budget boundaries.
