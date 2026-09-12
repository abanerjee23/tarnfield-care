# customer-chatbot-rag

A customer service chatbot for **Tarnfield Running Co.** that answers questions about returns,
exchanges and billing, grounded in the company's actual policy documents.

Three agents: a root orchestrator that talks to the customer, and two specialists — Returns &
Exchanges and Billing — that do the policy reasoning against a Vertex AI RAG Engine corpus.

> **Read [`BUILD_PLAN.md`](BUILD_PLAN.md) first.** Every architectural choice is recorded there
> as Decision → Why → What it costs us, with an architecture diagram in §3. This README covers
> only how to run things.

Generated with `agents-cli` version `1.5.0`.

---

## ⚠️ Know which RAG Engine mode you are in

RAG Engine's backing store is a **project + location setting, not a property of your corpus**,
so deleting a corpus never changes it:

| Mode | Backing store | Cost |
|---|---|---|
| `basic` / `scaled` | Spanner | **Provisioned instance, bills continuously** |
| `serverless` | Vector Search | Per use, no standing instance |
| `unprovisioned` | none | Nothing, and all RAG data is deleted |

**This project runs `serverless`.** Spanner mode is allowlist-only for new projects in
`us-central1`, `us-east1` and `us-east4`, and serverless has no standing cost — so it is both
the available option and the cheaper one. It needs `vectorsearch.googleapis.com` enabled.

```bash
make rag-status       # corpus contents and the current mode
make rag-serverless   # switch to serverless (the actual cost control)
make rag-unprovision  # delete all RAG data, project-wide. Absolute and destructive
```

A `Stop` hook warns if the mode ever goes back to a provisioned one, and `/rag-cost` covers the
procedure. See BUILD_PLAN §2.5 and §2.6.

---

## Project Structure

```
customer-chatbot-rag/
├── BUILD_PLAN.md              # Architecture, decisions, costs, build sequence
├── CLAUDE.md                  # AI-assisted development guide
├── Makefile                   # Corpus lifecycle + tests
├── app/
│   ├── agent.py               # Entry point
│   ├── agents.py              # Root + two specialists (single_turn)
│   ├── prompts.py             # Instructions; most safety rules live here
│   ├── tools.py               # Search, lookups, and request_* (human-gated)
│   ├── retrieval.py           # Corpus search with per-specialist scoping
│   ├── config.py              # Models, regions, corpus, session/memory backends
│   ├── fast_api_app.py        # FastAPI backend server
│   └── app_utils/             # App utilities and helpers
├── docs/                      # Policy PDFs ingested into the corpus
│   ├── tarnfield_returns_policy.pdf
│   ├── tarnfield_product_catalogue.pdf     # per-product return overrides
│   └── tarnfield_billing_policy.pdf
├── data/fixtures.json         # Dummy orders, invoices and billing cases
├── scripts/
│   ├── rag_corpus.py          # Corpus lifecycle
│   ├── rag_cost_check.sh      # Stop-hook billing warning
│   ├── smoke.py               # End-to-end conversation runner
│   └── make_billing_policy.py # Source text for the billing policy PDF
├── tests/                     # Unit, integration, and eval
└── pyproject.toml
```

## Requirements

- **uv** — [install](https://docs.astral.sh/uv/getting-started/installation/)
- **agents-cli** — `uv tool install google-agents-cli`
- **Google Cloud SDK** — [install](https://cloud.google.com/sdk/docs/install), then
  `gcloud auth application-default login`

## Quick Start

```bash
agents-cli install      # install dependencies
make rag-serverless     # one-time: put the project in serverless mode
make rag-up             # create the corpus, ingest docs/*.pdf
make smoke              # run real conversations end to end
make playground         # interactive local testing at /dev-ui/?app=app
```

## Configuration

Copy `.env.example` to `.env`. Two credential paths must be live at once (BUILD_PLAN §2.9):
`GOOGLE_GENAI_USE_VERTEXAI` switches **model calls only**, while RAG Engine and Agent Engine
always need ADC plus `GOOGLE_CLOUD_PROJECT`. Do not comment that variable out.

## Commands

| Command | What it does |
|---|---|
| `make rag-up` | Create the corpus and ingest `docs/*.pdf` |
| `make rag-status` | Corpus contents **and the billing tier** |
| `make rag-serverless` | Switch to serverless — no standing instance |
| `make rag-down` | Delete the corpus |
| `make rag-unprovision` | Halt RAG Engine billing — destructive, project-wide |
| `make smoke` | Real conversations through the agent (spends credits) |
| `make test` | Unit and integration tests |
| `make playground` | Local UI, with the same session/memory services as the server |
| `make playground-plain` | `agents-cli playground` — ADK defaults, no persistence |
| `agents-cli eval run` | Run the agent over the eval dataset and grade it |
| `agents-cli lint` | Code quality checks |
| `agents-cli deploy` | Deploy to Agent Runtime |
| `agents-cli publish gemini-enterprise` | Register the deployed agent with Gemini Enterprise |

## Regenerating the billing policy

The billing policy PDF is generated from source so wording changes stay diffable:

```bash
uv run --with reportlab python scripts/make_billing_policy.py
```

Re-run `make rag-up` afterwards so the corpus picks up the change.

## Playground

```bash
make playground        # then open http://127.0.0.1:8080/dev-ui/?app=app
```

Use `make playground`, not `agents-cli playground`. The latter runs `adk web` with no service
flags, so it falls back to ADK's in-memory defaults — conversations vanish on restart, there is
no memory service, and `user:` state does not carry between sessions. `make playground` passes
the session and memory services explicitly so what you test locally matches what runs deployed.

## Evaluation

Grading is split across four layers — routing, retrieval, reasoning, delivery — so a failure
can be attributed to one fix rather than a general sense that something is off. See
BUILD_PLAN §4 for the methodology and the must-have cases.

**The corpus must be up before evaluating.** `make rag-up` → eval → `make rag-down`. Forgetting
produces failures that look like model problems but aren't.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

## Observability

Telemetry exports to Cloud Trace, BigQuery and Cloud Logging. Resolved cases emit one
structured `case_outcome` row to BigQuery, keyed by order id — see BUILD_PLAN §2.15.
