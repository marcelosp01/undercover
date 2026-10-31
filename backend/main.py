"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException

from backend import db

app = FastAPI(title="UnderCover")


def get_db() -> Iterator[sqlite3.Connection]:
    """Open a database connection for one request."""
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


Db = Annotated[sqlite3.Connection, Depends(get_db)]


def record(conn: sqlite3.Connection, kind: str, record_id: str) -> dict[str, Any]:
    """Return one stored record, or raise a 404."""
    row = conn.execute(
        "SELECT body FROM records WHERE kind = ? AND id = ?", (kind, record_id)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"No {kind} record {record_id}")
    return json.loads(row["body"])


def payout_limit(conn: sqlite3.Connection) -> float:
    """Return the payout above which a handler must sign off."""
    return record(conn, "company", "company")["payout_approval_limit"]


def claim_state(work: sqlite3.Row | None, limit: float) -> str:
    """Return waiting, in_progress, awaiting_sign_off or decided."""
    if work is None:
        return "waiting"
    if work["decision"] is None:
        return "in_progress"
    over_limit = work["decision"] == "approve" and work["payout"] > limit
    if over_limit and work["signed_off_by"] is None:
        return "awaiting_sign_off"
    return "decided"


def work_row(conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row | None:
    """Return the agent's work on a claim, if it has started."""
    return conn.execute("SELECT * FROM work WHERE claim_id = ?", (claim_id,)).fetchone()


def claim_view(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any]:
    """Return a claim with its state, decision, sign-off, payment and steps."""
    claim = record(conn, "claims", claim_id)
    work = work_row(conn, claim_id)
    view = {**claim, "state": claim_state(work, payout_limit(conn))}
    view["decision"] = None
    view["sign_off"] = None
    view["payment"] = None
    if work is not None and work["decision"] is not None:
        view["decision"] = {
            "decision": work["decision"],
            "payout": work["payout"],
            "explanation": work["explanation"],
            "policy_section": work["policy_section"],
            "decided_at": work["decided_at"],
        }
    if work is not None and work["signed_off_by"] is not None:
        handler = record(conn, "handlers", work["signed_off_by"])
        view["sign_off"] = {
            "handler_id": handler["handler_id"],
            "name": handler["name"],
            "signed_off_at": work["signed_off_at"],
        }
    if work is not None and work["paid_amount"] is not None:
        view["payment"] = {"amount": work["paid_amount"], "paid_at": work["paid_at"]}
    steps = conn.execute(
        "SELECT at, text FROM steps WHERE claim_id = ? ORDER BY id", (claim_id,)
    ).fetchall()
    view["steps"] = [dict(step) for step in steps]
    return view


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(conn: Db) -> list[dict[str, Any]]:
    """List every claim in the queue with its state."""
    ids = conn.execute(
        "SELECT id FROM records WHERE kind = 'claims' ORDER BY id"
    ).fetchall()
    claims = []
    for row in ids:
        view = claim_view(conn, row["id"])
        customer = record(conn, "customers", view["customer_id"])
        claims.append(
            {
                "claim_id": view["claim_id"],
                "customer_id": view["customer_id"],
                "customer_name": customer["name"],
                "claim_type": view["claim_type"],
                "summary": view["summary"],
                "submitted_on": view["submitted_on"],
                "amount_claimed": view["amount_claimed"],
                "state": view["state"],
                "decision": view["decision"],
            }
        )
    return claims


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, conn: Db) -> dict[str, Any]:
    """Get one claim in full, with the agent's decision, sign-off and steps."""
    return claim_view(conn, claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, conn: Db) -> dict[str, Any]:
    """Get one policy with its plan, add-ons and trip."""
    return record(conn, "policies", policy_id)


@app.get("/api/plans/{plan}", operation_id="get_plan")
def get_plan(plan: str, conn: Db) -> dict[str, Any]:
    """Get the limits, waiting periods and deductible of one plan."""
    return record(conn, "plans", plan)


@app.get("/api/customers/{customer_id}", operation_id="get_customer")
def get_customer(customer_id: str, conn: Db) -> dict[str, Any]:
    """Get a customer's details and claim history."""
    return record(conn, "customers", customer_id)


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(conn: Db) -> list[dict[str, Any]]:
    """List the claims handlers."""
    rows = conn.execute("SELECT body FROM records WHERE kind = 'handlers' ORDER BY id")
    return [json.loads(row["body"]) for row in rows]


@app.get("/api/company", operation_id="get_company")
def get_company(conn: Db) -> dict[str, Any]:
    """Get the company settings, including the payout approval limit."""
    return record(conn, "company", "company")


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> dict[str, str]:
    """Get the full text of the policy wording."""
    return {"text": (db.DATA / "policy_wording.md").read_text(encoding="utf-8")}


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> dict[str, str]:
    """Get the agent's instructions, read only."""
    return {"text": (Path(__file__).parent / "instructions.md").read_text("utf-8")}
