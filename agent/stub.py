"""A scripted chat model for tests and demos, so no live model is called."""

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class StubModel(BaseChatModel):
    """Reads the claim, approves it as claimed, then tries to pay it."""

    @property
    def _llm_type(self) -> str:
        return "stub"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "StubModel":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        claim_id = str(messages[1].content).split()[-1]
        replies = [m for m in messages if isinstance(m, ToolMessage)]
        step = len(replies)
        amount = json.loads(str(replies[0].content))["amount_claimed"] if replies else 0
        calls = [
            ("get_claim", {"claim_id": claim_id}),
            (
                "record_decision",
                {
                    "claim_id": claim_id,
                    "decision": "approve",
                    "payout": amount,
                    "explanation": "The loss is covered and paid as claimed.",
                    "policy_section": "Section 10, How we work out your payment",
                },
            ),
            ("pay_claim", {"claim_id": claim_id, "amount": amount}),
        ]
        if step < len(calls):
            name, args = calls[step]
            message = AIMessage(
                content="",
                tool_calls=[{"name": name, "args": args, "id": f"call-{step}"}],
            )
        else:
            message = AIMessage(content=f"Approved {claim_id} for ${amount:,.2f}.")
        return ChatResult(generations=[ChatGeneration(message=message)])
