# Engineering notes

This document describes the current single-agent source. The older multi-agent
and reviewer implementation remains recoverable in Git history. Cloud resources
from that implementation are listed separately in [deployment](deployment.md).

## Request path

The Next.js same-origin proxy forwards permitted routes to `app/chat_gateway.py`.
The gateway runs `app.agent` locally through an ADK `Runner`; it does not call the
older deployed model workflow. Credentials stay server-side.

`app/guardrails.py` classifies the request before generation. Recognised unrelated
questions, greetings and ambiguous questions receive deterministic responses.
Policy and action requests retrieve current evidence with a 12-second retrieval
budget. Missing evidence returns an uncertainty response without a model call.
Action requests also receive an explicit execution-limit notice.

The model is `gemini-3.8-flash` with retry attempts configured to two. Retrieved
evidence and bounded memory recall are supplied before one intended response.
There are no specialist agents or action tools. `app/tools.py` supplies synthetic
order facts and scoped policy context before generation.

## Evidence and answer validation

Retrieval resolves the corpus by display name and permits only the configured
returns-policy and product-catalogue documents. The distance threshold removes
obvious mismatches; a returned passage does not prove that the question is answered.

The model returns structured JSON. Application checks reject malformed output,
unknown citation IDs, in-scope answers without citations, model-written source
links and recognised action claims or promises. Source links are generated from
retrieved document names, and excerpts remain available in session state.

These checks verify citation identity, not semantic support. The model prompt,
quality judges and human review must address irrelevant or contradictory evidence.
Pattern-based scope and action checks are incomplete, especially for paraphrases
and mixed intents; see the [evaluation coverage](evaluation.md#coverage-and-release-gaps).

The gateway buffers the answer until validation, then sends status/answer/source
events. It does not display unchecked model tokens. Older conversation messages
may show a referenced-policy link without implying current-turn verification.

## Sessions and memory

The gateway defaults to managed Google sessions and Memory Bank, using
`DEPLOYED_AGENT_RUNTIME_ID` or ignored deployment metadata. `CHAT_STATE_BACKEND=local`
selects local development services. Standalone ADK runners use the shared service
factory: an explicit session URI, then runtime-managed sessions when an engine ID
exists, then SQLite or in-memory sessions according to configuration.

Memory recall has a two-second budget; writes have a three-second budget. Recall
is optional and cannot override current policy. Writes extract selected sample
order, item and issue details from in-scope messages. Full messages still live in
session history; selective memory is not blanket redaction of stored conversations.
Local in-process memory does not survive a restart. Managed recall and customer
isolation need separate verification.

ADK invokes callbacks by keyword: keep the parameter name `callback_context`.
Memory is appended directly to the model request in the before-model callback.

## Identity and failure handling

The gateway uses a signed HttpOnly visitor cookie and checks conversation
ownership. The proxy checks origin and allowed routes, limits request size and
keeps browser credentials separate from cloud credentials. Anonymous continuity
does not authenticate a customer or authorise a real order lookup.

A process-local guard prevents overlapping turns for a visitor/conversation.
A shared coordination store and abuse quotas are needed before multi-instance
hosting. Stop cancels browser display, not guaranteed server execution; reload
history before resending after an interruption.

Default gateway timeouts are 30 seconds for API operations and 120 seconds per
turn; the frontend proxy waits up to 150 seconds. These are failure bounds, not
the proposed eight-second product latency target.

## Configuration and observability

`.env` holds non-secret settings. `.env.local` is an ignored local secret override
and is not loaded in Agent Runtime. Model calls use the Gemini Developer API;
RAG and managed services require Google ADC. Project resolution falls back to ADC
because the deployed runtime does not expose the local project variable in the
same way. The RAG region is separate from the model-serving location.

The automatic Arize exporter reuses the existing tracer provider and filters to
OpenInference ADK spans to avoid duplicate native model usage. It masks content
and error payloads by default. Google-native capture has separate controls.
Export buffering, timeout and acceptance diagnostics reduce request overhead but
do not guarantee lossless delivery. See [observability](observability.md).

The A2A adapter retains its legacy event converter for compatibility; its earlier
live verification belongs to the old deployed workflow. Recheck deployed
interfaces after any approved release. Deterministic integration checks do not
replace live model, retrieval or managed-memory validation.
