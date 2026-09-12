"""Read the dummy order/billing data, and file human-review requests.

The fixture is read-only seed data that ships with the agent (BUILD_PLAN 2.12).
Filed requests are appended to an in-process list, not written back: the record
that matters is the one the human reviewer works from, which lives outside this
system. Writes do not survive a restart, and that is understood, not accidental.
"""

from __future__ import annotations

import json
import secrets
from datetime import date
from pathlib import Path
from typing import Any

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures.json"

# Fixed so eval cases stay reproducible. Real code would use date.today().
TODAY = date(2026, 9, 12)

_data: dict[str, Any] | None = None
_filed_requests: list[dict[str, Any]] = []


def _load() -> dict[str, Any]:
    global _data
    if _data is None:
        _data = json.loads(FIXTURES_PATH.read_text())
    return _data


def get_order(order_id: str) -> dict[str, Any] | None:
    return _load()["orders"].get(order_id.strip().upper())


def get_invoice(invoice_id: str) -> dict[str, Any] | None:
    return _load()["invoices"].get(invoice_id.strip().upper())


def get_customer(customer_id: str) -> dict[str, Any] | None:
    return _load()["customers"].get(customer_id.strip().upper())


def billing_events(order_id: str) -> list[dict[str, Any]]:
    return _load()["known_billing_events"].get(order_id.strip().upper(), [])


def days_since_delivery(order: dict[str, Any]) -> int | None:
    """Days since delivery, or None if it has not arrived.

    Computed here rather than by the model: date arithmetic is ordinary
    software, and asking an LLM to do it is a design error (BUILD_PLAN 1).
    """
    delivered = order.get("delivered")
    if not delivered:
        return None
    return (TODAY - date.fromisoformat(delivered)).days


def file_request(kind: str, order_id: str, summary: str, details: dict[str, Any]) -> dict[str, Any]:
    """Record a request for a human to approve. Completes nothing.

    Returns the reference the customer is given (BUILD_PLAN 2.11).
    """
    ref = f"REQ-{secrets.token_hex(3).upper()}"
    record = {
        "reference": ref,
        "kind": kind,
        "order_id": order_id,
        "summary": summary,
        "details": details,
        "filed": TODAY.isoformat(),
        "human_decision": None,
    }
    _filed_requests.append(record)
    return record


def filed_requests() -> list[dict[str, Any]]:
    return list(_filed_requests)


def reset() -> None:
    """Clear filed requests and cached data. Tests only."""
    global _data
    _data = None
    _filed_requests.clear()
