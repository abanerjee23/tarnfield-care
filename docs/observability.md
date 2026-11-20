# Braintrust observability plan

Braintrust is the chosen platform for agent traces and evaluation. Export from
Tarnfield to Braintrust is pending. The current code still has an optional
[legacy Arize exporter](arize-observability.md). Google Cloud Logging and Trace
support deployment and infrastructure diagnostics.

## What we need to see

| Signal | What it helps explain |
|---|---|
| End-to-end turn duration and errors | Where customers waited or a turn failed |
| Model calls, tokens and retries | When usage or cost increases |
| Retrieval outcome and citation validation | Why an answer could be given or had to abstain |
| Session and memory outcomes | Whether history or recall worked without exposing customer content |

Use the existing OpenTelemetry provider for the planned Braintrust export.
Braintrust supports receiving OpenTelemetry spans. Verify how the current ADK
span attributes map into the project before relying on its timing and usage
views. The current workflow performs retrieval and memory in callbacks, so
verify which signals appear in the trace and which need to be read from logs.
Count each model call once and use the root duration to measure a whole turn.
[Braintrust OpenTelemetry integration](https://docs.braintrust.dev/integrations/sdk-integrations/opentelemetry/send-traces-and-logs)

## Verify the integration

1. Use an isolated development project and synthetic turns. Confirm a trace
   reaches Braintrust and that span relationships, latency, usage and error
   categories are visible.
2. Inspect exported spans and a simulated error for customer content. Check
   prompt and reply fields, evidence, memory, tool payloads and error messages.
   Keep those fields out of default exports and verify Google Cloud capture
   separately.
3. Confirm that a collector outage has bounded impact on customer turns and
   that export failures are diagnosable. Repeat trace and privacy checks on the
   managed-state path, then on the deployed customer path when available.

Keep API credentials on the server. Before sending customer data or enabling
online scoring, agree access, retention, deletion, consent, sampling and cost
controls. Set alert owners and thresholds for latency, errors, usage and export
failures as part of release work. Use the
[evaluation guide](evaluation.md#braintrust-offline-workflow) for synthetic
experiments and keep local evaluation reports separate from masked traces.

## Recorded evidence

The earlier multi-agent deployment demonstrated Arize trace delivery and
masking on 1 October 2026. The trace IDs, timings, transport smoke and rollback
notes are in the [legacy tracing guide](arize-observability.md#historical-verification-earlier-multi-agent-deployment).
Braintrust trace delivery, current-path privacy, and online scoring await
verification.
