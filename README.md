# Tarnfield Running Co. — Customer Service Chatbot

A customer service chatbot that answers questions about **returns, exchanges and billing**,
grounded in the company's actual policy documents rather than in what the model happens to
remember about returns policies in general.

Built on Google ADK, deployed to Agent Runtime.

**Three agents.** A root orchestrator that talks to the customer, and two specialists — Returns &
Exchanges and Billing — that do the policy reasoning. Only the root ever speaks to the customer;
only the policy documents can decide an answer.

**Status:** deployed and answering correctly. **Not yet evaluated** — the phase that measures
whether it is actually good has not started.

---

## The three documents

| Document | What it is | Read it when |
|---|---|---|
| **[`BUILD_PLAN.md`](BUILD_PLAN.md)** | The product document. Every decision as Decision → Why → What it costs, plus success criteria, risks, real costs, and what is deliberately missing | **Start here.** It explains the *why* of everything below |
| **[`ENGINEERING_NOTES.md`](ENGINEERING_NOTES.md)** | Implementation detail, SDK traps, the four deploy failures and their causes | You are about to change the code |
| **This file** | How to run it | You want it running |

---

## Quick start

```bash
agents-cli install      # dependencies
make rag-serverless     # one-time: put the project in serverless mode
make rag-up             # create the corpus, ingest docs/*.pdf
make playground         # interactive testing at /dev-ui/?app=app
```

**The corpus must be up before anything works.** With it down, the bot correctly tells you it
cannot check the policy — which looks like a broken bot if you have forgotten.

### Requirements

- **uv** — [install](https://docs.astral.sh/uv/getting-started/installation/)
- **agents-cli** — `uv tool install google-agents-cli`
- **Google Cloud SDK** — [install](https://cloud.google.com/sdk/docs/install), then
  `gcloud auth application-default login`

---

## Cost control: know which RAG mode you are in

RAG Engine's backing store is a **project-wide setting, not a property of your corpus**, so
deleting a corpus never changes it.

| Mode | Cost |
|---|---|
| `basic` / `scaled` | **Provisioned instance, bills continuously** |
| `serverless` | Per use, no standing instance |
| `unprovisioned` | Nothing, and all RAG data is deleted |

**This project runs `serverless`**, and the bill confirms it — there is no RAG line item at all
(BUILD_PLAN §5). It needs `vectorsearch.googleapis.com` enabled, which Terraform now does.

```bash
make rag-status       # corpus contents AND the current mode
make rag-serverless   # the actual cost control — one-time
make rag-unprovision  # deletes all RAG data, project-wide. Destructive
```

A session-end hook warns if the mode ever goes back to a provisioned one, and `/rag-cost` carries
the procedure.

---

## Commands

| Command | What it does |
|---|---|
| `make rag-up` | Create the corpus and ingest `docs/*.pdf` |
| `make rag-status` | Corpus contents **and the billing mode** |
| `make rag-serverless` | Switch to serverless — no standing instance |
| `make rag-down` | Delete the corpus |
| `make rag-unprovision` | Halt RAG Engine entirely — destructive, project-wide |
| `make playground` | Local UI with the same session and memory services as the server |
| `make playground-plain` | ADK defaults, no persistence — for comparison only |
| `make smoke` | Real conversations end to end (spends credits) |
| `make test` | Unit and integration tests |
| `agents-cli eval run` | Run the agent over the eval dataset and grade it |
| `agents-cli deploy` | Deploy to Agent Runtime |

**Use `make playground`, not `agents-cli playground`.** The latter runs with no service flags, so
conversations vanish on restart, there is no memory, and customer details do not carry between
sessions. `make playground` passes them explicitly so local testing matches what runs deployed.

---

## Configuration

Copy `.env.example` to `.env`.

**Read the header of that file before adding anything to it.** The file itself does not ship, but
`agents-cli deploy` turns every line into a deployment environment variable readable by anyone
with project access. So: **no secrets in `.env`** — the API key comes from Secret Manager.

---

## Project structure

```
customer-chatbot-rag/
├── BUILD_PLAN.md           # The product document — decisions, costs, gaps
├── ENGINEERING_NOTES.md    # Implementation detail and deploy traps
├── app/
│   ├── agents.py           # Root + two specialists
│   ├── prompts.py          # Instructions — most safety rules live here
│   ├── tools.py            # Search, lookups, and request_* (human-gated)
│   ├── retrieval.py        # Policy search with per-specialist scoping
│   ├── config.py           # Models, regions, corpus, project resolution
│   ├── callbacks.py        # Writes each conversation to memory
│   └── data/fixtures.json  # Dummy orders, invoices and billing cases
├── docs/                   # The three policy PDFs
├── scripts/                # Corpus lifecycle, smoke runner, PDF generator
├── tests/                  # Unit, integration, eval datasets
└── deployment/terraform/   # Project infrastructure
```

---

## Evaluation

Grading splits across four layers — **routing, retrieval, reasoning, delivery** — so a failure can
be attributed to one fix rather than to a general sense that something is off. See BUILD_PLAN §4
for the methodology and the ten must-have cases.

**The corpus must be up before evaluating.** `make rag-up` → eval → `make rag-down`. Forgetting
produces failures that look like model problems but aren't.

---

## Deployment

```bash
unset GOOGLE_APPLICATION_CREDENTIALS   # agents-cli is external to our credential guard
gcloud config set project <your-project-id>
agents-cli deploy
```

Four things broke on the first deploy and none were reproducible locally. If retrieval comes back
empty on a fresh project, read [`ENGINEERING_NOTES.md §5`](ENGINEERING_NOTES.md) before debugging
— the causes are listed there.

---

## What is deliberately not built

- **No autonomous actions.** Every material action is filed for human approval and returns a
  reference number, never an outcome (BUILD_PLAN 2.11).
- **No real order system.** Lookups read a JSON fixture (2.12).
- **No outcome logging yet.** The `case_outcome` table is designed but not built, which means
  human override rate — the most informative metric in the plan — is currently unmeasurable
  (2.15).
