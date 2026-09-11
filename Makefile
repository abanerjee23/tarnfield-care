# Corpus lifecycle (BUILD_PLAN 2.6).
# The corpus is ephemeral: bring it up to work, tear it down to stop the bill.

.PHONY: rag-up rag-down rag-status rag-unprovision test lint

rag-up:        ## Create the corpus and ingest docs/*.pdf
	uv run python scripts/rag_corpus.py up

rag-status:    ## Show corpus contents and the billing tier
	uv run python scripts/rag_corpus.py status

rag-down:      ## Delete the corpus (see rag-unprovision to halt billing)
	uv run python scripts/rag_corpus.py down

rag-unprovision: ## Halt RAG Engine billing. Destructive, project-wide.
	uv run python scripts/rag_corpus.py unprovision

test:          ## Unit and integration tests
	uv run pytest tests/unit tests/integration

lint:
	agents-cli lint
