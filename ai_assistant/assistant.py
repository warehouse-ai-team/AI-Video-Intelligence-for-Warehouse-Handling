from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompts import SYSTEM_PROMPT
from .tools import TOOL_DEFINITIONS, TOOL_EXECUTORS, BackendError

# Force loading .env from project root directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

MODEL = "gemini-flash-latest"
MAX_TOOL_ROUNDS = 5

def _to_gemini_tool_config() -> types.Tool:
    declarations = [
        types.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=t["input_schema"],
        )
        for t in TOOL_DEFINITIONS
    ]
    return types.Tool(function_declarations=declarations)


class WarehouseAssistant:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=key)
        self._tool = _to_gemini_tool_config()

    def ask(self, question: str, selected_event_id: str | None = None) -> dict:
        """
        Runs the agentic tool-use loop and returns:
        {"answer": str, "tools_used": list[str]}
        """
        user_text = question
        if selected_event_id:
            user_text += f"\n\n(The supervisor currently has event_id={selected_event_id} selected.)"

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_text)])]
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[self._tool],
        )
        tools_used: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content or not candidate.content.parts:
                return {"answer": response.text or "", "tools_used": tools_used}

            parts = candidate.content.parts
            function_calls = [p.function_call for p in parts if p.function_call]

            if not function_calls:
                return {"answer": response.text or "", "tools_used": tools_used}

            # Append the model's response containing the tool call request
            contents.append(candidate.content)

            response_parts = []
            for call in function_calls:
                tools_used.append(call.name)
                executor = TOOL_EXECUTORS.get(call.name)
                
                kwargs = dict(call.args) if call.args else {}
                try:
                    result = executor(**kwargs) if executor else {
                        "error": f"Unknown tool: {call.name}"
                    }
                except BackendError as exc:
                    result = {"error": str(exc)}
                except Exception as exc:
                    result = {"error": f"Execution error: {str(exc)}"}

                response_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={"result": result},
                    )
                )

            contents.append(types.Content(role="user", parts=response_parts))

        return {
            "answer": "I wasn't able to finish gathering the data needed to answer that. Please try rephrasing or ask something more specific.",
            "tools_used": tools_used,
        }