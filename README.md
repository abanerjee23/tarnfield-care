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

## ⚠️ The corpus costs money while it exists

Vertex AI RAG Engine provisions a managed database that **bills continuously**, and the billing
tier is a **project + location setting — not a property of your corpus**. Deleting the corpus
does *not* stop the meter.

```bash
make rag-status        # what exists, and which tier is billing
make rag-unprovision   # actually halts the bill (destructive, project-wide)
```

Run `make rag-status` before you walk away. A `Stop` hook warns automatically when the tier
is still provisioned, and `/rag-cost` covers the full procedure. See BUILD_PLAN §2.5 and §2.6.

---

## Project Structure

```
customer-chatbot-rag/
├── BUILD_PLAN.md              # Architecture, decisions, costs, build sequence
├── CLAUDE.md                  # AI-assisted development guide
├── Makefile                   # Corpus lifecycle + tests
├── app/
│   ├── agent.py               # Agent definitions
│   ├── config.py              # Models, regions, corpus, session/memory backends
│   ├── fast_api_app.py        # FastAPI backend server
│   └── app_utils/             # App utilities and helpers
├── docs/                      # Policy PDFs ingested into the corpus
│   ├── tarnfield_returns_policy.pdf
│   ├── tarnfield_product_catalogue.pdf     # per-product return overrides
│   └── tarnfield_billing_policy.pdf
├── data/fixtures.json         # Dummy orders + cases (built in BUILD_PLAN 6.4)
├── scripts/
│   ├── rag_corpus.py          # Corpus lifecycle (up/status/down/unprovision)
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
agents-cli install          # install dependencies
make rag-up                 # create the corpus, ingest docs/*.pdf
agents-cli playground       # interactive local testing
make rag-down               # delete the corpus when finished
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
| `make rag-down` | Delete the corpus (does **not** stop the bill) |
| `make rag-unprovision` | Halt RAG Engine billing — destructive, project-wide |
| `make test` | Unit and integration tests |
| `agents-cli playground` | Launch local development environment |
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
