"""The UnderCover backend."""

import json
import sqlite3
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from pydantic import BaseModel

from agent import main as agent_main
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


class Decision(BaseModel):
    decision: Literal["approve", "decline", "refer"]
    payout: float
    explanation: str
    policy_section: str


class Step(BaseModel):
    text: str


class SignOff(BaseModel):
    handler_id: str


class Payment(BaseModel):
    amount: float


def now() -> str:
    """Return the current UTC time to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


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


def start(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any]:
    """Mark a waiting claim in progress; a claim already in progress stays so."""
    record(conn, "claims", claim_id)
    work = work_row(conn, claim_id)
    if work is not None and work["decision"] is not None:
        raise HTTPException(409, f"Claim {claim_id} already has a decision")
    if work is None:
        conn.execute(
            "INSERT INTO work (claim_id, started_at) VALUES (?, ?)", (claim_id, now())
        )
        conn.commit()
    return claim_view(conn, claim_id)


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, conn: Db) -> dict[str, Any]:
    """Mark a claim in progress when the agent starts work on it."""
    return start(conn, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, step: Step, conn: Db) -> dict[str, Any]:
    """Log one step of the agent's work on a claim."""
    record(conn, "claims", claim_id)
    conn.execute(
        "INSERT INTO steps (claim_id, at, text) VALUES (?, ?, ?)",
        (claim_id, now(), step.text),
    )
    conn.commit()
    return claim_view(conn, claim_id)


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, body: Decision, conn: Db) -> dict[str, Any]:
    """Record the agent's decision, payout, explanation and policy section."""
    record(conn, "claims", claim_id)
    work = work_row(conn, claim_id)
    if work is None or work["decision"] is not None:
        raise HTTPException(409, f"Claim {claim_id} is not in progress")
    if (body.decision == "approve") != (body.payout > 0):
        raise HTTPException(422, "The payout is above zero if and only if approved")
    conn.execute(
        "UPDATE work SET decision = ?, payout = ?, explanation = ?, "
        "policy_section = ?, decided_at = ? WHERE claim_id = ?",
        (
            body.decision,
            body.payout,
            body.explanation,
            body.policy_section,
            now(),
            claim_id,
        ),
    )
    conn.commit()
    return claim_view(conn, claim_id)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, body: SignOff, conn: Db) -> dict[str, Any]:
    """Record a handler's sign-off on an approved payout over the limit."""
    record(conn, "claims", claim_id)
    handler = record(conn, "handlers", body.handler_id)
    if not handler["can_approve_over_limit"]:
        raise HTTPException(403, f"{handler['name']} cannot sign off over the limit")
    work = work_row(conn, claim_id)
    if claim_state(work, payout_limit(conn)) != "awaiting_sign_off":
        raise HTTPException(409, f"Claim {claim_id} is not awaiting sign-off")
    conn.execute(
        "UPDATE work SET signed_off_by = ?, signed_off_at = ? WHERE claim_id = ?",
        (body.handler_id, now(), claim_id),
    )
    conn.commit()
    return claim_view(conn, claim_id)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, body: Payment, conn: Db) -> dict[str, Any]:
    """Pay the approved amount; a payout over the limit waits for sign-off."""
    record(conn, "claims", claim_id)
    work = work_row(conn, claim_id)
    if work is None or work["decision"] != "approve":
        raise HTTPException(409, f"Claim {claim_id} has no approved payout")
    if work["paid_amount"] is not None:
        raise HTTPException(409, f"Claim {claim_id} is already paid")
    if body.amount != work["payout"]:
        raise HTTPException(409, f"The approved payout is {work['payout']:.2f}")
    if claim_state(work, payout_limit(conn)) == "awaiting_sign_off":
        raise HTTPException(409, f"Claim {claim_id} needs a handler's sign-off first")
    conn.execute(
        "UPDATE work SET paid_amount = ?, paid_at = ? WHERE claim_id = ?",
        (body.amount, now(), claim_id),
    )
    conn.commit()
    return claim_view(conn, claim_id)


def run_in_background(claim_id: str) -> None:
    """Run the agent on a claim, and log a step if it stops with an error."""
    try:
        agent_main.run(claim_id, str(uuid.uuid4()))
    except Exception as error:
        conn = db.connect()
        conn.execute(
            "INSERT INTO steps (claim_id, at, text) VALUES (?, ?, ?)",
            (claim_id, now(), f"The agent stopped: {error}"),
        )
        conn.commit()
        conn.close()


@app.post("/api/claims/{claim_id}/run", operation_id="run_agent", status_code=202)
def run_agent(claim_id: str, tasks: BackgroundTasks, conn: Db) -> dict[str, Any]:
    """Start the agent on a waiting claim; it works in the background."""
    record(conn, "claims", claim_id)
    if work_row(conn, claim_id) is not None:
        raise HTTPException(409, f"Claim {claim_id} is not waiting")
    view = start(conn, claim_id)
    tasks.add_task(run_in_background, claim_id)
    return view
