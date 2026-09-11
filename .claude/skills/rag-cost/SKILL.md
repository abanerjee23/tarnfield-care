---
name: rag-cost
description: Check and control what Vertex AI RAG Engine is costing this project — read the billing tier, bring the policy corpus up or down, and halt billing safely. Use when the user asks about RAG cost, wants to stop the corpus bill, is finishing a work session, asks "is anything still running / billing", or says they are done for the day.
---

# RAG Engine cost control

## The one thing to know

**The billing tier is a project + location singleton, not a property of the corpus.**

`make rag-down` deletes the corpus and **leaves the meter running**. This was verified
against `gemini-enterprise-learning`, which reported `Tier: Basic` while holding no corpus
at all. Only `make rag-unprovision` stops the bill.

If the user thinks deleting the corpus stopped the cost, correct that.

## Commands

| Command | What it does | Stops the bill? |
|---|---|---|
| `make rag-status` | Corpus contents **and** the billing tier | — |
| `make rag-up` | Create the corpus, ingest `docs/*.pdf` | — |
| `make rag-down` | Delete the corpus | **No** |
| `make rag-unprovision` | Set the tier to `Unprovisioned` | **Yes** |

## Reading the status

```
Tier     : Basic          <- billing right now
Tier     : Unprovisioned  <- not billing, the goal state when idle
Tier     : unknown (...)  <- API unreachable; do not claim either way
```

## Procedure

**When asked what it's costing:** run `make rag-status`. Report the tier first, the corpus
second — the tier is the part that bills. If the tier is `Basic` and no corpus exists, say so
plainly: money is being spent on nothing.

**When the user is done working:**
1. `make rag-status` to see the current state.
2. If the tier is provisioned, recommend `make rag-unprovision`.
3. **Do not run it for them without explicit confirmation.** It is destructive project-wide —
   it deletes *all* RAG Engine data in that project and location, not just this project's
   corpus. The script requires typing the region to confirm; let the user type it.

**When resuming work:** `make rag-up`. If the tier was unprovisioned, the first `rag-up`
re-provisions it and starts billing again. Say that out loud so it is a choice, not a surprise.

## The automatic reminder

A `Stop` hook (`.claude/settings.json` → `scripts/rag_cost_check.sh`) warns when the tier is
still provisioned. It is throttled to once per 30 minutes and runs async, so it neither slows
turns nor nags. Run `./scripts/rag_cost_check.sh --force` to check immediately.

If the user wants to silence it, change the hook rather than deleting the script — the check
is the only thing standing between them and a bill for an idle index.

## Open question this does not answer

Nobody has yet put a dollar figure on 100 Spanner processing units per month. That is open
question #3 in `BUILD_PLAN.md`, and it determines how much discipline this actually warrants —
$8/month and $80/month imply different habits. Google's pricing calculator settles it.
