"""Central configuration.

Everything here is a deliberate decision recorded in BUILD_PLAN.md. The section
references in the comments point at the decision that explains *why*, and what
it costs us.
"""

from __future__ import annotations

import os

# --- Models (BUILD_PLAN 2.10) -------------------------------------------------
# Split by job, not by agent seniority. The expensive model does the expensive
# thinking: multi-clause policy judgement about someone's money. The root routes
# and writes the reply, which is formatting work.
#
# These two constants are the ONLY place a model id appears.
# gemini-3.1-pro-preview is a preview model with ~2 weeks of deprecation notice,
# so a forced migration has to be a one-line change.

# Returns & Billing specialists: refund eligibility, multi-clause reasoning.
SPECIALIST_MODEL = "gemini-3.1-pro-preview"

# Root orchestrator: pick a specialist, deliver the answer warmly. It must never
# alter a specialist's ruling -- that constraint is instruction-following under
# pressure, which is exactly where the smaller model is likeliest to slip, so it
# is covered by a must-have eval case (BUILD_PLAN 4).
ROOT_MODEL = "gemini-3.8-flash"

# Retries matter more than usual here: a three-agent turn means ~3x the calls
# against preview-tier rate limits (BUILD_PLAN 2.2).
MODEL_RETRY_ATTEMPTS = 3


# --- Google Cloud (BUILD_PLAN 2.9) --------------------------------------------
# Split billing: model calls go to AI Studio via GEMINI_API_KEY, while RAG Engine
# and Agent Engine are separate clients that still need ADC + this project id.
# Both credential paths must be live at the same time.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")

# Model-serving location. "global" is valid here and is the fix for model 404s.
MODEL_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

# RAG Engine corpus location. Deliberately NOT GOOGLE_CLOUD_LOCATION: "global" is
# a model-serving value, not a valid corpus region. Keeping these separate also
# keeps the retrieval round-trip in a region we chose on purpose.
RAG_CORPUS_LOCATION = os.getenv("RAG_CORPUS_LOCATION", "us-east1")

# The corpus is ephemeral (BUILD_PLAN 2.6) so its ID changes on every rag-up.
# Nothing may hardcode an ID; we look the corpus up by this stable display name.
RAG_CORPUS_DISPLAY_NAME = os.getenv(
    "RAG_CORPUS_DISPLAY_NAME", "customer-service-policies"
)

# One corpus, scoped per specialist in the tool layer (BUILD_PLAN 2.4). A second
# corpus would mean a second standing Spanner bill.
# The returns specialist owns two documents: the policy sets the general rules,
# the catalogue carries per-product overrides ("final sale", "unopened packs
# only") that beat the general rule. Multi-document reasoning is the point.
RETURNS_POLICY_DOCS = [
    os.getenv("RETURNS_POLICY_DOC", "tarnfield_returns_policy.pdf"),
    os.getenv("PRODUCT_CATALOGUE_DOC", "tarnfield_product_catalogue.pdf"),
]
BILLING_POLICY_DOCS = [
    os.getenv("BILLING_POLICY_DOC", "tarnfield_billing_policy.pdf"),
]


# --- Sessions (BUILD_PLAN 2.7) ------------------------------------------------
# SQLite locally, Agent Engine managed sessions once deployed. SQLite is not an
# option in production: Agent Runtime filesystems are ephemeral, so a session DB
# written on one instance may not exist for the next request.
SESSION_BACKEND = os.getenv("SESSION_BACKEND", "sqlite")
SESSION_DB_PATH = os.getenv("SESSION_DB_PATH", "./.sessions/sessions.db")

# Set once deployed; required by BOTH VertexAiSessionService and
# VertexAiMemoryBankService.
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID", "")


# --- Memory (BUILD_PLAN 2.8) --------------------------------------------------
# Separate service from sessions, and a separate job: sessions hold the literal
# event log, memory holds distilled facts about a customer across conversations.
#
# Real memory only exists once deployed -- VertexAiMemoryBankService needs an
# AGENT_ENGINE_ID. The local backend is a non-persistent stand-in that exercises
# the code path but loses everything on restart, so memory-dependent evals are
# not trustworthy locally.
MEMORY_BACKEND = os.getenv("MEMORY_BACKEND", "in_memory")

# Authority order (BUILD_PLAN 2.8): temp: < session state < user: state <
# Memory Bank < policy corpus. Only the corpus may decide a ruling. Memory
# changes how we speak to a customer and what we offer next, never the answer.
#
# user: state is the system of record for anything we can name in advance -- it
# is exact, deletable, and works locally with no AGENT_ENGINE_ID. Memory Bank
# covers only what no key could have been declared for in advance.
