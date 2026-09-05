from __future__ import annotations
import json
import os
from anthropic import Anthropic

from .prompts import SYSTEM_PROMPT
from .tools import TOOL_DEFINITIONS, TOOL_EXECUTORS, BackendError

MODEL = "claude-sonnet-5"
MAX_TOOL_ROUNDS = 5  # guardrail against runaway tool-call loops


class WarehouseAssistant:
    def __init__(self, api_key: str | None = None):
        # Reads ANTHROPIC_API_KEY from env if not passed explicitly.
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def ask(self, question: str, selected_event_id: str | None = None) -> dict:
        """
        Runs the agentic tool-use loop and returns:
        {"answer": str, "tools_used": list[str]}
        """
        user_content = question
        if selected_event_id:
            user_content += f"\n\n(The supervisor currently has event_id={selected_event_id} selected.)"

        messages = [{"role": "user", "content": user_content}]
        tools_used: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                final_text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                return {"answer": final_text, "tools_used": tools_used}

            # Claude wants to call one or more tools — execute each and
            # feed results back before asking for the final answer.
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue
                tools_used.append(block.name)
                executor = TOOL_EXECUTORS.get(block.name)
                try:
                    result = executor(**block.input) if executor else {
                        "error": f"Unknown tool: {block.name}"
                    }
                except BackendError as exc:
                    result = {"error": str(exc)}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

            messages.append({"role": "user", "content": tool_results})

        return {
            "answer": "I wasn't able to finish gathering the data needed to answer that. Please try rephrasing or ask something more specific.",
            "tools_used": tools_used,
        }