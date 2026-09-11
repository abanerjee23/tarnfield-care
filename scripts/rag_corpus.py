"""Create, inspect and tear down the policy corpus.

The corpus is ephemeral by design (BUILD_PLAN 2.6): bring it up to build,
evaluate or demo, tear it down afterwards so it stops billing.

    uv run python scripts/rag_corpus.py up
    uv run python scripts/rag_corpus.py status
    uv run python scripts/rag_corpus.py down

Nothing here hardcodes a corpus ID. IDs change on every `up`, so the corpus is
always resolved by its stable display name (BUILD_PLAN 2.6).

SDK note: this uses `vertexai.rag`, which is GA but carries a deprecation
warning pointing at the newer `agentplatform` client. That client is still
marked experimental, so we stay on the stable-but-deprecated path for now. All
SDK calls live in this one file, so migrating is a contained change.
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*vertexai.rag.*deprecated.*")

import vertexai  # noqa: E402
from vertexai import rag  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
CONFIG_NAME = (
    f"projects/{config.PROJECT_ID}/locations/"
    f"{config.RAG_CORPUS_LOCATION}/ragEngineConfig"
)


def _init() -> None:
    if not config.PROJECT_ID:
        sys.exit("GOOGLE_CLOUD_PROJECT is not set. See .env.")

    # A stale GOOGLE_APPLICATION_CREDENTIALS pointing at a deleted key file makes
    # ADC fail with a confusing traceback rather than falling back to gcloud
    # credentials. Ignore it when the file is gone (BUILD_PLAN 6.1).
    stale = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if stale and not Path(stale).exists():
        print(
            f"warning: GOOGLE_APPLICATION_CREDENTIALS points at a missing file\n"
            f"         ({stale})\n"
            f"         Ignoring it and falling back to gcloud ADC.",
            file=sys.stderr,
        )
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    # RAG Engine needs a real region. GOOGLE_CLOUD_LOCATION is deliberately not
    # used here -- "global" is a model-serving value, not a corpus region.
    vertexai.init(project=config.PROJECT_ID, location=config.RAG_CORPUS_LOCATION)


def _find_corpus():
    """Resolve our corpus by display name, or None."""
    for corpus in rag.list_corpora():
        if corpus.display_name == config.RAG_CORPUS_DISPLAY_NAME:
            return corpus
    return None


def _policy_pdfs() -> list[Path]:
    pdfs = sorted(p for p in DOCS_DIR.glob("*.pdf") if not p.name.startswith("."))
    if not pdfs:
        sys.exit(f"No PDFs found in {DOCS_DIR}. Drop the policy documents there first.")
    return pdfs


def _tier_name() -> str:
    """Which RagManagedDb tier the project+location is on.

    This is what actually bills, and it is a project-level singleton -- not a
    property of our corpus. See `down`.
    """
    try:
        cfg = rag.get_rag_engine_config(name=CONFIG_NAME)
    except Exception as exc:  # noqa: BLE001 - surfaced, not swallowed
        return f"unknown ({type(exc).__name__})"
    tier = getattr(getattr(cfg, "rag_managed_db_config", None), "tier", None)
    return type(tier).__name__ if tier is not None else "Basic (default)"


def up(args: argparse.Namespace) -> None:
    _init()
    pdfs = _policy_pdfs()

    corpus = _find_corpus()
    if corpus is None:
        print(f"Creating corpus '{config.RAG_CORPUS_DISPLAY_NAME}' ...")
        corpus = rag.create_corpus(
            display_name=config.RAG_CORPUS_DISPLAY_NAME,
            description=(
                "Tarnfield customer service policy documents. "
                "Ephemeral -- see BUILD_PLAN 2.6."
            ),
        )
    else:
        print(f"Corpus already exists: {corpus.name}")

    existing = {f.display_name for f in rag.list_files(corpus_name=corpus.name)}

    for pdf in pdfs:
        if pdf.name in existing:
            print(f"  = {pdf.name} (already ingested)")
            continue
        print(f"  + {pdf.name} ...", flush=True)
        # display_name is what the retrieval tools scope on (BUILD_PLAN 2.4),
        # so it must stay equal to the filename in .env.
        rag.upload_file(
            corpus_name=corpus.name,
            path=str(pdf),
            display_name=pdf.name,
        )

    print(f"\nCorpus ready: {corpus.name}")
    print(f"Billing tier: {_tier_name()}  <-- this is what costs money")
    print("Run `make rag-down` when you stop working.")


def status(args: argparse.Namespace) -> None:
    _init()
    corpus = _find_corpus()
    print(f"Project  : {config.PROJECT_ID}")
    print(f"Location : {config.RAG_CORPUS_LOCATION}")
    print(f"Tier     : {_tier_name()}")

    if corpus is None:
        print(f"Corpus   : '{config.RAG_CORPUS_DISPLAY_NAME}' does not exist")
        print("\nNote: no corpus does NOT mean no bill. The RagManagedDb tier")
        print("above is project-wide and bills independently. See `make rag-down`.")
        return

    print(f"Corpus   : {corpus.name}")
    files = list(rag.list_files(corpus_name=corpus.name))
    print(f"Files    : {len(files)}")
    for f in files:
        print(f"  - {f.display_name}")


def down(args: argparse.Namespace) -> None:
    _init()
    corpus = _find_corpus()
    if corpus is None:
        print(f"No corpus named '{config.RAG_CORPUS_DISPLAY_NAME}'. Nothing to delete.")
    else:
        print(f"Deleting {corpus.name} ...")
        rag.delete_corpus(name=corpus.name)

    print(f"\nRagManagedDb tier is still: {_tier_name()}")
    print(
        "\nDeleting the corpus does not by itself unprovision the RAG Engine\n"
        "managed database. The tier is a project+location singleton and is what\n"
        "bills continuously. To halt it, run:\n\n"
        "    make rag-unprovision\n\n"
        "That is destructive beyond this project: it deletes ALL RAG Engine data\n"
        f"in {config.PROJECT_ID} / {config.RAG_CORPUS_LOCATION}, not just our corpus."
    )


def unprovision(args: argparse.Namespace) -> None:
    _init()
    target = f"{config.PROJECT_ID} / {config.RAG_CORPUS_LOCATION}"
    print(
        "This sets the RAG Engine managed DB tier to Unprovisioned.\n"
        f"It deletes ALL RAG Engine data in {target} -- every corpus in that\n"
        "location, including any not created by this project. It cannot be undone."
    )
    if not args.yes:
        if input(f"\nType the location to confirm ({config.RAG_CORPUS_LOCATION}): ").strip() != (
            config.RAG_CORPUS_LOCATION
        ):
            sys.exit("Aborted.")

    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=CONFIG_NAME,
            rag_managed_db_config=rag.RagManagedDbConfig(tier=rag.Unprovisioned()),
        )
    )
    print(f"Done. Tier is now: {_tier_name()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("up", help="create the corpus and ingest docs/*.pdf").set_defaults(func=up)
    sub.add_parser("status", help="show corpus contents and billing tier").set_defaults(func=status)
    sub.add_parser("down", help="delete the corpus").set_defaults(func=down)
    unp = sub.add_parser("unprovision", help="halt RAG Engine billing (destructive)")
    unp.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    unp.set_defaults(func=unprovision)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
