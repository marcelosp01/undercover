"""The UnderCover Agent."""

import os
import sys
import uuid
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent.stub import StubModel

load_dotenv(override=True)

BACKEND_URL = "http://127.0.0.1:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def call(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    """Call the backend and return its JSON, or the error text for the agent."""
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_error:
        return f"Error {response.status_code}: {response.text}"
    return response.json()


@tool
def get_claim(claim_id: str) -> Any:
    """Get a claim: the story, items, documents and its state so far."""
    return call("GET", f"/api/claims/{claim_id}")


@tool
def get_policy(policy_id: str) -> Any:
    """Get a policy: its plan, add-ons, trip and travelers."""
    return call("GET", f"/api/policies/{policy_id}")


@tool
def get_plan(plan: str) -> Any:
    """Get the limits of a plan: economy, premium or first."""
    return call("GET", f"/api/plans/{plan}")


@tool
def get_customer(customer_id: str) -> Any:
    """Get a customer's details and claim history."""
    return call("GET", f"/api/customers/{customer_id}")


@tool
def get_policy_wording() -> Any:
    """Get the full policy wording."""
    return call("GET", "/api/policy-wording")


@tool
def record_decision(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    explanation: str,
    policy_section: str,
) -> Any:
    """Record the decision, payout in USD, explanation and policy section."""
    body = {
        "decision": decision,
        "payout": payout,
        "explanation": explanation,
        "policy_section": policy_section,
    }
    return call("POST", f"/api/claims/{claim_id}/decision", body)


@tool
def pay_claim(claim_id: str, amount: float) -> Any:
    """Pay the approved payout; over the limit it waits for a handler's sign-off."""
    return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})


TOOLS = [
    get_claim,
    get_policy,
    get_plan,
    get_customer,
    get_policy_wording,
    record_decision,
    pay_claim,
]

LABELS = {
    "get_claim": "Read the claim",
    "get_policy": "Read the policy",
    "get_plan": "Read the plan",
    "get_customer": "Read the customer and claim history",
    "get_policy_wording": "Read the policy wording",
}


class StepLogger(BaseCallbackHandler):
    """Log each tool call of the agent as a step on the claim."""

    def __init__(self, claim_id: str) -> None:
        self.claim_id = claim_id

    def add(self, text: str) -> None:
        call("POST", f"/api/claims/{self.claim_id}/steps", {"text": text})

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        name, args = serialized["name"], inputs or {}
        if name == "record_decision":
            self.add(f"Decided to {args['decision']}, payout ${args['payout']:,.2f}")
        elif name == "pay_claim":
            self.add(f"Tried to pay ${args['amount']:,.2f}")
        else:
            self.add(LABELS[name])

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        text = str(getattr(output, "content", output))
        if text.startswith("Error"):
            self.add(f"The system refused: {text}")


def model() -> StubModel | ChatOpenAI:
    """Return the stub if UNDERCOVER_STUB_AGENT is set, else the real model."""
    if os.getenv("UNDERCOVER_STUB_AGENT"):
        return StubModel()
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim and return its final reply."""
    with backend() as client:
        response = client.get("/api/instructions")
        response.raise_for_status()
        instructions = response.json()["text"]
        client.post(f"/api/claims/{claim_id}/start").raise_for_status()
    agent = create_agent(llm or model(), tools=TOOLS, system_prompt=instructions)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Claim {claim_id}"}]},
        config={
            "configurable": {"thread_id": thread_id},
            "callbacks": [StepLogger(claim_id)],
        },
    )
    return result["messages"][-1].text


if __name__ == "__main__":
    print(run(sys.argv[1], str(uuid.uuid4())))
