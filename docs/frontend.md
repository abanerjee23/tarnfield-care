# Tarnfield Care customer preview

## User → problem → experience

A customer asks about returns/exchanges and receives a sourced policy explanation.
The UI offers policy links, conversation history and helpful uncertainty, without
claiming to execute refunds, exchanges or support requests.

Open [Tarnfield Care](http://127.0.0.1:3010). This is a local portfolio preview,
not a public customer release.

## Architecture

Next.js same-origin proxy → FastAPI gateway → current single-agent source.
The gateway defaults to managed Google sessions and Memory Bank; RAG also uses
Google Cloud. It does not invoke the old deployed agent's model workflow.
Credentials remain server-side.

Answers are buffered until the schema and current-turn citation IDs are
validated. The interface receives status/answer/source events via SSE. Source
dialogs show retrieved excerpts and original PDFs. Older historical answers may
show “Referenced policy” rather than imply their evidence was validated anew.

## Run locally

Use Python 3.11–3.13, `uv`, and Node.js 20.9 or later (Node 22 is suitable).
Install dependencies with `uv sync --locked` and `npm --prefix frontend ci`.

For a fresh checkout, copy `.env.example` to `.env` and `.env.local.example` to
`.env.local` without overwriting existing configuration. Set the Google project
and corpus settings in `.env`, and the Gemini key in `.env.local`. Keep Arize
disabled unless its space and key are configured. Authenticate Google ADC with
`gcloud auth application-default login`, then check `make rag-status`. Creating
or importing a corpus uses cloud resources; `make rag-up` ingests the demonstration
PDFs when needed. See [deployment](deployment.md) for managed state configuration.

The frontend defaults match the local gateway. Use `frontend/.env.example` as a
reference for server-only overrides when changing them.
Run `make chat-gateway` and `make chat-ui` in separate terminals.
Use the exact origin `http://127.0.0.1:3010`; localhost is a different origin.

Default managed state reads `deployment_metadata.json` or
`DEPLOYED_AGENT_RUNTIME_ID`. Google Application Default Credentials and the
Gemini API key must be configured. Live questions consume model credits.
Set `CHAT_STATE_BACKEND=local` for standalone SQLite sessions and in-process
memory; local memory does not survive restart.

Secrets go in ignored local overrides, never browser-visible variables.
Match `CHAT_PUBLIC_ORIGIN` and `GATEWAY_ALLOWED_ORIGINS` when changing origin.

## Verification and release

Use the supported Node version and an unused integration-server port:

```bash
uv run pytest tests/unit tests/integration
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

For isolated Python verification, use a clean checkout without local `.env`
overrides, disable Arize export and set `TEST_SERVER_PORT` to an unused port.
Local secret overrides can otherwise enable tracing during instrumentation tests.
See [build report](build-report.md) for dated results and end-to-end evidence.

Public hosting still requires identity/ownership decisions, privacy controls,
distributed request coordination, abuse limits, calibrated quality evaluations,
monitoring and approved deployment. No live cloud resources were retired.
