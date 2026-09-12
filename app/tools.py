"""Agent tools.

Two kinds, and the split is the safety boundary (BUILD_PLAN 2.11):

  * lookups and searches -- read-only, ungated. Answering is not an action.
  * request_* -- file a request for a human to approve. They return a reference
    number, never an outcome. Nothing here completes anything.

The naming is deliberate. A tool called `start_return` invites the model to
believe a return started.
"""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext
from google.adk.tools.load_memory_tool import load_memory_tool

from app import config, fixtures, retrieval

# --- Policy search (BUILD_PLAN 2.3, 2.4) --------------------------------------


def search_returns_policy(query: str) -> str:
    """Search the returns and exchanges policy and the product catalogue.

    Use for anything about whether an item can be returned or exchanged: time
    windows, item condition, packaging, faulty goods, and per-product rules such
    as final sale. Always search before making a determination.

    Args:
        query: What you need to know, in plain language.

    Returns:
        Retrieved policy extracts with the document each came from, or a message
        explaining that the policy could not be checked.
    """
    return retrieval.search(query, allowed_documents=config.RETURNS_POLICY_DOCS)


def search_billing_policy(query: str) -> str:
    """Search the billing and payments policy.

    Use for anything about money movement: payment methods, refund timing and
    routing, duplicate or pending charges, gift cards, discount codes, delivery
    charges, and disputed charges. Always search before making a determination.

    Args:
        query: What you need to know, in plain language.

    Returns:
        Retrieved policy extracts with the document each came from, or a message
        explaining that the policy could not be checked.
    """
    return retrieval.search(query, allowed_documents=config.BILLING_POLICY_DOCS)


# --- Read-only lookups (ungated) ----------------------------------------------


def lookup_order(order_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """Look up an order by its reference, e.g. TF-88213.

    Args:
        order_id: The order reference.

    Returns:
        Order details including what was bought, what was paid, and how many
        days have passed since delivery. `days_since_delivery` is computed for
        you -- do not calculate dates yourself.
    """
    order = fixtures.get_order(order_id)
    if order is None:
        return {"found": False, "order_id": order_id,
                "note": "No such order. Ask the customer to check the reference."}

    if customer_id := order.get("customer_id"):
        tool_context.state["user:customer_id"] = customer_id

    days = fixtures.days_since_delivery(order)
    return {
        "found": True,
        "order_id": order_id.upper(),
        "status": order["status"],
        "delivered": order.get("delivered"),
        "days_since_delivery": days,
        "not_yet_delivered": days is None,
        "items": order["items"],
        "delivery_charge": order["delivery_charge"],
        "discount_code": order.get("discount_code"),
        "discount_minimum_spend": order.get("discount_minimum_spend"),
        "payment": order["payment"],
        "total_paid": order["total_paid"],
        "reported_fault": order.get("reported_fault"),
    }


def lookup_invoice(invoice_id: str) -> dict[str, Any]:
    """Look up an invoice or VAT receipt by its reference, e.g. INV-5540.

    Args:
        invoice_id: The invoice reference.

    Returns:
        Invoice details, or a note that it was not found.
    """
    invoice = fixtures.get_invoice(invoice_id)
    if invoice is None:
        return {"found": False, "invoice_id": invoice_id}
    return {"found": True, "invoice_id": invoice_id.upper(), **invoice}


def check_charges(order_id: str) -> dict[str, Any]:
    """Check what charges exist against an order.

    Use when a customer reports a duplicate, unexpected or pending charge. An
    authorisation hold often looks like a second charge to the customer.

    Args:
        order_id: The order reference.

    Returns:
        The settled amount plus any outstanding authorisation holds.
    """
    order = fixtures.get_order(order_id)
    if order is None:
        return {"found": False, "order_id": order_id}
    return {
        "found": True,
        "order_id": order_id.upper(),
        "settled_amount": order["total_paid"],
        "payment": order["payment"],
        "other_events": fixtures.billing_events(order_id),
    }


# --- Requests: filed for a human, never completed (BUILD_PLAN 2.11) -----------


def _file(kind: str, order_id: str, summary: str, ctx: ToolContext,
          **details: Any) -> dict[str, Any]:
    record = fixtures.file_request(kind, order_id.upper(), summary, details)
    ctx.state["user:open_request_ref"] = record["reference"]
    return {
        "filed": True,
        "reference": record["reference"],
        "summary": summary,
        "completed": False,
        "tell_the_customer": (
            f"This has been sent to a colleague for approval with reference "
            f"{record['reference']}. It has NOT been actioned yet. Say so plainly -- "
            f"do not imply the refund, return or adjustment has already happened."
        ),
    }


def request_return(order_id: str, reason: str, summary: str,
                   tool_context: ToolContext) -> dict[str, Any]:
    """File a return request for a human to approve.

    Only call this after checking the policy and confirming with the customer.
    It does NOT start a return -- it queues one for approval.

    Args:
        order_id: The order reference.
        reason: Why the customer wants to return, in their own terms.
        summary: One plain-English sentence stating exactly what is being
            requested, which both the customer and the reviewer will read.

    Returns:
        A reference number and an explicit reminder that nothing has happened yet.
    """
    return _file("return", order_id, summary, tool_context, reason=reason)


def request_exchange(order_id: str, wanted: str, summary: str,
                     tool_context: ToolContext) -> dict[str, Any]:
    """File an exchange request for a human to approve.

    Does NOT arrange an exchange -- it queues one for approval.

    Args:
        order_id: The order reference.
        wanted: The size, colour or item the customer wants instead.
        summary: One plain-English sentence stating exactly what is requested.

    Returns:
        A reference number and an explicit reminder that nothing has happened yet.
    """
    return _file("exchange", order_id, summary, tool_context, wanted=wanted)


def request_billing_adjustment(order_id: str, issue: str, summary: str,
                               tool_context: ToolContext) -> dict[str, Any]:
    """File a billing adjustment for a human to approve.

    Use for duplicate charges, disputed amounts, or refunds that need to be
    rerouted. Does NOT move any money -- it queues the request for approval.

    Args:
        order_id: The order reference.
        issue: What appears to be wrong with the charge.
        summary: One plain-English sentence stating exactly what is requested.

    Returns:
        A reference number and an explicit reminder that nothing has happened yet.
    """
    return _file("billing_adjustment", order_id, summary, tool_context, issue=issue)


def escalate_to_human(topic: str, summary: str, tool_context: ToolContext) -> dict[str, Any]:
    """Hand a question to a person when the policy does not cover it.

    Use when the documents are silent, or the customer needs something outside
    what these tools can do. This is a legitimate outcome, not a failure.

    Args:
        topic: What the question is about.
        summary: One plain-English sentence a colleague can act on.

    Returns:
        A reference number to give the customer.
    """
    return _file("escalation", "n/a", summary, tool_context, topic=topic)


# `load_memory` searches what was said in EARLIER conversations (BUILD_PLAN 2.8).
# It is deliberately the last tool listed: it supplies context to reason with,
# never a determination. The specialists' instructions state that the policy
# outranks anything memory returns, and there is an eval case for exactly the
# case where the two disagree.
RETURNS_TOOLS = [search_returns_policy, lookup_order, request_return,
                 request_exchange, escalate_to_human, load_memory_tool]
BILLING_TOOLS = [search_billing_policy, lookup_order, lookup_invoice,
                 check_charges, request_billing_adjustment, escalate_to_human,
                 load_memory_tool]
