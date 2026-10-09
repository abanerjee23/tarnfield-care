# Cost and measurement

The aim is useful, supported guidance at a predictable cost per successful
answer. The single-agent design has no representative cost baseline yet.

## Current cost drivers

| Component | What to measure |
|---|---|
| Gemini 3.8 Flash | Input/output tokens, thinking where billed, retries and longer histories |
| Google Cloud RAG | Ingestion, embeddings, storage and retrieval; inspect region and billing mode |
| Managed sessions and Memory Bank | Stored history, retention, recall and memory generation |
| Agent hosting | Runtime compute, cold starts and scaling after release |
| Arize AX | Trace volume, retention, account plan and offline judge usage |
| Evaluation | Judge model, cases, repetitions, failures and re-grading |
| Supporting services | Secrets, build artifacts and native Cloud logging/trace |
| Public frontend | Hosting choice and traffic; not yet deployed |

Model calls use the Gemini Developer API; retrieval and managed state use Google
Cloud. Keep these billing paths separate. One intended model response is not a
fixed price per turn: retries, context length and memory work still matter.

Existing legacy Cloud Run and Firestore resources may continue to cost money,
even though the current source does not use them. Inventory them and obtain
retirement approval after replacement and rollback verification.

## What has been recorded

Two local single-agent smoke turns took 5.7s and 4.4s, with 3,893 and 3,949 total
tokens respectively. These totals are not enough to calculate a bill without
input/output breakdowns, applicable rates and service usage.

For historical context, the earlier deployed multi-agent trace
`ee18fb93d34d639e485828b08573974e` recorded four model calls, 11,424 tokens,
35.14 seconds and an Arize model-cost estimate of $0.019899. That estimate is not
an invoice, a current-design cost, or a matched before/after comparison.

## Measurement plan

Record cost per successful answer, including failed turns and retries, alongside
correctness, grounding, scope failures and customer task completion. Measure
p50/p95 time to first useful text and completed response on representative cases.

Count each eligible model call once. Do not add native duplicate spans or parent
aggregates. Track evaluation costs separately from customer inference; the
legacy CLI judge runs outside the automatic ADK trace integration.

For model spend, multiply input and billable output tokens by their applicable
rates, including thinking and caching only as billed. Verify current account
rates before budgeting; use provider bills to reconcile estimates. Do not infer
free service from a small demo or scale-to-zero configuration.

For a live experiment, agree cases × repetitions × expected inference and judge
usage first. Preserve outputs so unchanged answers can be regraded without
regenerating them. Deterministic unit checks do not measure billed behaviour;
live smoke tests use cloud services and may write managed session/memory data.

## Operational controls

Use `make rag-status` to inspect both the corpus and project/location billing
mode. Deleting a corpus alone does not unprovision a basic RAG instance; project-wide
mode changes require deliberate review.

Budget alerts, per-user quotas, quality/cost alert thresholds and routine billing
ownership remain release work. Trace delivery does not configure these controls.
See [evaluation](evaluation.md), [observability](observability.md) and
[deployment](deployment.md).
