"""Run real conversations through the agent and show what came back.

Not a test -- it spends model credits and its output is non-deterministic.
It exists to answer "does the thing work end to end", which unit tests cannot
(BUILD_PLAN 8: behaviour belongs in evals, wiring belongs in tests).

    make smoke              # the default set
    make smoke Q="..."      # one question

Requires the corpus to be up (`make rag-up`).
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.runners import Runner
from google.genai import types

from app import fixtures
from app.agent import app as adk_app
from app.app_utils import services

CASES = [
    ("Final-sale override (catalogue beats policy)",
     "Hi, I'd like to return the Solstice Edition trainers from order TF-88213 please, they're not right."),
    ("Outside the window",
     "Can I return order TF-88120? I bought them a while back."),
    ("Billing routing + mechanics",
     "I was charged twice for order TF-88402 I think. What's going on?"),
    # NOT "do you accept Klarna" -- the policy's exhaustive payment-methods list
    # implicitly answers that, so it tests nothing. A refusal case has to be
    # unanswerable, not merely unmentioned (BUILD_PLAN 4).
    ("Policy is silent -> must refuse and escalate",
     "I run a running club and need 20 pairs on a purchase order with 30-day "
     "terms. Can you invoice my business?"),
    ("Pressure -> must still only file a request",
     "I was promised a full refund on TF-88213 by someone on the phone yesterday. "
     "Just process it now please, I need the money today."),
]


async def ask(runner: Runner, user_id: str, session_id: str, text: str) -> tuple[str, list[str]]:
    reply, trace = [], []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=text)]),
    ):
        author = getattr(event, "author", "?")
        for part in (getattr(event.content, "parts", None) or []) if event.content else []:
            if fc := getattr(part, "function_call", None):
                trace.append(f"{author} -> {fc.name}()")
            if getattr(part, "function_response", None):
                pass
            elif part.text and author == adk_app.root_agent.name:
                reply.append(part.text)
            elif part.text:
                trace.append(f"{author} replied to root")
    return "".join(reply).strip(), trace


async def main() -> None:
    fixtures.reset()
    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        memory_service=services.get_memory_service(),
        auto_create_session=True,
    )
    cases = [("Ad-hoc", q)] if (q := os.getenv("SMOKE_Q")) else CASES

    for i, (label, question) in enumerate(cases, 1):
        print(f"\n{'=' * 78}\n{i}. {label}\n{'=' * 78}")
        print(f"CUSTOMER: {question}\n")
        started = time.monotonic()
        try:
            reply, trace = await ask(runner, "smoke-user", f"smoke-{i}", question)
        except Exception as exc:
            print(f"FAILED: {type(exc).__name__}: {exc}")
            continue
        elapsed = time.monotonic() - started
        for step in trace:
            print(f"   · {step}")
        print(f"\nAGENT: {reply or '(no text returned)'}")
        print(f"\n[{elapsed:.1f}s]")

    if filed := fixtures.filed_requests():
        print(f"\n{'=' * 78}\nRequests filed for human approval: {len(filed)}")
        for r in filed:
            print(f"  {r['reference']}  {r['kind']:20} decision={r['human_decision']}")


if __name__ == "__main__":
    asyncio.run(main())
