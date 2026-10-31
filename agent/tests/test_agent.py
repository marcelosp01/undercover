from pathlib import Path

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from agent import main
from agent.stub import StubModel


class ScriptedModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def tool_call(name, args, call_id):
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": call_id}]
    )


def decide(claim_id, decision):
    args = {
        "claim_id": claim_id,
        "decision": decision,
        "payout": 0,
        "explanation": "Not covered.",
        "policy_section": "Section 9, General exclusions",
    }
    replies = [tool_call("record_decision", args, "1"), AIMessage(content="Done.")]
    return ScriptedModel(messages=iter(replies))


def test_small_claim_is_paid(client):
    reply = main.run("CLM-1001", "t1", StubModel())
    claim = client.get("/api/claims/CLM-1001").json()
    assert reply == "Approved CLM-1001 for $420.00."
    assert claim["state"] == "decided"
    assert claim["payment"]["amount"] == 420
    steps = [s["text"] for s in claim["steps"]]
    assert steps == [
        "Read the claim",
        "Decided to approve, payout $420.00",
        "Tried to pay $420.00",
    ]


def test_over_limit_payment_is_refused(client):
    main.run("CLM-1002", "t2", StubModel())
    claim = client.get("/api/claims/CLM-1002").json()
    assert claim["state"] == "awaiting_sign_off"
    assert claim["payment"] is None
    assert claim["steps"][-1]["text"].startswith("The system refused: Error 409")


def test_decline_and_refer_record_no_payment(client):
    for claim_id, decision in (("CLM-1004", "decline"), ("CLM-1005", "refer")):
        main.run(claim_id, "t3", decide(claim_id, decision))
        claim = client.get(f"/api/claims/{claim_id}").json()
        assert claim["decision"]["decision"] == decision
        assert claim["payment"] is None
        assert claim["state"] == "decided"


def test_tools_return_errors_for_the_agent():
    assert main.get_claim.invoke({"claim_id": "CLM-0000"}).startswith("Error 404")


def test_tools_read_from_the_backend():
    assert main.get_policy.invoke({"policy_id": "POL-2001"})["plan"] == "premium"
    assert main.get_plan.invoke({"plan": "first"})["deductible"] == 0
    assert main.get_customer.invoke({"customer_id": "CUS-3001"})["name"] == "Maya Patel"
    assert "Policy Wording" in main.get_policy_wording.invoke({})["text"]


def test_instructions_come_from_the_backend(client, monkeypatch):
    seen = []
    create = main.create_agent
    monkeypatch.setattr(
        main,
        "create_agent",
        lambda llm, tools, system_prompt: (
            seen.append(system_prompt)
            or create(llm, tools=tools, system_prompt=system_prompt)
        ),
    )
    main.run("CLM-1004", "t4", decide("CLM-1004", "decline"))
    assert seen == [client.get("/api/instructions").json()["text"]]


def test_agent_reads_no_files():
    source = Path(main.__file__).read_text(encoding="utf-8")
    assert "open(" not in source
    assert "pathlib" not in source


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("UNDERCOVER_STUB_AGENT", raising=False)
    default = main.model()
    assert isinstance(default, ChatOpenAI)
    assert default.model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    named = main.model()
    assert isinstance(named, ChatOpenAI)
    assert named.model_name == "openrouter/free"
    monkeypatch.setenv("UNDERCOVER_STUB_AGENT", "1")
    assert isinstance(main.model(), StubModel)
